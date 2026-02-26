# -*- coding: utf-8 -*-
"""
築未科技 — 統一金流閘道
═══════════════════════════════════════════
整合三大支付管道：
  1. 綠界 ECPay（信用卡 / ATM / 超商）
  2. 支付寶 Alipay（跨境支付 / 大陸客戶）
  3. 街口支付 JKoPay（台灣行動支付）

統一介面：
  - create_order(method, user_id, plan, ...)  → 建立訂單
  - verify_callback(method, params)           → 驗證回調
  - query_order(method, order_id)             → 查詢訂單
  - list_methods()                            → 列出可用支付方式

環境變數：
  # 綠界 ECPay
  ECPAY_MERCHANT_ID / ECPAY_HASH_KEY / ECPAY_HASH_IV
  ECPAY_RETURN_URL / ECPAY_ORDER_RESULT_URL / ECPAY_SANDBOX

  # 支付寶 Alipay（Global / 跨境）
  ALIPAY_APP_ID / ALIPAY_PRIVATE_KEY / ALIPAY_PUBLIC_KEY
  ALIPAY_NOTIFY_URL / ALIPAY_RETURN_URL / ALIPAY_SANDBOX

  # 街口支付 JKoPay
  JKOPAY_STORE_ID / JKOPAY_API_KEY / JKOPAY_SECRET_KEY
  JKOPAY_NOTIFY_URL / JKOPAY_RETURN_URL / JKOPAY_SANDBOX
"""

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# ══════════════════════════════════════════════════════════════
# 共用設定
# ══════════════════════════════════════════════════════════════

ROOT = Path(__file__).resolve().parent
ORDER_DIR = ROOT / "brain_workspace" / "orders"
ORDER_DIR.mkdir(parents=True, exist_ok=True)

# 訂閱方案（三種金流共用）
PLANS = {
    "free":       {"name": "免費體驗版", "price": 0,    "period": "none",    "tier": "free"},
    "basic":      {"name": "基礎版",     "price": 499,  "period": "monthly", "tier": "free"},
    "pro":        {"name": "專業版",     "price": 1500, "period": "monthly", "tier": "professional"},
    "pro_annual": {"name": "專業版年繳", "price": 15000,"period": "yearly",  "tier": "professional"},
    "enterprise": {"name": "企業版",     "price": 8000, "period": "monthly", "tier": "enterprise"},
    "ent_annual": {"name": "企業版年繳", "price": 80000,"period": "yearly",  "tier": "enterprise"},
}

PAYMENT_METHODS = {
    "ecpay":  {"name": "綠界 ECPay",  "icon": "💳", "desc": "信用卡 / ATM / 超商代碼", "region": "台灣"},
    "alipay": {"name": "支付寶 Alipay","icon": "🔵", "desc": "支付寶掃碼 / 跨境支付",   "region": "中國大陸 / 全球"},
    "jkopay": {"name": "街口支付",     "icon": "🟢", "desc": "街口 App 掃碼付款",       "region": "台灣"},
}


def _save_order(order: dict):
    """儲存訂單到本地 JSON（備份用）。"""
    oid = order.get("order_id", f"unknown_{int(time.time())}")
    fpath = ORDER_DIR / f"{oid}.json"
    fpath.write_text(json.dumps(order, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_order(order_id: str) -> Optional[dict]:
    fpath = ORDER_DIR / f"{order_id}.json"
    if fpath.exists():
        return json.loads(fpath.read_text(encoding="utf-8"))
    return None


def _update_order_status(order_id: str, status: str, extra: dict = None):
    order = _load_order(order_id)
    if order:
        order["status"] = status
        order["updated_at"] = datetime.now().isoformat(timespec="seconds")
        if extra:
            order.update(extra)
        _save_order(order)


def _db_save_payment(user_id: str, amount: int, method: str, order_id: str, plan: str, status: str = "pending", metadata: dict = None):
    """嘗試寫入 PostgreSQL（可選）。"""
    try:
        import db_postgres
        conn = db_postgres._get_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO payments (user_id, amount_ntd, payment_method, payment_id, status, plan, metadata)
               VALUES (%s::UUID, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (payment_id) DO UPDATE SET status = EXCLUDED.status, updated_at = NOW()""",
            (user_id if user_id and user_id != "anonymous" else None,
             amount, method, order_id, status, plan,
             json.dumps(metadata or {}, ensure_ascii=False)),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


def _activate_user(user_id: str, plan: str):
    """付款成功 → 自動啟用訂閱 + License + Revenue Platform。"""
    # 啟用訂閱
    try:
        import auth_manager
        auth_manager.activate_subscription(user_id, plan)
    except Exception:
        pass
    # 自動生成/更新 License
    try:
        import license_manager
        tier = PLANS.get(plan, {}).get("tier", "free")
        if tier != "free":
            days = 365 if "annual" in plan else 30
            license_manager.generate_license(
                customer_name=user_id,
                tier=tier,
                duration_days=days,
                notes=f"auto-generated from payment plan={plan}",
            )
    except Exception:
        pass
    # Revenue Platform — 建立訂閱記錄
    try:
        from revenue_platform import get_platform as _get_rev
        _PLAN_TO_PRODUCT = {
            "creator_basic": "ai_creator", "creator_pro": "ai_creator", "creator_ultra": "ai_creator",
            "cms_pro": "construction_ai", "cms_enterprise": "construction_ai",
            "api_starter": "llm_api", "api_pro": "llm_api", "api_business": "llm_api", "api_unlimited": "llm_api",
            "basic": "ai_creator", "pro": "construction_ai", "enterprise": "construction_ai",
            "pro_annual": "construction_ai", "ent_annual": "construction_ai",
        }
        product = _PLAN_TO_PRODUCT.get(plan, "")
        if product:
            _get_rev().create_subscription(user_id, product, plan)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
# 1. 綠界 ECPay
# ══════════════════════════════════════════════════════════════

ECPAY_MERCHANT_ID = os.environ.get("ECPAY_MERCHANT_ID", "3002607").strip()
ECPAY_HASH_KEY = os.environ.get("ECPAY_HASH_KEY", "pwFHCqoQZGmho4w6").strip()
ECPAY_HASH_IV = os.environ.get("ECPAY_HASH_IV", "EkRm7iFT261dpevs").strip()
ECPAY_RETURN_URL = os.environ.get("ECPAY_RETURN_URL", "").strip()
ECPAY_ORDER_RESULT_URL = os.environ.get("ECPAY_ORDER_RESULT_URL", "").strip()
ECPAY_SANDBOX = os.environ.get("ECPAY_SANDBOX", "true").strip().lower() in ("true", "1", "yes")

_ECPAY_BASE = "https://payment-stage.ecpay.com.tw" if ECPAY_SANDBOX else "https://payment.ecpay.com.tw"
ECPAY_PAYMENT_URL = f"{_ECPAY_BASE}/Cashier/AioCheckOut/V5"
ECPAY_QUERY_URL = f"{_ECPAY_BASE}/Cashier/QueryTradeInfo/V5"


def _ecpay_check_mac(params: dict) -> str:
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    raw = f"HashKey={ECPAY_HASH_KEY}&" + "&".join(f"{k}={v}" for k, v in sorted_params) + f"&HashIV={ECPAY_HASH_IV}"
    encoded = urllib.parse.quote_plus(raw)
    for old, new in [("%2d", "-"), ("%5f", "_"), ("%2e", "."), ("%21", "!"),
                     ("%2a", "*"), ("%28", "("), ("%29", ")"), ("%20", "+")]:
        encoded = encoded.replace(old, new)
    return hashlib.sha256(encoded.lower().encode("utf-8")).hexdigest().upper()


def _ecpay_create(user_id: str, plan: str, amount: int, name: str, **kw) -> dict:
    order_id = f"ZW{int(time.time())}{(user_id or 'anon')[-4:]}"
    params = {
        "MerchantID": ECPAY_MERCHANT_ID,
        "MerchantTradeNo": order_id[:20],
        "MerchantTradeDate": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
        "PaymentType": "aio",
        "TotalAmount": str(amount),
        "TradeDesc": urllib.parse.quote_plus("築未科技AI平台訂閱"),
        "ItemName": name[:200],
        "ReturnURL": kw.get("return_url") or ECPAY_RETURN_URL or "https://brain.zhe-wei.net/api/gateway/callback/ecpay",
        "OrderResultURL": kw.get("order_result_url") or ECPAY_ORDER_RESULT_URL or "",
        "ChoosePayment": "ALL",
        "EncryptType": "1",
        "NeedExtraPaidInfo": "Y",
        "CustomField1": (user_id or "")[:50],
        "CustomField2": (plan or "")[:50],
    }
    params = {k: v for k, v in params.items() if v}
    params["CheckMacValue"] = _ecpay_check_mac(params)

    form_fields = "\n".join(f'<input type="hidden" name="{k}" value="{v}">' for k, v in params.items())
    form_html = f'<form id="ecpay_form" method="POST" action="{ECPAY_PAYMENT_URL}">{form_fields}</form><script>document.getElementById("ecpay_form").submit();</script>'

    order = {
        "order_id": order_id, "method": "ecpay", "user_id": user_id,
        "plan": plan, "amount": amount, "status": "pending",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    _save_order(order)
    _db_save_payment(user_id, amount, "ecpay", order_id, plan)

    return {"ok": True, "order_id": order_id, "amount": amount, "plan": plan,
            "method": "ecpay", "form_html": form_html, "sandbox": ECPAY_SANDBOX}


def _ecpay_verify(params: dict) -> dict:
    received = params.get("CheckMacValue", "")
    check_params = {k: v for k, v in params.items() if k != "CheckMacValue"}
    expected = _ecpay_check_mac(check_params)
    if received != expected:
        return {"ok": False, "error": "ECPay CheckMacValue 驗證失敗", "paid": False}

    paid = params.get("RtnCode", "") == "1"
    order_id = params.get("MerchantTradeNo", "")
    user_id = params.get("CustomField1", "")
    plan = params.get("CustomField2", "")

    status = "paid" if paid else "failed"
    _update_order_status(order_id, status, {"trade_no": params.get("TradeNo", "")})
    _db_save_payment(user_id, int(params.get("TradeAmt", "0") or 0), "ecpay", order_id, plan, status)

    if paid and user_id and plan:
        _activate_user(user_id, plan)

    return {"ok": True, "paid": paid, "order_id": order_id, "user_id": user_id,
            "plan": plan, "method": "ecpay", "trade_no": params.get("TradeNo", "")}


def _ecpay_query(order_id: str) -> dict:
    params = {
        "MerchantID": ECPAY_MERCHANT_ID,
        "MerchantTradeNo": order_id[:20],
        "TimeStamp": str(int(time.time())),
    }
    params["CheckMacValue"] = _ecpay_check_mac(params)
    data = urllib.parse.urlencode(params).encode("utf-8")
    try:
        req = urllib.request.Request(ECPAY_QUERY_URL, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return {"ok": True, "method": "ecpay", **dict(urllib.parse.parse_qsl(body))}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# 2. 支付寶 Alipay（Global / 跨境）
# ══════════════════════════════════════════════════════════════

ALIPAY_APP_ID = os.environ.get("ALIPAY_APP_ID", "").strip()
ALIPAY_PRIVATE_KEY = os.environ.get("ALIPAY_PRIVATE_KEY", "").strip()
ALIPAY_PUBLIC_KEY = os.environ.get("ALIPAY_PUBLIC_KEY", "").strip()
ALIPAY_NOTIFY_URL = os.environ.get("ALIPAY_NOTIFY_URL", "").strip()
ALIPAY_RETURN_URL = os.environ.get("ALIPAY_RETURN_URL", "").strip()
ALIPAY_SANDBOX = os.environ.get("ALIPAY_SANDBOX", "true").strip().lower() in ("true", "1", "yes")

_ALIPAY_GATEWAY = "https://openapi-sandbox.dl.alipaydev.com/gateway.do" if ALIPAY_SANDBOX else "https://openapi.alipay.com/gateway.do"


def _alipay_sign(params: dict) -> str:
    """
    RSA2 (SHA256WithRSA) 簽章。
    若無 rsa 模組，降級為 HMAC-SHA256。
    """
    sorted_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v and k != "sign")

    # 嘗試 RSA 簽章
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        key_data = ALIPAY_PRIVATE_KEY
        if "BEGIN" not in key_data:
            key_data = f"-----BEGIN RSA PRIVATE KEY-----\n{key_data}\n-----END RSA PRIVATE KEY-----"
        private_key = serialization.load_pem_private_key(key_data.encode(), password=None)
        signature = private_key.sign(
            sorted_str.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")
    except ImportError:
        pass

    # 降級：HMAC-SHA256（開發/測試用）
    secret = ALIPAY_PRIVATE_KEY or "dev_secret"
    return hmac.new(secret.encode(), sorted_str.encode(), hashlib.sha256).hexdigest()


def _alipay_verify_sign(params: dict) -> bool:
    """驗證支付寶回調簽章。"""
    sign = params.get("sign", "")
    sign_type = params.get("sign_type", "RSA2")
    sorted_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v and k not in ("sign", "sign_type"))

    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        key_data = ALIPAY_PUBLIC_KEY
        if "BEGIN" not in key_data:
            key_data = f"-----BEGIN PUBLIC KEY-----\n{key_data}\n-----END PUBLIC KEY-----"
        public_key = serialization.load_pem_public_key(key_data.encode())
        public_key.verify(
            base64.b64decode(sign),
            sorted_str.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def _alipay_create(user_id: str, plan: str, amount: int, name: str, **kw) -> dict:
    if not ALIPAY_APP_ID:
        return {"ok": False, "error": "支付寶未設定 ALIPAY_APP_ID，請在 .env 中配置"}

    order_id = f"ZWA{int(time.time())}{(user_id or 'anon')[-4:]}"

    # 將 NTD 轉換為 CNY（約 1:4.5 匯率，實際應動態取得）
    ntd_to_cny_rate = float(os.environ.get("NTD_TO_CNY_RATE", "0.22"))
    amount_cny = round(amount * ntd_to_cny_rate, 2)

    biz_content = json.dumps({
        "out_trade_no": order_id,
        "total_amount": f"{amount_cny:.2f}",
        "subject": name[:256],
        "product_code": "FAST_INSTANT_TRADE_PAY",
        "passback_params": urllib.parse.quote_plus(json.dumps({"user_id": user_id, "plan": plan})),
    }, ensure_ascii=False)

    params = {
        "app_id": ALIPAY_APP_ID,
        "method": "alipay.trade.page.pay",
        "format": "JSON",
        "return_url": kw.get("return_url") or ALIPAY_RETURN_URL or "https://brain.zhe-wei.net/api/gateway/return/alipay",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "notify_url": kw.get("notify_url") or ALIPAY_NOTIFY_URL or "https://brain.zhe-wei.net/api/gateway/callback/alipay",
        "biz_content": biz_content,
    }
    params["sign"] = _alipay_sign(params)

    # 產生跳轉 URL
    query = urllib.parse.urlencode(params)
    redirect_url = f"{_ALIPAY_GATEWAY}?{query}"

    form_fields = "\n".join(f'<input type="hidden" name="{k}" value="{v}">' for k, v in params.items())
    form_html = f'<form id="alipay_form" method="GET" action="{_ALIPAY_GATEWAY}">{form_fields}</form><script>document.getElementById("alipay_form").submit();</script>'

    order = {
        "order_id": order_id, "method": "alipay", "user_id": user_id,
        "plan": plan, "amount": amount, "amount_cny": amount_cny,
        "status": "pending", "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    _save_order(order)
    _db_save_payment(user_id, amount, "alipay", order_id, plan, metadata={"amount_cny": amount_cny})

    return {"ok": True, "order_id": order_id, "amount": amount, "amount_cny": amount_cny,
            "plan": plan, "method": "alipay", "redirect_url": redirect_url,
            "form_html": form_html, "sandbox": ALIPAY_SANDBOX}


def _alipay_verify(params: dict) -> dict:
    # 驗證簽章
    if ALIPAY_PUBLIC_KEY and not _alipay_verify_sign(params):
        return {"ok": False, "error": "支付寶簽章驗證失敗", "paid": False}

    trade_status = params.get("trade_status", "")
    paid = trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED")
    order_id = params.get("out_trade_no", "")
    trade_no = params.get("trade_no", "")

    # 解析 passback_params
    user_id = ""
    plan = ""
    try:
        pb = json.loads(urllib.parse.unquote_plus(params.get("passback_params", "{}")))
        user_id = pb.get("user_id", "")
        plan = pb.get("plan", "")
    except Exception:
        pass

    status = "paid" if paid else "failed"
    _update_order_status(order_id, status, {"trade_no": trade_no, "trade_status": trade_status})
    _db_save_payment(user_id, 0, "alipay", order_id, plan, status)

    if paid and user_id and plan:
        _activate_user(user_id, plan)

    return {"ok": True, "paid": paid, "order_id": order_id, "user_id": user_id,
            "plan": plan, "method": "alipay", "trade_no": trade_no, "trade_status": trade_status}


def _alipay_query(order_id: str) -> dict:
    if not ALIPAY_APP_ID:
        return {"ok": False, "error": "支付寶未設定"}

    biz_content = json.dumps({"out_trade_no": order_id}, ensure_ascii=False)
    params = {
        "app_id": ALIPAY_APP_ID,
        "method": "alipay.trade.query",
        "format": "JSON",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "biz_content": biz_content,
    }
    params["sign"] = _alipay_sign(params)

    query = urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(f"{_ALIPAY_GATEWAY}?{query}", method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            trade_resp = body.get("alipay_trade_query_response", {})
            return {"ok": True, "method": "alipay", **trade_resp}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# 3. 街口支付 JKoPay
# ══════════════════════════════════════════════════════════════

JKOPAY_STORE_ID = os.environ.get("JKOPAY_STORE_ID", "").strip()
JKOPAY_API_KEY = os.environ.get("JKOPAY_API_KEY", "").strip()
JKOPAY_SECRET_KEY = os.environ.get("JKOPAY_SECRET_KEY", "").strip()
JKOPAY_NOTIFY_URL = os.environ.get("JKOPAY_NOTIFY_URL", "").strip()
JKOPAY_RETURN_URL = os.environ.get("JKOPAY_RETURN_URL", "").strip()
JKOPAY_SANDBOX = os.environ.get("JKOPAY_SANDBOX", "true").strip().lower() in ("true", "1", "yes")

_JKOPAY_BASE = "https://sandbox-api.jkopay.com" if JKOPAY_SANDBOX else "https://api.jkopay.com"


def _jkopay_sign(payload: str) -> str:
    """HMAC-SHA256 簽章（街口 API 規範）。"""
    secret = JKOPAY_SECRET_KEY or "dev_secret"
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _jkopay_api(endpoint: str, body: dict) -> dict:
    """呼叫街口 API。"""
    url = f"{_JKOPAY_BASE}{endpoint}"
    payload_str = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    signature = _jkopay_sign(payload_str)

    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": JKOPAY_API_KEY,
        "X-Signature": signature,
    }

    data = payload_str.encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="ignore")
        return {"ok": False, "error": f"HTTP {e.code}: {body_text[:300]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _jkopay_create(user_id: str, plan: str, amount: int, name: str, **kw) -> dict:
    if not JKOPAY_STORE_ID:
        return {"ok": False, "error": "街口支付未設定 JKOPAY_STORE_ID，請在 .env 中配置"}

    order_id = f"ZWJ{int(time.time())}{(user_id or 'anon')[-4:]}"

    body = {
        "store_id": JKOPAY_STORE_ID,
        "platform_order_id": order_id,
        "currency": "TWD",
        "total_price": amount,
        "final_price": amount,
        "unredeem": 0,
        "product_name": name[:100],
        "product_image_url": "",
        "result_url": kw.get("return_url") or JKOPAY_RETURN_URL or "https://brain.zhe-wei.net/api/gateway/return/jkopay",
        "result_display_url": kw.get("return_url") or JKOPAY_RETURN_URL or "",
        "notify_url": kw.get("notify_url") or JKOPAY_NOTIFY_URL or "https://brain.zhe-wei.net/api/gateway/callback/jkopay",
        "metadata": json.dumps({"user_id": user_id, "plan": plan}, ensure_ascii=False),
    }

    resp = _jkopay_api("/platform/entry/api/v1/orders", body)

    if resp.get("result_code") == "000" or resp.get("ok") is not False:
        payment_url = resp.get("payment_url", "")
        form_html = f'<script>window.location.href="{payment_url}";</script>' if payment_url else ""

        order = {
            "order_id": order_id, "method": "jkopay", "user_id": user_id,
            "plan": plan, "amount": amount, "status": "pending",
            "payment_url": payment_url,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        _save_order(order)
        _db_save_payment(user_id, amount, "jkopay", order_id, plan)

        return {"ok": True, "order_id": order_id, "amount": amount, "plan": plan,
                "method": "jkopay", "payment_url": payment_url,
                "form_html": form_html, "sandbox": JKOPAY_SANDBOX}
    else:
        return {"ok": False, "error": resp.get("error") or resp.get("result_message", "街口 API 呼叫失敗"),
                "method": "jkopay", "raw": resp}


def _jkopay_verify(params: dict) -> dict:
    """驗證街口回調。"""
    # 驗證簽章
    received_sig = params.get("X-Signature") or params.get("signature", "")
    body_str = params.get("_raw_body", "")
    if received_sig and body_str and JKOPAY_SECRET_KEY:
        expected = _jkopay_sign(body_str)
        if received_sig != expected:
            return {"ok": False, "error": "街口簽章驗證失敗", "paid": False}

    order_id = params.get("platform_order_id", "")
    status = params.get("status", "")
    paid = status in ("SUCCESS", "success")

    # 解析 metadata
    user_id = ""
    plan = ""
    try:
        meta = json.loads(params.get("metadata", "{}"))
        user_id = meta.get("user_id", "")
        plan = meta.get("plan", "")
    except Exception:
        pass

    order_status = "paid" if paid else "failed"
    _update_order_status(order_id, order_status)
    _db_save_payment(user_id, 0, "jkopay", order_id, plan, order_status)

    if paid and user_id and plan:
        _activate_user(user_id, plan)

    return {"ok": True, "paid": paid, "order_id": order_id, "user_id": user_id,
            "plan": plan, "method": "jkopay", "status": status}


def _jkopay_query(order_id: str) -> dict:
    if not JKOPAY_STORE_ID:
        return {"ok": False, "error": "街口支付未設定"}

    body = {
        "store_id": JKOPAY_STORE_ID,
        "platform_order_id": order_id,
    }
    resp = _jkopay_api("/platform/entry/api/v1/orders/query", body)
    return {"ok": True, "method": "jkopay", **resp}


# ══════════════════════════════════════════════════════════════
# 統一介面
# ══════════════════════════════════════════════════════════════

def list_methods() -> list[dict]:
    """列出所有可用支付方式（已設定 Key 的才顯示為 available）。"""
    result = []
    for mid, info in PAYMENT_METHODS.items():
        available = False
        if mid == "ecpay":
            available = bool(ECPAY_MERCHANT_ID)
        elif mid == "alipay":
            available = bool(ALIPAY_APP_ID)
        elif mid == "jkopay":
            available = bool(JKOPAY_STORE_ID)
        result.append({**info, "id": mid, "available": available})
    return result


def list_plans() -> list[dict]:
    """列出所有訂閱方案。"""
    return [{"id": pid, **p} for pid, p in PLANS.items()]


def create_order(
    method: str,
    user_id: str,
    plan: str,
    custom_amount: int = 0,
    item_name: str = "",
    **kwargs,
) -> dict[str, Any]:
    """
    統一建立訂單。

    Args:
        method: "ecpay" | "alipay" | "jkopay"
        user_id: 用戶 ID
        plan: 方案 ID（basic/pro/enterprise/...）
        custom_amount: 自訂金額（覆蓋方案價格）
        item_name: 商品名稱（選填）
    """
    if method not in PAYMENT_METHODS:
        return {"ok": False, "error": f"不支援的支付方式: {method}，可用: {', '.join(PAYMENT_METHODS.keys())}"}

    plan_info = PLANS.get(plan)
    if not plan_info and not custom_amount:
        return {"ok": False, "error": f"未知方案: {plan}，可用: {', '.join(PLANS.keys())}"}

    amount = custom_amount or (plan_info["price"] if plan_info else 0)
    if amount <= 0:
        return {"ok": False, "error": "金額必須大於 0"}

    name = item_name or f"築未科技 AI 平台 — {plan_info['name'] if plan_info else plan}"

    dispatch = {
        "ecpay": _ecpay_create,
        "alipay": _alipay_create,
        "jkopay": _jkopay_create,
    }
    return dispatch[method](user_id, plan, amount, name, **kwargs)


def verify_callback(method: str, params: dict) -> dict[str, Any]:
    """統一驗證回調。"""
    dispatch = {
        "ecpay": _ecpay_verify,
        "alipay": _alipay_verify,
        "jkopay": _jkopay_verify,
    }
    if method not in dispatch:
        return {"ok": False, "error": f"不支援的支付方式: {method}"}
    return dispatch[method](params)


def query_order(method: str, order_id: str) -> dict[str, Any]:
    """統一查詢訂單。"""
    # 先查本地
    local = _load_order(order_id)

    dispatch = {
        "ecpay": _ecpay_query,
        "alipay": _alipay_query,
        "jkopay": _jkopay_query,
    }
    if method not in dispatch:
        if local:
            return {"ok": True, **local}
        return {"ok": False, "error": f"不支援的支付方式: {method}"}

    remote = dispatch[method](order_id)
    if local:
        remote["local_status"] = local.get("status", "unknown")
    return remote


def get_order(order_id: str) -> dict:
    """取得本地訂單資訊。"""
    order = _load_order(order_id)
    if not order:
        return {"ok": False, "error": f"訂單不存在: {order_id}"}
    return {"ok": True, **order}


def list_orders(user_id: str = "", status: str = "", limit: int = 50) -> list[dict]:
    """列出訂單（從本地 JSON）。"""
    orders = []
    for f in sorted(ORDER_DIR.glob("ZW*.json"), reverse=True):
        try:
            o = json.loads(f.read_text(encoding="utf-8"))
            if user_id and o.get("user_id") != user_id:
                continue
            if status and o.get("status") != status:
                continue
            orders.append(o)
            if len(orders) >= limit:
                break
        except Exception:
            continue
    return orders


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

def _cli():
    import argparse
    parser = argparse.ArgumentParser(description="築未科技 統一金流閘道")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("methods", help="列出支付方式")
    sub.add_parser("plans", help="列出方案")

    c = sub.add_parser("create", help="建立訂單")
    c.add_argument("--method", required=True, choices=["ecpay", "alipay", "jkopay"])
    c.add_argument("--user", default="test_user")
    c.add_argument("--plan", default="pro")

    q = sub.add_parser("query", help="查詢訂單")
    q.add_argument("order_id")
    q.add_argument("--method", default="ecpay")

    sub.add_parser("orders", help="列出訂單")

    args = parser.parse_args()

    if args.cmd == "methods":
        for m in list_methods():
            avail = "✅" if m["available"] else "❌"
            print(f"  {avail} {m['icon']} {m['id']:8s} {m['name']:12s} — {m['desc']}")
    elif args.cmd == "plans":
        for p in list_plans():
            print(f"  {p['id']:12s} {p['name']:10s} NT${p['price']:>6,}  ({p['period']})")
    elif args.cmd == "create":
        r = create_order(args.method, args.user, args.plan)
        print(json.dumps({k: v for k, v in r.items() if k != "form_html"}, ensure_ascii=False, indent=2))
    elif args.cmd == "query":
        r = query_order(args.method, args.order_id)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif args.cmd == "orders":
        for o in list_orders():
            print(f"  {o.get('order_id','?'):20s} {o.get('method','?'):8s} {o.get('status','?'):8s} NT${o.get('amount',0):>6,}  {o.get('plan','?')}")
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()

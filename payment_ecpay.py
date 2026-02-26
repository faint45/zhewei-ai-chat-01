# -*- coding: utf-8 -*-
"""
築未科技 — 綠界 ECPay 金流整合模組

支援：
  - 信用卡一次付清
  - 信用卡定期定額（訂閱制）
  - ATM 虛擬帳號
  - 付款結果回調（ReturnURL / OrderResultURL）
  - 訂單查詢

環境變數：
  ECPAY_MERCHANT_ID     — 商店代號（測試：3002607）
  ECPAY_HASH_KEY        — HashKey
  ECPAY_HASH_IV         — HashIV
  ECPAY_RETURN_URL      — 付款結果回調 URL
  ECPAY_ORDER_RESULT_URL — 付款完成導向頁面
  ECPAY_SANDBOX         — 是否使用測試環境（預設 true）

綠界測試環境：
  MerchantID: 3002607
  HashKey: pwFHCqoQZGmho4w6
  HashIV: EkRm7iFT261dpevs
"""
import hashlib
import json
import os
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# ── 設定 ──
ECPAY_MERCHANT_ID = os.environ.get("ECPAY_MERCHANT_ID", "3002607").strip()
ECPAY_HASH_KEY = os.environ.get("ECPAY_HASH_KEY", "pwFHCqoQZGmho4w6").strip()
ECPAY_HASH_IV = os.environ.get("ECPAY_HASH_IV", "EkRm7iFT261dpevs").strip()
ECPAY_RETURN_URL = os.environ.get("ECPAY_RETURN_URL", "").strip()
ECPAY_ORDER_RESULT_URL = os.environ.get("ECPAY_ORDER_RESULT_URL", "").strip()
ECPAY_SANDBOX = os.environ.get("ECPAY_SANDBOX", "true").strip().lower() in ("true", "1", "yes")

# API 端點
_API_BASE = "https://payment-stage.ecpay.com.tw" if ECPAY_SANDBOX else "https://payment.ecpay.com.tw"
ECPAY_PAYMENT_URL = f"{_API_BASE}/Cashier/AioCheckOut/V5"
ECPAY_QUERY_URL = f"{_API_BASE}/Cashier/QueryTradeInfo/V5"
ECPAY_PERIOD_URL = f"{_API_BASE}/Cashier/AioCheckOut/V5"

# ── 訂閱方案定義 ──
PLANS = {
    "basic": {"name": "基礎版", "price": 499, "period": "monthly"},
    "pro": {"name": "專業版", "price": 999, "period": "monthly"},
    "enterprise": {"name": "企業版", "price": 4999, "period": "monthly"},
}


def _generate_check_mac_value(params: dict) -> str:
    """
    產生綠界檢查碼（CheckMacValue）。
    規則：HashKey + 參數依 key 排序 + HashIV → URL encode → 轉小寫 → SHA256 → 轉大寫
    """
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    raw = f"HashKey={ECPAY_HASH_KEY}&" + "&".join(f"{k}={v}" for k, v in sorted_params) + f"&HashIV={ECPAY_HASH_IV}"
    # URL encode（綠界規定的特殊編碼）
    encoded = urllib.parse.quote_plus(raw)
    # 綠界特殊字元還原
    encoded = encoded.replace("%2d", "-").replace("%5f", "_").replace("%2e", ".").replace("%21", "!")
    encoded = encoded.replace("%2a", "*").replace("%28", "(").replace("%29", ")")
    encoded = encoded.replace("%20", "+")
    encoded = encoded.lower()
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper()


def create_payment_order(
    user_id: str,
    plan: str,
    custom_amount: int = 0,
    item_name: str = "",
    return_url: str = "",
    order_result_url: str = "",
) -> dict[str, Any]:
    """
    建立付款訂單，回傳綠界表單 HTML（前端直接 render 即可自動跳轉）。

    Returns: {"ok": True, "order_id": "...", "form_html": "<form ...>"}
    """
    plan_info = PLANS.get(plan)
    if not plan_info and not custom_amount:
        return {"ok": False, "error": f"未知方案: {plan}"}

    amount = custom_amount or plan_info["price"]
    name = item_name or f"築未科技 AI 平台 — {plan_info['name'] if plan_info else plan}"

    # 訂單編號：ZW + 時間戳 + 用戶 ID 後 4 碼
    order_id = f"ZW{int(time.time())}{(user_id or 'anon')[-4:]}"

    params = {
        "MerchantID": ECPAY_MERCHANT_ID,
        "MerchantTradeNo": order_id[:20],
        "MerchantTradeDate": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
        "PaymentType": "aio",
        "TotalAmount": str(amount),
        "TradeDesc": urllib.parse.quote_plus("築未科技AI平台訂閱"),
        "ItemName": name[:200],
        "ReturnURL": return_url or ECPAY_RETURN_URL or "https://example.com/api/payment/callback",
        "OrderResultURL": order_result_url or ECPAY_ORDER_RESULT_URL or "",
        "ChoosePayment": "Credit",
        "EncryptType": "1",
        "NeedExtraPaidInfo": "Y",
        "CustomField1": user_id[:50] if user_id else "",
        "CustomField2": plan[:50] if plan else "",
    }

    # 移除空值
    params = {k: v for k, v in params.items() if v}

    # 產生檢查碼
    params["CheckMacValue"] = _generate_check_mac_value(params)

    # 產生自動提交表單 HTML
    form_fields = "\n".join(
        f'<input type="hidden" name="{k}" value="{v}">' for k, v in params.items()
    )
    form_html = f"""
    <form id="ecpay_form" method="POST" action="{ECPAY_PAYMENT_URL}">
        {form_fields}
    </form>
    <script>document.getElementById('ecpay_form').submit();</script>
    """

    # 記錄到 PG
    try:
        import db_postgres
        conn = db_postgres._get_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO payments (user_id, amount_ntd, payment_method, payment_id, status, plan, metadata)
               VALUES (%s::UUID, %s, 'ecpay', %s, 'pending', %s, %s)""",
            (user_id if user_id and user_id != "anonymous" else None,
             amount, order_id, plan,
             json.dumps({"params": {k: v for k, v in params.items() if k != "CheckMacValue"}}, ensure_ascii=False)),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass

    return {
        "ok": True,
        "order_id": order_id,
        "amount": amount,
        "plan": plan,
        "form_html": form_html,
        "payment_url": ECPAY_PAYMENT_URL,
        "sandbox": ECPAY_SANDBOX,
    }


def create_subscription_order(
    user_id: str,
    plan: str,
    return_url: str = "",
    order_result_url: str = "",
) -> dict[str, Any]:
    """
    建立定期定額訂閱訂單（信用卡自動扣款）。
    """
    plan_info = PLANS.get(plan)
    if not plan_info:
        return {"ok": False, "error": f"未知方案: {plan}"}

    amount = plan_info["price"]
    name = f"築未科技 AI 平台 — {plan_info['name']}（月繳）"
    order_id = f"ZW{int(time.time())}{(user_id or 'anon')[-4:]}"

    params = {
        "MerchantID": ECPAY_MERCHANT_ID,
        "MerchantTradeNo": order_id[:20],
        "MerchantTradeDate": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
        "PaymentType": "aio",
        "TotalAmount": str(amount),
        "TradeDesc": urllib.parse.quote_plus("築未科技AI平台月繳訂閱"),
        "ItemName": name[:200],
        "ReturnURL": return_url or ECPAY_RETURN_URL or "https://example.com/api/payment/callback",
        "OrderResultURL": order_result_url or ECPAY_ORDER_RESULT_URL or "",
        "ChoosePayment": "Credit",
        "EncryptType": "1",
        "NeedExtraPaidInfo": "Y",
        "CustomField1": user_id[:50] if user_id else "",
        "CustomField2": plan[:50] if plan else "",
        # 定期定額參數
        "PeriodAmount": str(amount),
        "PeriodType": "M",       # M=月
        "Frequency": "1",        # 每 1 個月
        "ExecTimes": "12",       # 執行 12 次（1 年）
        "PeriodReturnURL": return_url or ECPAY_RETURN_URL or "",
    }

    params = {k: v for k, v in params.items() if v}
    params["CheckMacValue"] = _generate_check_mac_value(params)

    form_fields = "\n".join(
        f'<input type="hidden" name="{k}" value="{v}">' for k, v in params.items()
    )
    form_html = f"""
    <form id="ecpay_form" method="POST" action="{ECPAY_PERIOD_URL}">
        {form_fields}
    </form>
    <script>document.getElementById('ecpay_form').submit();</script>
    """

    try:
        import db_postgres
        conn = db_postgres._get_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO payments (user_id, amount_ntd, payment_method, payment_id, status, plan, metadata)
               VALUES (%s::UUID, %s, 'ecpay_period', %s, 'pending', %s, %s)""",
            (user_id if user_id and user_id != "anonymous" else None,
             amount, order_id, plan,
             json.dumps({"type": "subscription", "period": "monthly"}, ensure_ascii=False)),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass

    return {
        "ok": True,
        "order_id": order_id,
        "amount": amount,
        "plan": plan,
        "type": "subscription",
        "form_html": form_html,
        "sandbox": ECPAY_SANDBOX,
    }


def verify_callback(params: dict) -> dict[str, Any]:
    """
    驗證綠界回調（ReturnURL / PeriodReturnURL）。
    綠界會 POST 付款結果到 ReturnURL，需驗證 CheckMacValue。

    Returns: {"ok": True, "paid": True/False, "order_id": "...", "user_id": "...", "plan": "..."}
    """
    received_mac = params.get("CheckMacValue", "")
    # 移除 CheckMacValue 後重新計算
    check_params = {k: v for k, v in params.items() if k != "CheckMacValue"}
    expected_mac = _generate_check_mac_value(check_params)

    if received_mac != expected_mac:
        return {"ok": False, "error": "CheckMacValue 驗證失敗", "paid": False}

    rtn_code = params.get("RtnCode", "")
    order_id = params.get("MerchantTradeNo", "")
    user_id = params.get("CustomField1", "")
    plan = params.get("CustomField2", "")
    trade_no = params.get("TradeNo", "")
    amount = params.get("TradeAmt", "0")

    paid = rtn_code == "1"

    # 更新 PG 付款狀態
    try:
        import db_postgres
        conn = db_postgres._get_conn()
        cur = conn.cursor()
        cur.execute(
            """UPDATE payments SET status = %s, updated_at = NOW(),
                      metadata = metadata || %s::jsonb
               WHERE payment_id = %s""",
            ("paid" if paid else "failed",
             json.dumps({"trade_no": trade_no, "rtn_code": rtn_code, "rtn_msg": params.get("RtnMsg", "")}),
             order_id),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass

    # 付款成功 → 自動啟用訂閱
    if paid and user_id and plan:
        try:
            import auth_manager
            auth_manager.activate_subscription(user_id, plan)
        except Exception:
            pass

    return {
        "ok": True,
        "paid": paid,
        "order_id": order_id,
        "trade_no": trade_no,
        "user_id": user_id,
        "plan": plan,
        "amount": int(amount) if amount.isdigit() else 0,
        "rtn_code": rtn_code,
        "rtn_msg": params.get("RtnMsg", ""),
    }


def query_trade(order_id: str) -> dict[str, Any]:
    """查詢訂單狀態。"""
    import urllib.request

    params = {
        "MerchantID": ECPAY_MERCHANT_ID,
        "MerchantTradeNo": order_id[:20],
        "TimeStamp": str(int(time.time())),
    }
    params["CheckMacValue"] = _generate_check_mac_value(params)

    data = urllib.parse.urlencode(params).encode("utf-8")
    try:
        req = urllib.request.Request(ECPAY_QUERY_URL, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            result = dict(urllib.parse.parse_qsl(body))
            return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}

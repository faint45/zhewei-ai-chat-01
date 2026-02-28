# -*- coding: utf-8 -*-
"""
金流回調 E2E 測試
═══════════════════════════════════════════
測試鏈路：
  1. CheckMacValue 計算正確性
  2. verify_callback 成功/失敗路徑
  3. 付款成功 → activate_subscription 觸發
  4. 統一金流閘道 (payment_gateway) 路由
  5. HTTP 端點回調模擬

執行：
  python tests/test_payment_e2e.py
  docker exec zhewei_brain python tests/test_payment_e2e.py
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASSED = 0
FAILED = 0
ERRORS = []


def _test(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print(f"  ✅ {name}")
    except AssertionError as e:
        FAILED += 1
        ERRORS.append(f"{name}: {e}")
        print(f"  ❌ {name} — {e}")
    except Exception as e:
        FAILED += 1
        ERRORS.append(f"{name}: {type(e).__name__}: {e}")
        print(f"  💥 {name} — {type(e).__name__}: {e}")


# ── Test 1: CheckMacValue 計算 ──
def test_check_mac_value():
    import payment_ecpay as pe
    params = {
        "MerchantID": "3002607",
        "MerchantTradeNo": "ZW1234567890test",
        "MerchantTradeDate": "2026/02/27 23:00:00",
        "PaymentType": "aio",
        "TotalAmount": "1500",
        "TradeDesc": "test",
        "ItemName": "專業版",
        "ReturnURL": "https://jarvis.zhe-wei.net/api/payment/callback",
        "ChoosePayment": "Credit",
        "EncryptType": "1",
        "NeedExtraPaidInfo": "Y",
        "CustomField1": "test-user-001",
        "CustomField2": "pro",
    }
    mac = pe._generate_check_mac_value(params)
    assert isinstance(mac, str) and len(mac) == 64, f"MAC 長度錯誤: {len(mac)}"
    assert mac == mac.upper(), "MAC 應為大寫"
    mac2 = pe._generate_check_mac_value(params)
    assert mac == mac2, "相同參數應產生相同 MAC"
    params2 = {**params, "TotalAmount": "999"}
    mac3 = pe._generate_check_mac_value(params2)
    assert mac != mac3, "不同參數應產生不同 MAC"


# ── Test 2: verify_callback 成功 ──
def test_verify_callback_success():
    import payment_ecpay as pe
    cb = {
        "MerchantID": pe.ECPAY_MERCHANT_ID,
        "MerchantTradeNo": f"ZWtest{int(time.time())}",
        "RtnCode": "1", "RtnMsg": "Succeeded",
        "TradeNo": "2402271234567", "TradeAmt": "1500",
        "PaymentDate": "2026/02/27 23:30:00",
        "PaymentType": "Credit_CreditCard",
        "TradeDate": "2026/02/27 23:25:00",
        "CustomField1": "test-e2e-user", "CustomField2": "pro",
    }
    cb["CheckMacValue"] = pe._generate_check_mac_value(cb)
    r = pe.verify_callback(cb)
    assert r["ok"] is True, f"verify 應成功: {r}"
    assert r["paid"] is True, "RtnCode=1 → paid=True"
    assert r["user_id"] == "test-e2e-user"
    assert r["plan"] == "pro"
    assert r["amount"] == 1500


# ── Test 3: verify_callback MAC 錯誤 ──
def test_verify_callback_bad_mac():
    import payment_ecpay as pe
    cb = {
        "MerchantID": pe.ECPAY_MERCHANT_ID,
        "MerchantTradeNo": "ZWtestBADMAC",
        "RtnCode": "1", "RtnMsg": "Succeeded",
        "TradeNo": "fake123", "TradeAmt": "999",
        "CustomField1": "hacker", "CustomField2": "enterprise",
        "CheckMacValue": "DEADBEEF" * 8,
    }
    r = pe.verify_callback(cb)
    assert r["ok"] is False, "假 MAC 應失敗"
    assert r["paid"] is False


# ── Test 4: verify_callback 付款失敗 ──
def test_verify_callback_payment_failed():
    import payment_ecpay as pe
    cb = {
        "MerchantID": pe.ECPAY_MERCHANT_ID,
        "MerchantTradeNo": f"ZWfail{int(time.time())}",
        "RtnCode": "10100058", "RtnMsg": "付款失敗",
        "TradeNo": "2402270000000", "TradeAmt": "499",
        "CustomField1": "test-fail-user", "CustomField2": "basic",
    }
    cb["CheckMacValue"] = pe._generate_check_mac_value(cb)
    r = pe.verify_callback(cb)
    assert r["ok"] is True, "MAC 正確，verify 應成功"
    assert r["paid"] is False, "RtnCode!=1 → paid=False"


# ── Test 5: 統一金流閘道路由 ──
def test_gateway_routing():
    try:
        import payment_gateway as gw
    except ImportError:
        print("  ⏭️  payment_gateway 未安裝，跳過")
        return
    r = gw.create_order("ecpay", "test-gw-user", "pro", 0, "")
    assert r["ok"] is True, f"ECPay 建單失敗: {r}"
    assert r["method"] == "ecpay"
    assert r["sandbox"] is True, "應為 sandbox 模式"
    assert "form_html" in r
    if not os.environ.get("ALIPAY_APP_ID"):
        r2 = gw.create_order("alipay", "test-gw-user", "pro", 0, "")
        assert r2["ok"] is False, "無 ALIPAY_APP_ID 應失敗"
    if not os.environ.get("JKOPAY_STORE_ID"):
        r3 = gw.create_order("jkopay", "test-gw-user", "pro", 0, "")
        assert r3["ok"] is False, "無 JKOPAY_STORE_ID 應失敗"
    methods = gw.list_methods()
    assert len(methods) >= 1, "至少應有 1 個支付方式"


# ── Test 6: 訂閱啟用鏈路 ──
def test_subscription_activation():
    import auth_manager
    test_uid = f"e2e-pay-{int(time.time())}"
    reg = auth_manager.register_user(test_uid, "TestPass123!", f"{test_uid}@test.com")
    uid = reg.get("user_id", test_uid)
    r = auth_manager.activate_subscription(uid, "pro")
    assert r.get("ok") is True, f"啟用失敗: {r}"
    assert r.get("subscription") == "active"
    info = auth_manager.get_user_info(uid)
    if info:
        assert info.get("subscription") == "active", f"狀態應為 active: {info}"


# ── Test 7: HTTP /api/payment/callback ──
def test_http_callback_endpoint():
    import payment_ecpay as pe
    BASE = os.environ.get("BRAIN_URL", "http://localhost:8002")
    cb = {
        "MerchantID": pe.ECPAY_MERCHANT_ID,
        "MerchantTradeNo": f"ZWhttp{int(time.time())}",
        "RtnCode": "1", "RtnMsg": "Succeeded",
        "TradeNo": "2402279999999", "TradeAmt": "1500",
        "PaymentDate": "2026/02/27 23:35:00",
        "PaymentType": "Credit_CreditCard",
        "TradeDate": "2026/02/27 23:30:00",
        "CustomField1": "http-test-user", "CustomField2": "pro",
    }
    cb["CheckMacValue"] = pe._generate_check_mac_value(cb)
    data = urllib.parse.urlencode(cb).encode("utf-8")
    try:
        req = urllib.request.Request(f"{BASE}/api/payment/callback", data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            assert "1|OK" in body, f"應回傳 '1|OK'，實際: {body}"
    except urllib.error.URLError as e:
        print(f"  ⚠️  brain_server 未運行 ({e})，跳過")


# ── Test 8: HTTP /api/gateway/callback/ecpay ──
def test_http_gateway_callback():
    import payment_ecpay as pe
    BASE = os.environ.get("BRAIN_URL", "http://localhost:8002")
    cb = {
        "MerchantID": pe.ECPAY_MERCHANT_ID,
        "MerchantTradeNo": f"ZWgw{int(time.time())}",
        "RtnCode": "1", "RtnMsg": "Succeeded",
        "TradeNo": "2402278888888", "TradeAmt": "8000",
        "PaymentDate": "2026/02/27 23:36:00",
        "PaymentType": "Credit_CreditCard",
        "TradeDate": "2026/02/27 23:35:00",
        "CustomField1": "gw-test-user", "CustomField2": "enterprise",
    }
    cb["CheckMacValue"] = pe._generate_check_mac_value(cb)
    data = urllib.parse.urlencode(cb).encode("utf-8")
    try:
        req = urllib.request.Request(f"{BASE}/api/gateway/callback/ecpay", data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            assert "1|OK" in body, f"Gateway 應回傳 '1|OK'，實際: {body}"
    except urllib.error.URLError as e:
        print(f"  ⚠️  brain_server 未運行 ({e})，跳過")


if __name__ == "__main__":
    print("=" * 60)
    print("金流回調 E2E 測試")
    print("=" * 60)
    print("\n📋 Unit Tests（不需 server）")
    _test("CheckMacValue 計算", test_check_mac_value)
    _test("verify_callback 成功", test_verify_callback_success)
    _test("verify_callback MAC 錯誤", test_verify_callback_bad_mac)
    _test("verify_callback 付款失敗", test_verify_callback_payment_failed)
    _test("統一金流閘道路由", test_gateway_routing)
    _test("訂閱啟用鏈路", test_subscription_activation)
    print("\n🌐 Integration Tests（需 brain_server 運行）")
    _test("HTTP /api/payment/callback", test_http_callback_endpoint)
    _test("HTTP /api/gateway/callback/ecpay", test_http_gateway_callback)
    print("\n" + "=" * 60)
    total = PASSED + FAILED
    print(f"結果: {PASSED}/{total} 通過, {FAILED} 失敗")
    if ERRORS:
        print("\n失敗詳情:")
        for e in ERRORS:
            print(f"  • {e}")
    print("=" * 60)
    sys.exit(1 if FAILED else 0)

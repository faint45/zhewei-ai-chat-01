# -*- coding: utf-8 -*-
"""築未科技 — 商用 API Router (License + KB同步 + 租戶 + 付款 + 金流 + Revenue)"""
import asyncio
import json
import os

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from routers.deps import (
    _extract_token, _require_admin, _require_superadmin,
    auth_manager, sec_mw, smart_ai, logger, ROOT,
)

router = APIRouter(tags=["商用"])

# ── Optional modules ──
try:
    import license_manager
except ImportError:
    license_manager = None

try:
    import kb_snapshot
except ImportError:
    kb_snapshot = None

try:
    import tenant_manager
except ImportError:
    tenant_manager = None

try:
    import payment_ecpay
except ImportError:
    payment_ecpay = None

try:
    import payment_gateway
except ImportError:
    payment_gateway = None

try:
    import usage_metering
except ImportError:
    usage_metering = None

try:
    from revenue_platform import get_platform as get_revenue_platform
    REVENUE_PLATFORM_AVAILABLE = True
except ImportError:
    REVENUE_PLATFORM_AVAILABLE = False


# ── License 管理 ──
@router.get("/api/commercial/license/validate")
async def api_license_validate():
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    return {"ok": True, **license_manager.validate_license()}


@router.post("/api/commercial/license/activate")
async def api_license_activate(request: Request):
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    body = await request.json()
    data = body.get("license_data", "")
    if not data:
        raise HTTPException(400, "license_data is required")
    return license_manager.activate_license(data, bind_device=body.get("bind_device", True))


@router.get("/api/commercial/license/offline-check")
async def api_license_offline_check():
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    return license_manager.check_offline_grace()


@router.post("/api/commercial/license/online-verify")
async def api_license_online_verify():
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    result = license_manager.validate_license()
    if result.get("valid"):
        license_manager.update_online_check()
        return {"ok": True, "message": "連線驗證成功", **result}
    return {"ok": False, **result}


@router.post("/api/commercial/license/generate")
async def api_license_generate(request: Request):
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    _require_superadmin(request)
    body = await request.json()
    return license_manager.generate_license(
        customer_name=body.get("customer_name", ""), tier=body.get("tier", "professional"),
        duration_days=body.get("duration_days", 365), device_fingerprint=body.get("device_fingerprint", ""),
        max_devices=body.get("max_devices", 1), notes=body.get("notes", ""),
    )


@router.get("/api/commercial/license/list")
async def api_license_list(request: Request):
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    _require_admin(request)
    return {"ok": True, "licenses": license_manager.list_licenses()}


@router.post("/api/commercial/license/revoke")
async def api_license_revoke(request: Request):
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    _require_superadmin(request)
    body = await request.json()
    lid = body.get("license_id", "")
    if not lid:
        raise HTTPException(400, "license_id is required")
    return license_manager.revoke_license(lid)


@router.get("/api/commercial/device-info")
async def api_device_info():
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    import platform
    return {"ok": True, "fingerprint": license_manager.get_device_fingerprint(), "hostname": platform.node(), "os": f"{platform.system()} {platform.release()}", "arch": platform.machine()}


@router.get("/api/commercial/features")
async def api_commercial_features(request: Request):
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    data = _extract_token(request)
    return {"ok": True, **license_manager.get_user_features(data or {})}


# ── KB 同步 ──
@router.get("/api/commercial/kb/snapshot-info")
async def api_kb_snapshot_info():
    if not kb_snapshot:
        return {"ok": False, "error": "知識庫快照模組未安裝"}
    return {"ok": True, **kb_snapshot.get_snapshot_info()}


@router.get("/api/commercial/kb/snapshots")
async def api_kb_snapshots():
    if not kb_snapshot:
        return {"ok": False, "error": "知識庫快照模組未安裝"}
    return {"ok": True, "snapshots": kb_snapshot.list_snapshots()}


@router.post("/api/commercial/kb/export")
async def api_kb_export(request: Request):
    if not kb_snapshot:
        return {"ok": False, "error": "知識庫快照模組未安裝"}
    _require_admin(request)
    body = await request.json()
    return kb_snapshot.export_snapshot(collection_name=body.get("collection", ""), include_embeddings=body.get("include_embeddings", True), compress=body.get("compress", True), max_items=body.get("max_items", -1))


@router.post("/api/commercial/kb/export-delta")
async def api_kb_export_delta(request: Request):
    if not kb_snapshot:
        return {"ok": False, "error": "知識庫快照模組未安裝"}
    _require_admin(request)
    body = await request.json()
    since = body.get("since_version", 0)
    if not since:
        raise HTTPException(400, "since_version is required")
    return kb_snapshot.export_delta(since_version=since, collection_name=body.get("collection", ""))


@router.post("/api/commercial/kb/import")
async def api_kb_import(request: Request):
    if not kb_snapshot:
        return {"ok": False, "error": "知識庫快照模組未安裝"}
    body = await request.json()
    snapshot_file = body.get("snapshot_file", "")
    if not snapshot_file:
        raise HTTPException(400, "snapshot_file is required")
    return kb_snapshot.import_snapshot(snapshot_file=snapshot_file, collection_name=body.get("collection", ""), skip_existing=body.get("skip_existing", True))


@router.get("/api/commercial/kb/check-update")
async def api_kb_check_update(client_version: int = 0):
    if not kb_snapshot:
        return {"ok": False, "error": "知識庫快照模組未安裝"}
    info = kb_snapshot.get_snapshot_info()
    sv = info.get("current_version", 0)
    return {"ok": True, "has_update": sv > client_version, "server_version": sv, "client_version": client_version, "versions_behind": sv - client_version if sv > client_version else 0}


# ── 遠端加強 ──
@router.post("/api/commercial/remote-enhance")
async def api_remote_enhance(request: Request):
    if license_manager:
        lic = license_manager.validate_license()
        if not lic.get("valid"):
            return {"ok": False, "error": "License 無效或已過期", "need_license": True}
        if lic.get("remote_calls_per_month", 0) == 0:
            return {"ok": False, "error": "免費版不支援遠端加強，請升級方案"}
    token_data = _extract_token(request)
    uid = (token_data or {}).get("sub", "anonymous")
    if usage_metering:
        plan = "free"
        if token_data and uid != "anonymous":
            user_info = auth_manager.get_user_info(uid)
            if user_info:
                plan = user_info.get("subscription_plan", "") or "free"
        quota = usage_metering.check_quota(uid, plan)
        if not quota.get("allowed", True):
            return {"ok": False, "error": "本月配額已用完", "quota": quota}
    body = await request.json()
    messages = body.get("messages", [])
    task_type = body.get("task_type", "think")
    if not messages:
        raise HTTPException(400, "messages is required")
    import time as _time
    start = _time.time()
    try:
        result = await smart_ai.generate(messages[-1].get("content", "") if messages else "", context="\n".join(m.get("content", "") for m in messages[:-1]) if len(messages) > 1 else "")
        duration_ms = int((_time.time() - start) * 1000)
        if usage_metering:
            usage_metering.record_usage(provider=result.get("provider", "unknown"), model=result.get("model", "unknown"), input_tokens=usage_metering.estimate_tokens(str(messages)), output_tokens=usage_metering.estimate_tokens(result.get("text", "")), duration_ms=duration_ms, user_id=uid, task_type=task_type)
        return {"ok": True, "text": result.get("text", ""), "provider": result.get("provider", ""), "model": result.get("model", ""), "duration_ms": duration_ms}
    except Exception as e:
        if usage_metering:
            usage_metering.record_usage(provider="error", model="", duration_ms=int((_time.time() - start) * 1000), success=False, error_msg=str(e)[:200], user_id=uid, task_type=task_type)
        return {"ok": False, "error": str(e)[:300]}


@router.get("/api/commercial/system-status")
async def api_commercial_system_status(request: Request):
    status = {}
    if license_manager:
        lic = license_manager.validate_license()
        offline = license_manager.check_offline_grace()
        status["license"] = {"valid": lic.get("valid", False), "tier": lic.get("tier", "free"), "tier_name": lic.get("tier_name", ""), "customer_name": lic.get("customer_name", ""), "days_remaining": lic.get("days_remaining", 0), "expires_at": lic.get("expires_at", "")}
        status["offline"] = {"ok": offline.get("ok", False), "days_offline": offline.get("days_offline", 0), "grace_remaining": offline.get("days_remaining_offline", 0)}
    else:
        status["license"] = {"valid": False, "tier": "free"}
        status["offline"] = {"ok": False}
    if usage_metering:
        status["usage_today"] = usage_metering.get_today_summary()
        token_data = _extract_token(request)
        uid = (token_data or {}).get("sub", "anonymous")
        plan = "free"
        if token_data and uid != "anonymous":
            user_info = auth_manager.get_user_info(uid)
            if user_info:
                plan = user_info.get("subscription_plan", "") or "free"
        status["quota"] = usage_metering.check_quota(uid, plan)
    else:
        status["usage_today"] = {}
        status["quota"] = {}
    if kb_snapshot:
        status["kb_version"] = kb_snapshot.get_snapshot_info()
    else:
        status["kb_version"] = {"current_version": 0}
    return {"ok": True, **status}


# ── 租戶管理 ──
@router.get("/api/tenants")
async def api_list_tenants(request: Request):
    _require_admin(request)
    try:
        import db_postgres
        tenants = db_postgres.list_tenants()
        return {"ok": True, "tenants": tenants, "count": len(tenants)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/tenants")
async def api_create_tenant(request: Request):
    _require_admin(request)
    payload = await request.json()
    name = str((payload or {}).get("name", "")).strip()
    slug = str((payload or {}).get("slug", "")).strip()
    plan = str((payload or {}).get("plan", "free")).strip()
    if not name or not slug:
        raise HTTPException(400, "name and slug are required")
    try:
        import db_postgres
        return db_postgres.create_tenant(name, slug, plan)
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/tenants/{tenant_slug}/stats")
async def api_tenant_stats(tenant_slug: str):
    if not tenant_manager:
        return {"ok": False, "error": "租戶模組未安裝"}
    try:
        return tenant_manager.tenant_stats(tenant_slug)
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/tenants/{tenant_slug}/kb-quota")
async def api_tenant_kb_quota(tenant_slug: str):
    if not tenant_manager:
        return {"ok": False, "error": "租戶模組未安裝"}
    try:
        import db_postgres
        t = db_postgres.get_tenant_by_slug(tenant_slug)
        plan = t.get("plan", "free") if t else "free"
        return {"ok": True, **tenant_manager.check_kb_quota(tenant_slug, plan)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/tenants/{tenant_slug}/roles/{role_id}/learn")
async def api_tenant_role_learn(tenant_slug: str, role_id: str, request: Request):
    if not tenant_manager:
        return {"ok": False, "error": "租戶模組未安裝"}
    payload = await request.json()
    question = str((payload or {}).get("question", "")).strip()
    answer = str((payload or {}).get("answer", "")).strip()
    source = str((payload or {}).get("source", "api")).strip()
    if not question or not answer:
        raise HTTPException(400, "question and answer are required")
    try:
        return await asyncio.to_thread(tenant_manager.tenant_role_learn, tenant_slug, role_id, question, answer, source)
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/tenants/{tenant_slug}/roles/{role_id}/search")
async def api_tenant_role_search(tenant_slug: str, role_id: str, request: Request):
    if not tenant_manager:
        return {"ok": False, "error": "租戶模組未安裝"}
    payload = await request.json()
    query = str((payload or {}).get("query", "")).strip()
    top_k = int((payload or {}).get("top_k", 5) or 5)
    include_master = bool((payload or {}).get("include_master", True))
    if not query:
        raise HTTPException(400, "query is required")
    try:
        hits = await asyncio.to_thread(tenant_manager.tenant_role_search, tenant_slug, role_id, query, top_k, include_master)
        return {"ok": True, "hits": hits, "count": len(hits)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── 付款（ECPay）──
@router.post("/api/payment/create")
async def api_payment_create(request: Request):
    if not payment_ecpay:
        return {"ok": False, "error": "付款模組未安裝"}
    data = _extract_token(request)
    uid = (data or {}).get("sub", "anonymous")
    payload = await request.json()
    plan = str((payload or {}).get("plan", "basic")).strip()
    return payment_ecpay.create_payment_order(uid, plan)


@router.post("/api/payment/subscribe")
async def api_payment_subscribe(request: Request):
    if not payment_ecpay:
        return {"ok": False, "error": "付款模組未安裝"}
    data = _extract_token(request)
    uid = (data or {}).get("sub", "anonymous")
    payload = await request.json()
    plan = str((payload or {}).get("plan", "pro")).strip()
    return payment_ecpay.create_subscription_order(uid, plan)


@router.post("/api/payment/callback")
async def api_payment_callback(request: Request):
    if not payment_ecpay:
        return "0|ERROR"
    if sec_mw:
        client_ip = sec_mw.get_client_ip(request)
        if not sec_mw.is_ecpay_ip_allowed(client_ip):
            logger.warning("ECPay callback rejected: IP %s", client_ip)
            return "0|ERROR"
    try:
        form = await request.form()
        params = {k: v for k, v in form.items()}
        result = payment_ecpay.verify_callback(params)
        if result.get("paid"):
            logger.info("Payment success: order=%s user=%s plan=%s", result.get("order_id"), result.get("user_id"), result.get("plan"))
        return "1|OK" if result.get("ok") else "0|ERROR"
    except Exception as e:
        logger.error("Payment callback error: %s", e)
        return "0|ERROR"


@router.get("/api/payment/query/{order_id}")
async def api_payment_query(order_id: str):
    if not payment_ecpay:
        return {"ok": False, "error": "付款模組未安裝"}
    return payment_ecpay.query_trade(order_id)


@router.get("/api/payment/plans")
async def api_payment_plans():
    if not payment_ecpay:
        return {"ok": False, "error": "付款模組未安裝"}
    plans = [{"id": pid, "name": p["name"], "price_ntd": p["price"], "period": p["period"]} for pid, p in payment_ecpay.PLANS.items()]
    return {"ok": True, "plans": plans, "sandbox": payment_ecpay.ECPAY_SANDBOX}


# ── 統一金流 ──
@router.get("/api/gateway/methods")
async def api_gateway_methods():
    if not payment_gateway:
        return {"ok": False, "error": "統一金流模組未安裝"}
    return {"ok": True, "methods": payment_gateway.list_methods()}


@router.get("/api/gateway/plans")
async def api_gateway_plans():
    if not payment_gateway:
        return {"ok": False, "error": "統一金流模組未安裝"}
    return {"ok": True, "plans": payment_gateway.list_plans()}


@router.post("/api/gateway/create")
async def api_gateway_create(request: Request):
    if not payment_gateway:
        return {"ok": False, "error": "統一金流模組未安裝"}
    data = _extract_token(request)
    uid = (data or {}).get("sub", "anonymous")
    payload = await request.json()
    return payment_gateway.create_order(str((payload or {}).get("method", "ecpay")).strip(), uid, str((payload or {}).get("plan", "pro")).strip(), int((payload or {}).get("custom_amount", 0) or 0), str((payload or {}).get("item_name", "")).strip())


@router.post("/api/gateway/callback/{method}")
async def api_gateway_callback(method: str, request: Request):
    if not payment_gateway:
        return "0|ERROR"
    try:
        content_type = request.headers.get("content-type", "")
        if "json" in content_type:
            raw_body = await request.body()
            params = json.loads(raw_body)
            params["_raw_body"] = raw_body.decode("utf-8", errors="ignore")
        else:
            form = await request.form()
            params = {k: v for k, v in form.items()}
        sig = request.headers.get("X-Signature", "")
        if sig:
            params["X-Signature"] = sig
        result = payment_gateway.verify_callback(method, params)
        if result.get("paid"):
            logger.info("[%s] Payment success: order=%s", method, result.get("order_id"))
        if method == "ecpay":
            return "1|OK" if result.get("ok") else "0|ERROR"
        if method == "alipay":
            return "success" if result.get("ok") else "fail"
        return result
    except Exception as e:
        logger.error("[%s] Payment callback error: %s", method, e)
        return "0|ERROR" if method == "ecpay" else {"ok": False, "error": str(e)}


@router.get("/api/gateway/return/{method}")
async def api_gateway_return(method: str, request: Request):
    params = dict(request.query_params)
    order_id = params.get("MerchantTradeNo") or params.get("out_trade_no") or params.get("platform_order_id", "")
    return HTMLResponse(f'<html><head><meta charset="utf-8"><title>付款處理中</title></head><body style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;background:#0f172a;color:#e2e8f0"><div style="text-align:center"><h2>✅ 付款處理中</h2><p>訂單編號: {order_id}</p><p><a href="/jarvis" style="color:#0ea5e9">← 返回系統</a></p></div></body></html>')


@router.get("/api/gateway/query/{order_id}")
async def api_gateway_query(order_id: str, method: str = ""):
    if not payment_gateway:
        return {"ok": False, "error": "統一金流模組未安裝"}
    if not method:
        method = "alipay" if order_id.startswith("ZWA") else "jkopay" if order_id.startswith("ZWJ") else "ecpay"
    return payment_gateway.query_order(method, order_id)


@router.get("/api/gateway/orders")
async def api_gateway_orders(request: Request, status: str = "", limit: int = 50):
    if not payment_gateway:
        return {"ok": False, "error": "統一金流模組未安裝"}
    _require_admin(request)
    orders = payment_gateway.list_orders(status=status, limit=limit)
    return {"ok": True, "orders": orders, "count": len(orders)}


# ── Revenue Platform ──
@router.get("/api/revenue/summary")
async def api_revenue_summary():
    if not REVENUE_PLATFORM_AVAILABLE:
        return {"ok": False, "error": "Revenue Platform 未安裝"}
    return get_revenue_platform().get_revenue_summary()


@router.get("/api/revenue/products")
async def api_revenue_products():
    if not REVENUE_PLATFORM_AVAILABLE:
        return {"ok": False, "error": "Revenue Platform 未安裝"}
    return get_revenue_platform().get_products()


@router.get("/api/revenue/products/{product}/plans")
async def api_revenue_product_plans(product: str):
    if not REVENUE_PLATFORM_AVAILABLE:
        return {"ok": False, "error": "Revenue Platform 未安裝"}
    return get_revenue_platform().get_product_plans(product)


@router.post("/api/revenue/subscribe")
async def api_revenue_subscribe(request: Request):
    if not REVENUE_PLATFORM_AVAILABLE:
        return {"ok": False, "error": "Revenue Platform 未安裝"}
    data = await request.json()
    return get_revenue_platform().create_subscription(data.get("user_id", "anonymous"), data.get("product", ""), data.get("plan", ""))


@router.get("/api/revenue/subscriptions")
async def api_revenue_subscriptions(product: str = None):
    if not REVENUE_PLATFORM_AVAILABLE:
        return {"ok": False, "error": "Revenue Platform 未安裝"}
    subs = get_revenue_platform().get_active_subscriptions(product)
    return {"ok": True, "subscriptions": subs}


@router.get("/api/revenue/usage")
async def api_revenue_usage(product: str = None, days: int = 30):
    if not REVENUE_PLATFORM_AVAILABLE:
        return {"ok": False, "error": "Revenue Platform 未安裝"}
    return get_revenue_platform().get_usage_stats(product, days)


@router.get("/api/revenue/suggestions")
async def api_revenue_suggestions():
    if not REVENUE_PLATFORM_AVAILABLE:
        return {"ok": False, "error": "Revenue Platform 未安裝"}
    return {"ok": True, "suggestions": get_revenue_platform().get_growth_suggestions()}

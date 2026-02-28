# -*- coding: utf-8 -*-
"""築未科技 — 用量 + 監控 + 營運通知 Router"""
import json
from fastapi import APIRouter, Request, HTTPException
from routers.deps import _extract_token, _require_admin, auth_manager, logger

router = APIRouter(tags=["用量監控"])

# ── Optional modules ──
try:
    import usage_metering
except ImportError:
    usage_metering = None

try:
    from ai_usage_tracker import usage_tracker
    USAGE_TRACKER_AVAILABLE = True
except ImportError:
    USAGE_TRACKER_AVAILABLE = False

try:
    import structured_logger
except ImportError:
    structured_logger = None

try:
    import ops_notify
except ImportError:
    ops_notify = None

try:
    from ai_usage_alerts import alerts_manager
    USAGE_ALERTS_AVAILABLE = True
except ImportError:
    USAGE_ALERTS_AVAILABLE = False


# ── 用量計量 ──
@router.get("/api/usage/today")
async def api_usage_today():
    if not usage_metering:
        return {"ok": False, "error": "用量計量模組未安裝"}
    return {"ok": True, **usage_metering.get_today_summary()}


@router.get("/api/usage/me")
async def api_usage_me(request: Request, days: int = 30):
    if not usage_metering:
        return {"ok": False, "error": "用量計量模組未安裝"}
    data = _extract_token(request)
    uid = (data or {}).get("sub", "anonymous")
    return {"ok": True, **usage_metering.get_user_usage(uid, days)}


@router.get("/api/usage/quota")
async def api_usage_quota(request: Request):
    if not usage_metering:
        return {"ok": False, "error": "用量計量模組未安裝"}
    data = _extract_token(request)
    uid = (data or {}).get("sub", "anonymous")
    plan = (data or {}).get("sub_status", "free")
    user_info = auth_manager.get_user_info(uid) if uid != "anonymous" else None
    if user_info:
        plan = user_info.get("subscription_plan", "") or "free"
    return {"ok": True, **usage_metering.check_quota(uid, plan)}


@router.get("/api/usage/system")
async def api_usage_system(request: Request, days: int = 30):
    if not usage_metering:
        return {"ok": False, "error": "用量計量模組未安裝"}
    _require_admin(request)
    return {"ok": True, **usage_metering.get_system_usage(days)}


# ── AI 用量追蹤 ──
@router.get("/api/usage/today/v2")
async def api_usage_today_v2():
    if not USAGE_TRACKER_AVAILABLE:
        return {"ok": False, "error": "用量追蹤模組未安裝"}
    return {"ok": True, **usage_tracker.get_today_stats()}


@router.get("/api/usage/weekly")
async def api_usage_weekly():
    if not USAGE_TRACKER_AVAILABLE:
        return {"ok": False, "error": "用量追蹤模組未安裝"}
    return {"ok": True, **usage_tracker.get_weekly_stats()}


@router.get("/api/usage/report")
async def api_usage_report():
    if not USAGE_TRACKER_AVAILABLE:
        return {"ok": False, "error": "用量追蹤模組未安裝"}
    return {"ok": True, "report": usage_tracker.export_report()}


# ── 用量警報 ──
@router.get("/api/usage/alerts")
async def api_usage_alerts():
    if not USAGE_ALERTS_AVAILABLE:
        return {"ok": False, "error": "警報模組未安裝"}
    return {"ok": True, "alerts": alerts_manager.get_recent_alerts()}


@router.get("/api/usage/alerts/check")
async def api_usage_alerts_check():
    if not USAGE_ALERTS_AVAILABLE:
        return {"ok": False, "error": "警報模組未安裝"}
    try:
        from ai_usage_tracker import usage_tracker as ut
        stats = ut.get_today_stats()
        alerts = alerts_manager.check_usage(stats)
        return {"ok": True, "alerts": alerts}
    except ImportError:
        return {"ok": False, "error": "用量追蹤模組未安裝"}


@router.post("/api/usage/alerts/threshold")
async def api_usage_alerts_threshold(request: Request):
    if not USAGE_ALERTS_AVAILABLE:
        return {"ok": False, "error": "警報模組未安裝"}
    payload = await request.json()
    provider = str((payload or {}).get("provider", "")).strip().lower()
    value = float((payload or {}).get("value", 0))
    if provider and value > 0:
        alerts_manager.set_threshold(provider, value)
        return {"ok": True, "message": f"已設定 {provider} 閾值為 ${value}"}
    return {"ok": False, "error": "provider 和 value 為必填"}


# ── 監控儀表板 ──
@router.get("/api/monitor/dashboard")
async def api_monitor_dashboard(request: Request):
    if not structured_logger:
        return {"ok": False, "error": "監控模組未安裝"}
    _require_admin(request)
    return {"ok": True, **structured_logger.get_dashboard_data()}


@router.get("/api/monitor/logs")
async def api_monitor_logs(request: Request, level: str = "", limit: int = 50):
    if not structured_logger:
        return {"ok": False, "error": "監控模組未安裝"}
    _require_admin(request)
    try:
        log_file = structured_logger.LOG_FILE
        if not log_file.exists():
            return {"ok": True, "logs": [], "count": 0}
        entries = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if level and entry.get("level", "") != level.upper():
                        continue
                    entries.append(entry)
                except Exception:
                    pass
        entries = entries[-limit:]
        entries.reverse()
        return {"ok": True, "logs": entries, "count": len(entries)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── 營運通知 ──
@router.post("/api/ops/send-email")
async def api_ops_send_email(request: Request):
    if not ops_notify:
        return {"ok": False, "error": "營運模組未安裝"}
    _require_admin(request)
    payload = await request.json()
    to = str((payload or {}).get("to", "")).strip()
    subject = str((payload or {}).get("subject", "")).strip()
    body = str((payload or {}).get("body", "")).strip()
    if not to or not subject or not body:
        raise HTTPException(400, "to, subject, body are required")
    return ops_notify.send_email(to, subject, ops_notify._email_wrapper(subject, f"<p>{body}</p>"))


@router.post("/api/ops/check-expiring")
async def api_ops_check_expiring(request: Request):
    if not ops_notify:
        return {"ok": False, "error": "營運模組未安裝"}
    _require_admin(request)
    payload = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    days = int((payload or {}).get("days", 7))
    results = ops_notify.check_expiring_subscriptions(days)
    return {"ok": True, "results": results, "count": len(results)}


@router.post("/api/ops/check-quota-alerts")
async def api_ops_check_quota(request: Request):
    if not ops_notify:
        return {"ok": False, "error": "營運模組未安裝"}
    _require_admin(request)
    alerts = ops_notify.check_quota_alerts()
    return {"ok": True, "alerts": alerts, "count": len(alerts)}


@router.get("/api/ops/smtp-status")
async def api_ops_smtp_status(request: Request):
    if not ops_notify:
        return {"ok": False, "error": "營運模組未安裝"}
    _require_admin(request)
    return {"ok": True, "smtp_enabled": ops_notify.SMTP_ENABLED, "smtp_host": ops_notify.SMTP_HOST, "smtp_port": ops_notify.SMTP_PORT, "smtp_from": ops_notify.SMTP_FROM, "smtp_user_set": bool(ops_notify.SMTP_USER)}

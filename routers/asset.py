# -*- coding: utf-8 -*-
"""築未科技 — Asset Commander Router"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException
from routers.deps import _extract_token, _require_admin, logger

router = APIRouter(tags=["資產管理"])

try:
    import asset_commander
    ASSET_COMMANDER_AVAILABLE = True
except ImportError:
    asset_commander = None
    ASSET_COMMANDER_AVAILABLE = False


@router.get("/api/asset/state")
async def api_asset_state():
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    return {"ok": True, **asset_commander.get_commander().get_state()}


@router.get("/api/asset/health")
async def api_asset_health():
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    commander = asset_commander.get_commander()
    state = commander.get_state()
    gpu_info = commander.get_gpu_info()
    return {"ok": True, "running": state["running"], "current_platform": state["current_platform"], "net_profit_day": state["net_profit_day"], "should_pause": state["should_pause"], "best_platform": state["best_platform"], "gpu_available": gpu_info["available"], "gpu_power_watts": state["gpu_power_watts"], "gpu_utilization": state["gpu_utilization"]}


@router.get("/api/asset/config")
async def api_asset_config():
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    return {"ok": True, **asset_commander.get_commander().get_config()}


@router.post("/api/asset/config")
async def api_asset_config_update(request: Request):
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    _require_admin(request)
    payload = await request.json()
    asset_commander.get_commander().update_config(payload)
    return {"ok": True, "message": "配置已更新"}


@router.post("/api/asset/start")
async def api_asset_start():
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    asset_commander.get_commander().start()
    return {"ok": True, "message": "Asset Commander 已啟動"}


@router.post("/api/asset/stop")
async def api_asset_stop():
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    asset_commander.get_commander().stop()
    return {"ok": True, "message": "Asset Commander 已停止"}


@router.post("/api/asset/switch")
async def api_asset_switch(request: Request):
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    _require_admin(request)
    payload = await request.json()
    platform = payload.get("platform", "")
    success = await asset_commander.get_commander().switch_to_platform(platform)
    if success:
        return {"ok": True, "message": f"已切換到 {platform}"}
    return {"ok": False, "error": "切換失敗，平臺不存在"}


@router.get("/api/asset/report")
async def api_asset_report():
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    return {"ok": True, **asset_commander.get_commander().get_daily_report()}


@router.get("/api/asset/earnings")
async def api_asset_earnings(days: int = 7):
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    commander = asset_commander.get_commander()
    cutoff = datetime.now() - timedelta(days=days)
    history = [r for r in commander.earnings_history if datetime.fromisoformat(r["timestamp"]) > cutoff]
    return {"ok": True, "history": history, "count": len(history)}


@router.post("/api/asset/refresh")
async def api_asset_refresh():
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    commander = asset_commander.get_commander()
    await commander.update_all_platforms()
    return {"ok": True, "message": "已刷新", **commander.get_state()}

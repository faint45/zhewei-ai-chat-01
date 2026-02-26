# -*- coding: utf-8 -*-
"""
水情預警系統 — FastAPI 服務入口
路由前綴：/api/flood/*

可獨立部署（Pi5 N100 總機）或掛載到 prediction_service.py
"""
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# 確保能 import 主專案
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

log = logging.getLogger("water_alert.service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [WaterAlert] %(levelname)s %(message)s")

app = FastAPI(
    title="水情預警系統 API",
    description="築未科技 — 五源加權 AI 水情預警",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 全局實例 =====
_decision_engines = {}   # station_id -> FloodDecisionEngine
_influxdb = None
_broadcast = None


def _init():
    """延遲初始化"""
    global _influxdb, _broadcast

    from water_alert.config import DEFAULT_STATIONS, DEFAULT_SYSTEM
    from water_alert.flood_decision_engine import FloodDecisionEngine

    for station in DEFAULT_STATIONS:
        _decision_engines[station.station_id] = FloodDecisionEngine(station, DEFAULT_SYSTEM)

    # InfluxDB（可選）
    try:
        from water_alert.influxdb_store import InfluxDBStore
        _influxdb = InfluxDBStore()
        _influxdb.connect()
    except Exception as e:
        log.warning(f"InfluxDB 不可用: {e}")

    # 廣播控制器（可選，僅 Pi 環境）
    try:
        from water_alert.broadcast_controller import BroadcastController
        _broadcast = BroadcastController()
    except Exception as e:
        log.warning(f"廣播控制器不可用: {e}")


# ===== Pydantic Models =====

class SensorData(BaseModel):
    station_id: str
    water_level_m: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    cloud_type: Optional[str] = ""
    forecast_rainfall_mm: Optional[float] = None
    vision_score: Optional[float] = None


class AlertTrigger(BaseModel):
    station_id: str = "WA-HQ"
    alert_level: int = 2
    message: str = ""
    siren_sec: int = 10
    light_sec: int = 30
    broadcast_repeat: int = 3


class CalibrateRequest(BaseModel):
    station_id: str
    known_level_m: float


# ===== API 路由 =====

@app.on_event("startup")
async def startup():
    _init()
    log.info(f"水情預警系統啟動，站點: {list(_decision_engines.keys())}")


@app.get("/api/flood/health")
async def health():
    return {
        "status": "ok",
        "service": "water-alert",
        "stations": list(_decision_engines.keys()),
        "influxdb": _influxdb is not None,
        "broadcast": _broadcast is not None,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/flood/decide")
async def decide(data: SensorData):
    """
    接收感測數據，執行五源加權決策

    可由站端 LoRa 上報觸發，也可由外部 API 呼叫
    """
    engine = _decision_engines.get(data.station_id)
    if not engine:
        raise HTTPException(404, f"站點不存在: {data.station_id}")

    inputs = []

    if data.water_level_m is not None:
        inputs.append(engine.normalize_radar(data.water_level_m))

    if data.cloud_cover_pct is not None:
        inputs.append(engine.normalize_cloud(data.cloud_cover_pct, data.cloud_type or ""))

    if data.humidity is not None:
        inputs.append(engine.normalize_dht(data.temperature or 25, data.humidity))

    if data.forecast_rainfall_mm is not None:
        inputs.append(engine.normalize_forecast(data.forecast_rainfall_mm))

    if data.vision_score is not None:
        from water_alert.flood_decision_engine import SensorInput
        inputs.append(SensorInput(
            source="vision", value=data.vision_score,
            raw_value=data.vision_score, unit="score",
            timestamp=datetime.now().isoformat(),
        ))

    if not inputs:
        raise HTTPException(400, "至少需要一項感測數據")

    decision = engine.decide(inputs)

    # 寫入 InfluxDB
    if _influxdb:
        _influxdb.write_decision(
            data.station_id, decision.weighted_score,
            decision.alert_level, decision.alert_name, decision.trend,
        )
        if data.water_level_m is not None:
            _influxdb.write_water_level(data.station_id, 0, data.water_level_m)
        if data.humidity is not None:
            _influxdb.write_weather(data.station_id, data.temperature or 0, data.humidity)

    # 自動觸發警報
    if decision.alert_level >= 2 and _broadcast:
        _broadcast.trigger_alert(decision.alert_level)

    # 高風險推播 Ntfy
    if decision.alert_level >= 2:
        _push_ntfy_alert(data.station_id, decision)

    return decision.to_dict()


@app.post("/api/flood/alert/trigger")
async def trigger_alert(req: AlertTrigger):
    """手動觸發警報"""
    if _broadcast:
        _broadcast.trigger_alert(
            req.alert_level, req.message,
            req.siren_sec, req.light_sec, req.broadcast_repeat,
        )
        if _influxdb:
            _influxdb.write_alert(req.station_id, req.alert_level, req.message)
        return {"status": "triggered", "level": req.alert_level}
    return {"status": "broadcast_unavailable"}


@app.post("/api/flood/alert/stop")
async def stop_alert():
    """停止所有警報"""
    if _broadcast:
        _broadcast.all_off()
        return {"status": "stopped"}
    return {"status": "broadcast_unavailable"}


@app.get("/api/flood/stations")
async def list_stations():
    """列出所有站點"""
    from water_alert.config import DEFAULT_STATIONS
    return [
        {
            "station_id": s.station_id,
            "station_name": s.station_name,
            "river_name": s.river_name,
            "distance_km": s.distance_km,
            "radar": s.radar_installed,
            "camera": s.camera_installed,
            "thresholds": {
                "warning_m": s.water_level_warning_m,
                "alert_m": s.water_level_alert_m,
                "critical_m": s.water_level_critical_m,
                "evacuate_m": s.water_level_evacuate_m,
            },
        }
        for s in DEFAULT_STATIONS
    ]


@app.get("/api/flood/history")
async def query_history(
    station_id: str = Query("WA-001"),
    measurement: str = Query("water_level"),
    hours: int = Query(24),
):
    """查詢歷史數據"""
    if not _influxdb:
        raise HTTPException(503, "InfluxDB 未連接")
    data = _influxdb._query_measurement(measurement, station_id, hours)
    return {"count": len(data), "data": data}


@app.get("/api/flood/broadcast/status")
async def broadcast_status():
    """廣播控制器狀態"""
    if _broadcast:
        return _broadcast.get_status()
    return {"gpio_available": False, "siren_on": False, "light_on": False}


# ===== Ntfy 推播 =====

def _push_ntfy_alert(station_id: str, decision):
    """推送 Ntfy 警報"""
    from water_alert.config import NTFY_SERVER, DEFAULT_STATIONS
    import urllib.request

    station = next((s for s in DEFAULT_STATIONS if s.station_id == station_id), None)
    topic = (station.ntfy_topic if station else "") or "flood_general"
    level_emoji = {0: "🟢", 1: "🟡", 2: "🟠", 3: "🔴", 4: "🆘"}

    title = f"{level_emoji.get(decision.alert_level, '⚠️')} {decision.alert_name} — {station_id}"
    body = f"加權分數: {decision.weighted_score:.0f}/100\n"
    body += f"趨勢: {decision.trend}\n"
    if decision.actions:
        body += "\n建議行動:\n" + "\n".join(f"• {a}" for a in decision.actions[:5])

    try:
        data = body.encode("utf-8")
        req = urllib.request.Request(
            f"{NTFY_SERVER}/{topic}",
            data=data,
            headers={
                "Title": title,
                "Priority": str(min(5, decision.alert_level + 2)),
                "Tags": f"water,alert,{decision.alert_name}",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
        log.info(f"Ntfy 推播成功: {topic}")
    except Exception as e:
        log.error(f"Ntfy 推播失敗: {e}")


# ===== 獨立啟動 =====

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("WATER_ALERT_PORT", "8016"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

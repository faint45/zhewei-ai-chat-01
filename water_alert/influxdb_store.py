# -*- coding: utf-8 -*-
"""
水情預警系統 — InfluxDB 時序資料庫
儲存水位/氣象/決策歷史，供 Grafana 儀表板查詢

依賴：pip install influxdb-client
"""
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

log = logging.getLogger("water_alert.influxdb")

from water_alert.config import INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET


class InfluxDBStore:
    """
    InfluxDB 時序資料庫封裝

    Measurements:
    - water_level: 水位數據（distance_m, water_level_m, signal_strength）
    - weather: 溫濕度（temperature, humidity）
    - cloud: 雲量（cloud_cover_pct, rain_probability）
    - decision: 決策結果（weighted_score, alert_level）
    - alert: 警報記錄
    """

    def __init__(self):
        self._client = None
        self._write_api = None
        self._query_api = None

    def connect(self) -> bool:
        """連接 InfluxDB"""
        if not INFLUXDB_TOKEN:
            log.warning("INFLUXDB_TOKEN 未設定，InfluxDB 儲存停用")
            return False
        try:
            from influxdb_client import InfluxDBClient
            from influxdb_client.client.write_api import SYNCHRONOUS
            self._client = InfluxDBClient(
                url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG,
            )
            self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
            self._query_api = self._client.query_api()
            # 驗證連線
            self._client.ping()
            log.info(f"InfluxDB 連接成功: {INFLUXDB_URL}")
            return True
        except ImportError:
            log.error("influxdb-client 未安裝: pip install influxdb-client")
            return False
        except Exception as e:
            log.error(f"InfluxDB 連接失敗: {e}")
            return False

    def close(self):
        if self._client:
            self._client.close()

    # ===== 寫入 =====

    def write_water_level(self, station_id: str, distance_m: float,
                          water_level_m: float, signal_strength: float = 0):
        """寫入水位數據"""
        self._write_point("water_level", station_id, {
            "distance_m": distance_m,
            "water_level_m": water_level_m,
            "signal_strength": signal_strength,
        })

    def write_weather(self, station_id: str, temperature: float, humidity: float):
        """寫入溫濕度"""
        self._write_point("weather", station_id, {
            "temperature": temperature,
            "humidity": humidity,
        })

    def write_cloud(self, station_id: str, cloud_cover_pct: float,
                    cloud_type: str = "", rain_probability: float = 0):
        """寫入雲量"""
        self._write_point("cloud", station_id, {
            "cloud_cover_pct": cloud_cover_pct,
            "rain_probability": rain_probability,
        }, extra_tags={"cloud_type": cloud_type})

    def write_decision(self, station_id: str, weighted_score: float,
                       alert_level: int, alert_name: str = "", trend: str = ""):
        """寫入決策結果"""
        self._write_point("decision", station_id, {
            "weighted_score": weighted_score,
            "alert_level": alert_level,
        }, extra_tags={"alert_name": alert_name, "trend": trend})

    def write_alert(self, station_id: str, alert_level: int,
                    message: str = "", actions_taken: str = ""):
        """寫入警報記錄"""
        self._write_point("alert", station_id, {
            "alert_level": alert_level,
        }, extra_tags={"message": message[:200], "actions_taken": actions_taken[:200]})

    # ===== 查詢 =====

    def query_water_level(self, station_id: str, hours: int = 24) -> list:
        """查詢水位歷史"""
        return self._query_measurement("water_level", station_id, hours)

    def query_decisions(self, station_id: str, hours: int = 24) -> list:
        """查詢決策歷史"""
        return self._query_measurement("decision", station_id, hours)

    def query_alerts(self, station_id: str = "", hours: int = 168) -> list:
        """查詢警報歷史（預設 7 天）"""
        return self._query_measurement("alert", station_id, hours)

    def get_latest(self, measurement: str, station_id: str) -> Optional[dict]:
        """查詢最新一筆"""
        results = self._query_measurement(measurement, station_id, hours=1)
        return results[-1] if results else None

    # ===== 內部 =====

    def _write_point(self, measurement: str, station_id: str,
                     fields: dict, extra_tags: dict = None):
        """寫入單筆資料點"""
        if not self._write_api:
            return
        try:
            from influxdb_client import Point
            p = Point(measurement).tag("station_id", station_id)
            if extra_tags:
                for k, v in extra_tags.items():
                    if v:
                        p = p.tag(k, str(v))
            for k, v in fields.items():
                if isinstance(v, (int, float)):
                    p = p.field(k, v)
                elif isinstance(v, str):
                    p = p.field(k, v)
            self._write_api.write(bucket=INFLUXDB_BUCKET, record=p)
        except Exception as e:
            log.error(f"InfluxDB 寫入失敗 [{measurement}]: {e}")

    def _query_measurement(self, measurement: str, station_id: str,
                           hours: int = 24) -> list:
        """查詢 measurement"""
        if not self._query_api:
            return []
        try:
            flux = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: -{hours}h)
  |> filter(fn: (r) => r._measurement == "{measurement}")'''
            if station_id:
                flux += f'''
  |> filter(fn: (r) => r.station_id == "{station_id}")'''
            flux += '''
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"])
  |> limit(n: 1000)'''

            tables = self._query_api.query(flux)
            results = []
            for table in tables:
                for record in table.records:
                    row = {"time": record.get_time().isoformat()}
                    row.update(record.values)
                    # 清理 influx 內部 key
                    for k in ("result", "table", "_start", "_stop", "_measurement"):
                        row.pop(k, None)
                    results.append(row)
            return results
        except Exception as e:
            log.error(f"InfluxDB 查詢失敗 [{measurement}]: {e}")
            return []


# ===== Grafana Dashboard JSON 範本 =====

GRAFANA_DASHBOARD_TEMPLATE = {
    "title": "水情預警系統",
    "description": "即時水位監測 + AI 決策 + 警報歷史",
    "panels": [
        {
            "title": "即時水位 (m)",
            "type": "timeseries",
            "targets": [{
                "query": 'from(bucket:"water_alert") |> range(start:-24h) '
                         '|> filter(fn:(r) => r._measurement == "water_level") '
                         '|> filter(fn:(r) => r._field == "water_level_m")',
            }],
        },
        {
            "title": "AI 決策分數",
            "type": "gauge",
            "targets": [{
                "query": 'from(bucket:"water_alert") |> range(start:-1h) '
                         '|> filter(fn:(r) => r._measurement == "decision") '
                         '|> filter(fn:(r) => r._field == "weighted_score") '
                         '|> last()',
            }],
            "thresholds": [
                {"value": 25, "color": "green"},
                {"value": 50, "color": "yellow"},
                {"value": 70, "color": "orange"},
                {"value": 85, "color": "red"},
            ],
        },
        {
            "title": "雲量 (%)",
            "type": "timeseries",
            "targets": [{
                "query": 'from(bucket:"water_alert") |> range(start:-24h) '
                         '|> filter(fn:(r) => r._measurement == "cloud") '
                         '|> filter(fn:(r) => r._field == "cloud_cover_pct")',
            }],
        },
        {
            "title": "溫濕度",
            "type": "timeseries",
            "targets": [{
                "query": 'from(bucket:"water_alert") |> range(start:-24h) '
                         '|> filter(fn:(r) => r._measurement == "weather")',
            }],
        },
        {
            "title": "警報歷史",
            "type": "table",
            "targets": [{
                "query": 'from(bucket:"water_alert") |> range(start:-7d) '
                         '|> filter(fn:(r) => r._measurement == "alert")',
            }],
        },
    ],
}

# -*- coding: utf-8 -*-
"""
水情預警系統 — 站點與系統配置
"""
import os
from dataclasses import dataclass, field
from typing import Optional

# ===== 環境變數 =====
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11460").rstrip("/")
WA_LLM_MODEL = os.environ.get("WA_LLM_MODEL", "qwen3:32b")

# InfluxDB
INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN", "")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG", "zhewei")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET", "water_alert")

# LoRa
LORA_SERIAL_PORT = os.environ.get("LORA_SERIAL_PORT", "/dev/ttyUSB0")
LORA_BAUD_RATE = int(os.environ.get("LORA_BAUD_RATE", "9600"))
LORA_FREQUENCY = float(os.environ.get("LORA_FREQUENCY", "433.0"))  # MHz
LORA_SPREAD_FACTOR = int(os.environ.get("LORA_SPREAD_FACTOR", "7"))
LORA_BANDWIDTH = int(os.environ.get("LORA_BANDWIDTH", "125"))  # kHz

# Ntfy 推播
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")

# 廣播/閃光燈 GPIO（Pi5）
GPIO_SIREN_PIN = int(os.environ.get("GPIO_SIREN_PIN", "17"))
GPIO_LIGHT_PIN = int(os.environ.get("GPIO_LIGHT_PIN", "27"))
GPIO_RELAY_PIN = int(os.environ.get("GPIO_RELAY_PIN", "22"))

# 水利署 API
WRA_API_BASE = os.environ.get("WRA_API_BASE", "https://fhy.wra.gov.tw/WraApi/v1")
CWB_API_KEY = os.environ.get("CWB_API_KEY", "")


@dataclass
class StationConfig:
    """觀測站配置"""
    station_id: str                     # 站點代號（如 WA-001）
    station_name: str                   # 站點名稱（如 筏子溪上游 3km）
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0              # 海拔高度 (m)
    river_name: str = ""               # 河川名稱
    distance_km: float = 0.0           # 距工地距離 (km)
    # 雷達水位計
    radar_installed: bool = False
    radar_mount_height_m: float = 5.0  # 雷達安裝高度（距河床底 m）
    radar_serial_port: str = "/dev/ttyUSB1"
    # 攝影機
    camera_installed: bool = False
    camera_index: int = 0              # /dev/video0
    camera_fisheye: bool = False       # 魚眼鏡頭（雲量辨識用）
    # 溫濕度感測器
    dht_installed: bool = False
    dht_pin: int = 4                   # GPIO pin for DHT22
    # LoRa
    lora_address: int = 1              # LoRa 網路地址 (1-255)
    # 告警閾值
    water_level_warning_m: float = 2.0    # 注意水位 (m)
    water_level_alert_m: float = 3.0      # 警戒水位 (m)
    water_level_critical_m: float = 4.0   # 危險水位 (m)
    water_level_evacuate_m: float = 5.0   # 撤離水位 (m)
    # 雲量閾值
    cloud_heavy_pct: float = 80.0      # 厚雲佔比 > 80% → 加權
    # Ntfy topic
    ntfy_topic: str = ""               # 空則用預設


@dataclass
class SystemConfig:
    """系統全局配置"""
    # 決策引擎加權
    weight_radar: float = 0.40         # 雷達水位權重 40%
    weight_vision: float = 0.25        # 視覺水位權重 25%
    weight_cloud: float = 0.15         # 雲量權重 15%
    weight_dht: float = 0.10           # 溫濕度權重 10%
    weight_forecast: float = 0.10      # 氣象預報權重 10%
    # 輪詢間隔
    poll_interval_sec: int = 30        # 感測器輪詢間隔
    upload_interval_sec: int = 60      # LoRa 上傳間隔
    forecast_interval_sec: int = 600   # 氣象預報更新間隔
    # 錄影
    record_on_alert: bool = True       # 警報時自動錄影
    record_duration_sec: int = 300     # 錄影時長
    # 廣播
    broadcast_repeat: int = 3          # 廣播語音重複次數
    siren_duration_sec: int = 10       # 警報器響鈴時長


# ===== 預設站點配置 =====
DEFAULT_STATIONS = [
    StationConfig(
        station_id="WA-001",
        station_name="上游觀測站（3km）",
        river_name="筏子溪",
        distance_km=3.0,
        radar_installed=True,
        camera_installed=True,
        camera_fisheye=True,
        dht_installed=True,
        lora_address=1,
        water_level_warning_m=2.0,
        water_level_alert_m=3.0,
        water_level_critical_m=4.0,
        water_level_evacuate_m=5.0,
        ntfy_topic="flood_upstream_3km",
    ),
    StationConfig(
        station_id="WA-002",
        station_name="上游觀測站（1km）",
        river_name="筏子溪",
        distance_km=1.0,
        radar_installed=True,
        camera_installed=True,
        dht_installed=True,
        lora_address=2,
        water_level_warning_m=1.5,
        water_level_alert_m=2.5,
        water_level_critical_m=3.5,
        water_level_evacuate_m=4.5,
        ntfy_topic="flood_upstream_1km",
    ),
    StationConfig(
        station_id="WA-HQ",
        station_name="總機（工地現場）",
        river_name="筏子溪",
        distance_km=0.0,
        radar_installed=False,
        camera_installed=True,
        dht_installed=True,
        lora_address=0,  # 0 = 總機/Gateway
        ntfy_topic="flood_site_hq",
    ),
]

DEFAULT_SYSTEM = SystemConfig()

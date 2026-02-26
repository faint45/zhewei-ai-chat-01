# 🌊 Water Alert — 水情預警系統

> 築未科技 — 五源加權 AI 水情預警：雷達水位 + 視覺辨識 + 雲量分析 + 溫濕度 + 氣象預報

## 架構

```text
water_alert/
├── config.py                  ← 站點配置 + 系統參數 + 環境變數
├── radar_water_level.py       ← 80GHz FMCW 雷達水位計（Modbus RTU / UART）
├── lora_gateway.py            ← LoRa SX1276 通訊閘道（封包編解碼 + Mesh + 廣播）
├── cloud_sky_analyzer.py      ← 魚眼鏡頭雲量/雲型辨識（HSV + VLM）
├── flood_decision_engine.py   ← 五源加權 AI 決策引擎（核心）
├── station_controller.py      ← Pi5 站端主控（感測器輪詢 + 本地決策 + LoRa）
├── broadcast_controller.py    ← 廣播喇叭 + 警示閃光燈 GPIO 控制
├── influxdb_store.py          ← InfluxDB 時序資料庫 + Grafana 範本
├── water_alert_service.py     ← FastAPI 服務入口 /api/flood/*（port 8016）
├── requirements.txt           ← 依賴清單
└── README.md
```

## 複用現有模組（零衝突）

| 現有模組 | 複用方式 | 衝突風險 |
| --- | --- | --- |
| `prediction_modules/prediction_engine.py` | +`predict_flood()` 方法 | ✅ 純新增 |
| `prediction_modules/alert_manager.py` | +`send_flood_alert()` 方法 | ✅ 純新增 |
| `prediction_modules/scientific_data_collector.py` | +`collect_water_level_data()` | ✅ 純新增 |
| `tools/vision_edge_service.py` | import VisionPipeline | ✅ 不動 |
| `tools/edge_compute.py` | import EdgeCompute | ✅ 不動 |
| `brain_workspace/static/modules/mod-ntfy-push.js` | 前端 PWA 推播 | ✅ 不動 |

## 五源加權決策

```text
  雷達水位 ──── 40% ───┐
  視覺水位 ──── 25% ───┤
  雲量辨識 ──── 15% ───┼──→ FloodDecisionEngine.decide()
  溫濕度   ──── 10% ───┤         │
  氣象預報 ──── 10% ───┘         ▼
                         ┌──────────────┐
                         │  0-25  安全   │ 🟢
                         │ 25-50  注意   │ 🟡
                         │ 50-70  警戒   │ 🟠
                         │ 70-85  危險   │ 🔴
                         │ 85-100 撤離   │ 🆘
                         └──────────────┘
```

## 系統拓撲

```text
  [上游 3km Pi5]          [上游 1km Pi5]
   雷達+魚眼+DHT22         雷達+DHT22
       │ LoRa                  │ LoRa
       └──────────┐  ┌────────┘
                  ▼  ▼
            [總機 N100/Pi5]
             LoRa Gateway
             AI 決策引擎
             InfluxDB + Grafana
             FastAPI :8016
             廣播喇叭 + 閃光燈
                  │
          ┌───────┼───────┐
          ▼       ▼       ▼
       Ntfy     LINE    predict.zhe-wei.net
       推播     通知     Grafana 儀表板
```

## 快速開始

```powershell
# 1. 安裝依賴
pip install -r water_alert/requirements.txt

# 2. 啟動 API 服務
python -m water_alert.water_alert_service
# → http://localhost:8016/docs

# 3. 測試決策引擎
python -c "
from water_alert.flood_decision_engine import FloodDecisionEngine
from water_alert.config import DEFAULT_STATIONS, DEFAULT_SYSTEM
engine = FloodDecisionEngine(DEFAULT_STATIONS[0], DEFAULT_SYSTEM)
inputs = [
    engine.normalize_radar(2.5),
    engine.normalize_cloud(70, 'nimbostratus'),
    engine.normalize_dht(22, 92),
    engine.normalize_forecast(45),
]
result = engine.decide(inputs)
print(f'{result.alert_name} ({result.weighted_score:.0f}/100)')
print(f'Actions: {result.actions}')
"
```

## API 端點

| 方法 | 路徑 | 說明 |
| --- | --- | --- |
| GET | `/api/flood/health` | 健康檢查 |
| POST | `/api/flood/decide` | 五源加權決策（核心） |
| POST | `/api/flood/alert/trigger` | 手動觸發警報 |
| POST | `/api/flood/alert/stop` | 停止所有警報 |
| GET | `/api/flood/stations` | 列出站點 |
| GET | `/api/flood/history` | 查詢歷史數據 |
| GET | `/api/flood/broadcast/status` | 廣播控制器狀態 |

## Ntfy 推播 Topic

| Topic | 說明 |
| --- | --- |
| `flood_upstream_3km` | 上游 3km 觀測站 |
| `flood_upstream_1km` | 上游 1km 觀測站 |
| `flood_site_hq` | 工地總機 |
| `flood_general` | 水情總覽 |

## 環境變數

```env
# InfluxDB
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-token
INFLUXDB_ORG=zhewei
INFLUXDB_BUCKET=water_alert

# LoRa
LORA_SERIAL_PORT=/dev/ttyUSB0
LORA_FREQUENCY=433.0

# GPIO（Pi5）
GPIO_SIREN_PIN=17
GPIO_LIGHT_PIN=27
GPIO_RELAY_PIN=22

# 水利署 API
WRA_API_BASE=https://fhy.wra.gov.tw/WraApi/v1
CWB_API_KEY=your-cwb-key

# 服務 Port
WATER_ALERT_PORT=8016
```

## 開發排程

| 階段 | 模組 | 工時 |
| --- | --- | --- |
| P1 | flood_decision_engine + prediction_engine 擴充 | 40h |
| P2 | lora_gateway + station_controller | 40h |
| P3 | radar_water_level + influxdb_store | 16h |
| P4 | vision_edge_service 水位辨識 prompt | 40h |
| P5 | cloud_sky_analyzer | 24h |
| P6 | alert_manager 擴充 + broadcast_controller | 32h |
| P7 | water_alert_service + Grafana 儀表板 | 32h |

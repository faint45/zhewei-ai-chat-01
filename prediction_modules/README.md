# 易經科學預測系統 - I Ching Scientific Prediction System

## 系統概述

結合傳統易經八卦智慧與現代科學數據，進行台灣地區地震、氣象、經濟預測，並透過實際事件驗證修正預測模型。

### 核心特色

- 🔮 **易經八卦引擎** - 完整64卦系統，支援時間起卦、數據起卦、蓍草起卦
- 🌍 **科學數據整合** - 電離層、地磁、地震、氣象等多源數據
- 📊 **智慧預測算法** - 卦象解讀 + 科學數據修正 + 機器學習優化
- ✅ **驗證修正機制** - 實際事件驗證 + 自動參數調整
- 📈 **即時監測系統** - WebSocket 推送 + 自動警報
- 🎨 **視覺化儀表板** - Vue 3 + Tailwind CSS 響應式介面

## 系統架構

```
prediction_modules/
├── iching_core.py              # 易經核心引擎（64卦、八卦、起卦法）
├── scientific_data_collector.py # 科學數據收集器
├── prediction_engine.py         # 預測引擎（整合易經+科學）
├── prediction_service.py        # FastAPI 服務（REST + WebSocket）
├── static/
│   └── prediction_dashboard.html # Web 儀表板
├── data_cache/                  # 數據快取
├── predictions.db               # SQLite 預測記錄資料庫
└── requirements.txt             # Python 依賴
```

## 快速啟動

### 1. 安裝依賴

```bash
cd D:\zhe-wei-tech
Jarvis_Training\.venv312\Scripts\python.exe -m pip install -r prediction_modules/requirements.txt
```

### 2. 啟動服務

**方式一：使用啟動腳本**
```bash
scripts\start_prediction_system.bat
```

**方式二：手動啟動**
```bash
cd D:\zhe-wei-tech
Jarvis_Training\.venv312\Scripts\python.exe prediction_modules\prediction_service.py
```

### 3. 訪問系統

- 📊 **儀表板**: http://localhost:8025/static/prediction_dashboard.html
- 📖 **API 文檔**: http://localhost:8025/docs
- 🔌 **WebSocket**: ws://localhost:8025/ws/predictions

## 核心模組說明

### 1. 易經核心引擎 (iching_core.py)

#### 主要功能
- 64卦完整資料庫（含地震、氣象相關卦象）
- 八卦基本屬性（金木水火土、方位、性質）
- 三種起卦方法：
  - **時間起卦** - 根據年月日時推算
  - **數據起卦** - 根據科學數據陣列推算
  - **蓍草起卦** - 傳統隨機起卦

#### 重要卦象
- **震為雷 (51)** - 地震強烈預兆
- **艮為山 (52)** - 山體穩固，防地層變動
- **火山旅 (56)** - 地下能量累積
- **坎為水 (29)** - 大雨洪水
- **離為火 (30)** - 高溫乾旱
- **巽為風 (57)** - 強風颱風

#### 使用範例
```python
from iching_core import IChingEngine

engine = IChingEngine()

# 時間起卦
hexagram = engine.cast_hexagram_by_time()

# 數據起卦（電離層數據）
data = [3.5, 4.2, 3.8, 5.1, 4.5, 3.9]
hexagram = engine.cast_hexagram_by_data(data)

# 地震預測解讀
scientific_data = {
    'ionosphere_anomaly': 0.75,
    'geomagnetic_anomaly': 0.65
}
prediction = engine.interpret_for_earthquake(hexagram, scientific_data)
```

### 2. 科學數據收集器 (scientific_data_collector.py)

#### 數據來源

| 數據類型 | 來源 | 用途 |
|---------|------|------|
| 電離層 | NOAA SWPC, NASA CCMC | 地震前兆偵測 |
| 地磁 | NOAA Kp Index, INTERMAGNET | 地震、太空天氣 |
| 地震 | USGS, 中央氣象署 | 歷史地震分析 |
| 氣象 | 中央氣象署自動站 | 天氣預測 |

#### 異常指標計算
- **電離層異常** - TEC 值、foF2 頻率異常
- **地磁異常** - Kp 指數 > 5 為擾動
- **地震活動度** - 7天內 M3.0+ 地震次數
- **氣壓異常** - < 1000 hPa 為低壓

#### 環境變數設定
```bash
# 中央氣象署 API Key（選用）
CWB_API_KEY=your_api_key_here
```

### 3. 預測引擎 (prediction_engine.py)

#### 預測流程
1. 收集科學數據 → 計算異常指標
2. 起卦（時間法或數據法）
3. 卦象解讀 + 科學數據修正
4. 應用歷史修正參數
5. 生成預測結果 + 建議措施
6. 保存到資料庫

#### 驗證修正機制
- **準確度評分** - 0-100 分
- **自動參數調整** - 學習率 0.1
- **修正因子** - correction_factor (0.5-1.5)
- **權重調整** - weight_adjustment (-10 to +10)

#### 地震預測評分標準
- 預測有地震且發生 → 40 分
- 規模誤差 < 1.0 → +30 分
- 時間誤差 ≤ 3 天 → +30 分
- 預測無地震且正確 → 80 分

### 4. FastAPI 服務 (prediction_service.py)

#### REST API 端點

**預測相關**
- `POST /api/prediction/predict` - 創建新預測
- `POST /api/prediction/validate` - 驗證預測結果
- `GET /api/prediction/history` - 獲取預測歷史
- `GET /api/prediction/statistics` - 獲取統計數據

**科學數據**
- `GET /api/scientific/anomaly` - 綜合異常指標
- `GET /api/scientific/ionosphere` - 電離層數據
- `GET /api/scientific/geomagnetic` - 地磁數據
- `GET /api/scientific/earthquake` - 地震數據
- `GET /api/scientific/weather` - 氣象數據

**易經工具**
- `POST /api/iching/cast` - 起卦
- `GET /api/iching/hexagrams` - 獲取64卦資料
- `GET /api/iching/trigrams` - 獲取八卦資料

**WebSocket**
- `WS /ws/predictions` - 即時預測推送

#### 自動監測
- 每小時檢查異常指標
- 總異常 > 0.6 自動進行地震預測
- 風險等級 > 70% 廣播高風險警報

## 使用範例

### Python API 調用

```python
import requests

# 創建地震預測
response = requests.post('http://localhost:8025/api/prediction/predict', json={
    'prediction_type': 'earthquake',
    'use_time_casting': False
})
prediction = response.json()
print(f"風險等級: {prediction['risk_level']}%")

# 驗證預測
requests.post('http://localhost:8025/api/prediction/validate', json={
    'prediction_id': prediction['id'],
    'actual_event': {
        'occurred': True,
        'magnitude': 5.2,
        'days_from_prediction': 3
    }
})

# 獲取統計
stats = requests.get('http://localhost:8025/api/prediction/statistics').json()
print(f"平均準確度: {stats['average_accuracy']}%")
```

### JavaScript WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8025/ws/predictions');

ws.onopen = () => {
    ws.send(JSON.stringify({ type: 'subscribe' }));
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === 'high_risk_alert') {
        alert(`高風險警報！風險等級: ${message.data.risk_level}%`);
    }
};

// 請求即時預測
ws.send(JSON.stringify({
    type: 'request_prediction',
    prediction_type: 'earthquake'
}));
```

## 資料庫結構

### predictions 表
- `id` - 預測ID (EQ_/WX_/EC_ + timestamp)
- `timestamp` - 預測時間
- `prediction_type` - earthquake/weather/economy
- `hexagram_number` - 卦號 (1-64)
- `risk_level` - 風險等級 (0-100)
- `status` - pending/verified/failed
- `accuracy_score` - 準確度分數

### validations 表
- 驗證記錄
- 實際事件數據
- 準確度評分

### correction_params 表
- 修正參數
- 按預測類型和卦號分類
- 自動更新學習

## 擴展開發

### 新增預測類型

1. 在 `iching_core.py` 新增解讀方法
```python
def interpret_for_custom(self, hexagram: Hexagram, data: Dict) -> Dict:
    # 自訂解讀邏輯
    pass
```

2. 在 `prediction_engine.py` 新增預測方法
```python
def predict_custom(self) -> Prediction:
    # 預測流程
    pass
```

3. 在 `prediction_service.py` 新增 API 端點

### 新增數據源

在 `scientific_data_collector.py` 新增收集方法：
```python
def collect_custom_data(self) -> List[CustomData]:
    # 數據收集邏輯
    pass
```

## 部署建議

### 本地部署
- Port: 8025
- 啟動腳本: `scripts\start_prediction_system.bat`

### Docker 部署
```dockerfile
FROM python:3.12
WORKDIR /app
COPY prediction_modules/ /app/
RUN pip install -r requirements.txt
CMD ["uvicorn", "prediction_service:app", "--host", "0.0.0.0", "--port", "8025"]
```

### 整合到 brain_server
在 `brain_server.py` 新增代理端點：
```python
@app.get("/api/prediction/{path:path}")
async def prediction_proxy(path: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://localhost:8025/api/{path}")
        return response.json()
```

## 注意事項

1. **API Key 設定** - 中央氣象署 API Key 可提升數據準確度
2. **數據更新頻率** - 建議每小時更新一次
3. **驗證週期** - 地震預測建議 7 天後驗證
4. **修正參數** - 至少需要 10 次驗證才能穩定
5. **WebSocket 連線** - 注意防火牆設定

## 技術棧

- **後端**: Python 3.12, FastAPI, SQLite
- **前端**: Vue 3, Tailwind CSS, Chart.js
- **即時通訊**: WebSocket
- **數據源**: NOAA, USGS, NASA, 中央氣象署

## 授權

© 2026 築未科技 Zhewei Tech - All Rights Reserved

## 聯絡方式

- 技術支援: allen34556@gmail.com
- 系統文檔: https://jarvis.zhe-wei.net

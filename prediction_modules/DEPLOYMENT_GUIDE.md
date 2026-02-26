# 易經科學預測系統 - 部署指南

## 快速部署（5分鐘上線）

### 步驟 1: 安裝依賴

```bash
cd D:\zhe-wei-tech
Jarvis_Training\.venv312\Scripts\python.exe -m pip install -r prediction_modules/requirements.txt
```

### 步驟 2: 啟動服務

```bash
scripts\start_prediction_system.bat
```

服務將在 **Port 8025** 啟動

### 步驟 3: 訪問系統

- 📊 儀表板: <http://localhost:8025/static/prediction_dashboard.html>
- 📖 API 文檔: <http://localhost:8025/docs>
- 🔌 WebSocket: `ws://localhost:8025/ws/predictions`

## 環境變數配置（可選）

在 `.env` 文件中添加：

```bash
# 中央氣象署 API Key（提升數據準確度）
CWB_API_KEY=your_cwb_api_key_here

# 預測服務端口
PREDICTION_SERVICE_PORT=8025
```

## 系統架構

```
易經科學預測系統
├── 易經核心引擎 (iching_core.py)
│   ├── 64卦完整資料庫
│   ├── 八卦五行屬性
│   └── 三種起卦方法
│
├── 科學數據收集器 (scientific_data_collector.py)
│   ├── 電離層數據 (NOAA SWPC)
│   ├── 地磁數據 (Kp Index)
│   ├── 地震數據 (USGS + 中央氣象署)
│   └── 氣象數據 (中央氣象署)
│
├── 預測引擎 (prediction_engine.py)
│   ├── 地震預測
│   ├── 氣象預測
│   ├── 經濟預測
│   └── 驗證修正機制
│
└── FastAPI 服務 (prediction_service.py)
    ├── REST API
    ├── WebSocket 推送
    └── 自動監測
```

## 核心功能

### 1. 地震預測

**預測流程:**
1. 收集電離層、地磁異常數據
2. 使用科學數據起卦
3. 結合卦象與異常指標評估風險
4. 生成預測報告和建議措施

**風險等級:**
- 極高風險 (80-100%): 發布地震警報
- 高風險 (60-79%): 提高警戒
- 中等風險 (40-59%): 持續觀察
- 低風險 (0-39%): 正常監測

### 2. 氣象預測

**預測類型:**
- 降雨 (坎卦主水)
- 高溫 (離卦主火)
- 強風 (巽卦主風)
- 正常

### 3. 經濟預測

**市場趨勢:**
- 上升 (乾卦剛健)
- 下降 (坤卦柔順)
- 震盪 (震卦動盪)
- 持平

### 4. 驗證修正

**自動學習機制:**
- 實際事件驗證
- 準確度評分 (0-100)
- 自動調整修正參數
- 學習率: 0.1

## API 使用範例

### Python 調用

```python
import requests

# 創建地震預測
response = requests.post('http://localhost:8025/api/prediction/predict', json={
    'prediction_type': 'earthquake',
    'use_time_casting': False
})
prediction = response.json()

print(f"風險等級: {prediction['risk_level']}%")
print(f"卦象: {prediction['hexagram_name']}")

# 驗證預測
requests.post('http://localhost:8025/api/prediction/validate', json={
    'prediction_id': prediction['id'],
    'actual_event': {
        'occurred': True,
        'magnitude': 5.2,
        'days_from_prediction': 3
    }
})
```

### JavaScript WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8025/ws/predictions');

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'high_risk_alert') {
        alert(`地震高風險警報！風險等級: ${msg.data.risk_level}%`);
    }
};

// 請求即時預測
ws.send(JSON.stringify({
    type: 'request_prediction',
    prediction_type: 'earthquake'
}));
```

## 測試系統

運行完整測試：

```bash
cd D:\zhe-wei-tech
Jarvis_Training\.venv312\Scripts\python.exe prediction_modules\test_prediction_system.py
```

測試項目：
- ✅ 易經核心引擎
- ✅ 科學數據收集
- ✅ 預測引擎
- ✅ 系統整合

## 整合到 brain_server

### 方式一: 反向代理

在 `brain_server.py` 添加：

```python
@app.get("/api/prediction/{path:path}")
async def prediction_proxy(path: str, request: Request):
    async with httpx.AsyncClient() as client:
        url = f"http://localhost:8025/api/{path}"
        response = await client.get(url, params=dict(request.query_params))
        return response.json()
```

### 方式二: 直接導入

```python
from prediction_modules.prediction_engine import PredictionEngine

prediction_engine = PredictionEngine()

@app.post("/api/jarvis/predict-earthquake")
async def predict_earthquake():
    prediction = prediction_engine.predict_earthquake()
    return prediction.to_dict()
```

## Nginx Gateway 配置

在 `gateway/nginx.conf` 添加：

```nginx
location /prediction/ {
    proxy_pass http://host.docker.internal:8025/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

## Cloudflare Tunnel 外網訪問

添加新域名到 Tunnel 配置：

```yaml
ingress:
  - hostname: predict.zhe-wei.net
    service: http://localhost:8025
```

## 數據源說明

### 電離層數據
- **來源**: NOAA Space Weather Prediction Center
- **指標**: F10.7 太陽輻射通量
- **異常閾值**: > 150 SFU 或 < 80 SFU
- **更新頻率**: 每小時

### 地磁數據
- **來源**: NOAA Planetary K-index
- **指標**: Kp 指數 (0-9)
- **異常閾值**: Kp > 5 (地磁擾動)
- **更新頻率**: 每 3 小時

### 地震數據
- **來源**: USGS + 中央氣象署
- **範圍**: 台灣及周邊 (119-123°E, 21-26°N)
- **篩選**: M3.0+ 地震
- **歷史**: 7 天內

### 氣象數據
- **來源**: 中央氣象署自動氣象站
- **站點**: 全台 30+ 測站
- **要素**: 溫度、濕度、氣壓、風速、降雨
- **更新頻率**: 每 10 分鐘

## 性能優化

### 數據快取
- 快取目錄: `prediction_modules/data_cache/`
- 快取時效: 1 小時
- 自動清理舊數據

### 資料庫優化
- SQLite 索引: timestamp, prediction_type
- 定期清理 > 1 年的歷史記錄
- 使用 WAL 模式提升並發

### WebSocket 連接池
- 最大連接數: 100
- 心跳間隔: 30 秒
- 自動重連機制

## 監控與告警

### 系統健康檢查

```bash
curl http://localhost:8025/api/prediction/health
```

### 自動監測
- 每小時檢查異常指標
- 總異常 > 0.6 自動預測
- 風險 > 70% 廣播警報

### 日誌記錄
- 位置: `prediction_modules/logs/`
- 等級: INFO, WARNING, ERROR
- 輪轉: 每日，保留 30 天

## 故障排除

### 問題 1: 無法啟動服務

**原因**: 端口 8025 被占用

**解決**:
```bash
# 查找占用進程
netstat -ano | findstr :8025

# 修改端口（在 prediction_service.py）
uvicorn.run(app, port=8026)
```

### 問題 2: 科學數據收集失敗

**原因**: API 請求超時或無網路

**解決**:
- 檢查網路連接
- 使用模擬數據模式
- 設定 CWB_API_KEY 環境變數

### 問題 3: 預測準確度低

**原因**: 修正參數未充分訓練

**解決**:
- 至少驗證 10 次以上
- 檢查科學數據品質
- 調整學習率參數

## 商業應用建議

### 1. 地震預警服務
- 整合 Ntfy 推播系統
- 高風險自動發送警報
- 訂閱制收費模式

### 2. 氣象預報增強
- 結合傳統氣象預報
- 提供長期趨勢分析
- 農業、營建業應用

### 3. 金融市場分析
- 股市趨勢預測
- 風險評估工具
- 投資決策輔助

## 未來擴展

### 短期 (1-3 個月)
- [ ] 完整 64 卦資料庫補充
- [ ] 更多科學數據源整合
- [ ] 機器學習模型優化
- [ ] 手機 APP 開發

### 中期 (3-6 個月)
- [ ] 多地區預測支援
- [ ] 歷史事件大數據分析
- [ ] AI 自動解卦系統
- [ ] 社群分享功能

### 長期 (6-12 個月)
- [ ] 全球地震預測網絡
- [ ] 深度學習模型訓練
- [ ] 商業 API 服務
- [ ] 國際化多語言支援

## 技術支援

- 📧 Email: allen34556@gmail.com
- 🌐 官網: <https://jarvis.zhe-wei.net>
- 📚 文檔: `prediction_modules/README.md`
- 🐛 問題回報: GitHub Issues

---

© 2026 築未科技 Zhewei Tech - 易經科學預測系統 v1.0.0

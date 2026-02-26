# 🚨 國家級警報推播系統

## 系統概述

基於 **Ntfy** 推播服務，建立媲美國家級警報的即時推播系統，整合易經科學預測引擎，提供多級別、多類型的災害預警服務。

---

## 🎯 核心特色

### 1. 五級警報系統
- **🆘 國家級緊急 (Level 5)** - 深紅色，持續震動，最高優先級
- **🔴 緊急 (Level 4)** - 紅色，強制顯示，需要立即行動
- **🚨 警報 (Level 3)** - 橙色，震動提示，高度關注
- **⚠️ 注意 (Level 2)** - 黃色，聲音提示，保持警覺
- **ℹ️ 資訊 (Level 1)** - 藍色，一般通知

### 2. 十種警報類型
| 類型 | 圖示 | Ntfy Topic | 說明 |
|------|------|-----------|------|
| 地震 | 🌍 | taiwan_earthquake_alert | 地震預警與即時通報 |
| 海嘯 | 🌊 | taiwan_tsunami_alert | 海嘯警報 |
| 颱風 | 🌀 | taiwan_typhoon_alert | 颱風動態與警報 |
| 水災 | 💧 | taiwan_flood_alert | 淹水與洪水警報 |
| 土石流 | ⛰️ | taiwan_landslide_alert | 土石流警戒 |
| 火災 | 🔥 | taiwan_fire_alert | 大型火災通報 |
| 劇烈天氣 | ⛈️ | taiwan_weather_alert | 雷雨、冰雹等 |
| 空氣品質 | 💨 | taiwan_air_alert | PM2.5、空污警報 |
| 疫情 | 🦠 | taiwan_epidemic_alert | 疫情通報 |
| 經濟 | 📉 | taiwan_economic_alert | 重大經濟事件 |

### 3. 智慧推播功能
- ✅ **自動觸發** - 預測風險超過閾值自動發送
- ✅ **分區推播** - 依影響區域精準推送
- ✅ **多平台支援** - iOS、Android、Web、Desktop
- ✅ **離線可用** - PWA 技術，離線也能查看歷史
- ✅ **即時互動** - 「我安全」回報、分享警報

---

## 📦 系統架構

```
國家級警報系統
├── alert_manager.py          # 警報管理核心
│   ├── NationalAlertManager  # 警報管理器
│   ├── AlertLevel (Enum)     # 5 級警報等級
│   └── AlertType (Enum)      # 10 種警報類型
│
├── prediction_service.py     # FastAPI 服務（整合）
│   ├── 警報 API 端點
│   └── 自動觸發機制
│
├── static/
│   └── alert_receiver.html   # 手機端 PWA 接收器
│       ├── Vue 3 響應式介面
│       ├── Ntfy SSE 即時連線
│       └── 本地通知 API
│
└── alerts.db                 # SQLite 警報資料庫
    ├── alerts               # 警報記錄
    ├── subscribers          # 訂閱者
    ├── delivery_logs        # 發送日誌
    └── alert_statistics     # 統計數據
```

---

## 🚀 快速部署

### 步驟 1: 環境變數設定

在 `.env` 文件中添加：

```bash
# Ntfy 推播服務配置
NTFY_SERVER=https://ntfy.sh
NTFY_ADMIN_USER=taiwan_alert_admin
NTFY_ADMIN_PASS=your_secure_password_here

# 或使用自架 Ntfy 服務器
# NTFY_SERVER=https://notify.zhewei.tech
```

### 步驟 2: 啟動服務

```bash
# 預測系統會自動載入警報管理器
scripts\start_prediction_system.bat
```

### 步驟 3: 訪問警報接收器

- 📱 **手機端**: http://localhost:8025/static/alert_receiver.html
- 💻 **管理後台**: http://localhost:8025/static/prediction_dashboard.html

---

## 📱 手機端 PWA 使用指南

### iOS 安裝步驟
1. Safari 開啟 `http://localhost:8025/static/alert_receiver.html`
2. 點擊「分享」按鈕
3. 選擇「加入主畫面」
4. 完成！現在可以像 APP 一樣使用

### Android 安裝步驟
1. Chrome 開啟警報接收器頁面
2. 點擊「新增至主畫面」提示
3. 或從選單選擇「安裝應用程式」
4. 完成！

### 功能特色
- ✅ **全螢幕顯示** - 無瀏覽器 UI 干擾
- ✅ **推播通知** - 原生系統通知
- ✅ **離線可用** - Service Worker 快取
- ✅ **即時連線** - Ntfy SSE 推送
- ✅ **聲音震動** - 可自訂提示方式

---

## 🔧 API 使用範例

### Python - 發送地震警報

```python
from alert_manager import NationalAlertManager

manager = NationalAlertManager()

# 發送地震警報
alert = manager.send_earthquake_alert(
    magnitude=5.2,
    depth=15.0,
    location="台北市",
    risk_level=75.0,
    prediction_id="EQ_20260215_220000"
)

print(f"警報已發送: {alert.id}")
print(f"發送狀態: {alert.delivery_status}")
```

### Python - 發送氣象警報

```python
alert = manager.send_weather_alert(
    weather_type="強風",
    severity=65.0,
    forecast_period="未來3-7天",
    prediction_id="WX_20260215_220100"
)
```

### Python - 廣播緊急通知

```python
# 發送到所有主題
alerts = manager.broadcast_emergency(
    title="🆘 國家級緊急警報",
    message="請立即採取避難措施！"
)
```

### REST API - 發送自訂警報

```bash
curl -X POST http://localhost:8025/api/alerts/send \
  -H "Content-Type: application/json" \
  -d '{
    "alert_type": "earthquake",
    "alert_level": 4,
    "title": "地震警報",
    "message": "預測規模 M5.2 地震",
    "area": "台北市"
  }'
```

### JavaScript - 訂閱警報

```javascript
// 使用 Ntfy SSE
const eventSource = new EventSource('https://ntfy.sh/taiwan_earthquake_alert/sse');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.event === 'message') {
        console.log('收到警報:', data.title, data.message);
        
        // 顯示系統通知
        new Notification(data.title, {
            body: data.message,
            icon: '/alert-icon.png',
            vibrate: [200, 100, 200]
        });
    }
};
```

---

## 🎨 警報等級配置

### Level 5 - 國家級緊急 🆘
```python
{
    'icon': '🆘',
    'color': '#991B1B',  # 深紅色
    'priority': 5,
    'sound': 'emergency',
    'vibrate': True,
    'require_interaction': True  # 必須手動關閉
}
```

**觸發條件:**
- 地震規模 ≥ 6.0 或風險 ≥ 80%
- 海嘯警報
- 重大災害

**行為:**
- 持續震動和聲音
- 全螢幕彈出
- 無法自動關閉
- 廣播到所有主題

### Level 4 - 緊急 🔴
**觸發條件:**
- 地震規模 5.0-5.9 或風險 60-79%
- 颱風警報
- 嚴重天氣

### Level 3 - 警報 🚨
**觸發條件:**
- 地震規模 4.0-4.9 或風險 40-59%
- 水災、土石流警戒

### Level 2 - 注意 ⚠️
**觸發條件:**
- 地震規模 3.0-3.9 或風險 20-39%
- 一般天氣警報

### Level 1 - 資訊 ℹ️
**觸發條件:**
- 系統通知
- 經濟資訊
- 一般公告

---

## 🔄 自動觸發機制

### 預測系統整合

警報管理器已整合到預測引擎，當預測風險超過閾值時自動發送警報：

```python
# 在 prediction_service.py 的自動監測任務中
async def auto_monitor_task():
    while True:
        anomaly = data_collector.calculate_anomaly_indicators()
        
        if anomaly['total_anomaly'] > 0.6:
            # 執行地震預測
            eq_prediction = prediction_engine.predict_earthquake()
            
            # 自動發送警報
            if eq_prediction.risk_level > 70:
                alert = alert_manager.send_earthquake_alert(
                    magnitude=eq_prediction.risk_level / 15,  # 簡化轉換
                    depth=15.0,
                    location="台灣",
                    risk_level=eq_prediction.risk_level,
                    prediction_id=eq_prediction.id
                )
                
                # 廣播到 WebSocket
                await manager.broadcast({
                    "type": "high_risk_alert",
                    "alert": alert.to_dict()
                })
        
        await asyncio.sleep(3600)  # 每小時檢查
```

---

## 📊 統計與監控

### 獲取警報統計

```python
stats = manager.get_statistics(days=7)

print(f"7天內總警報數: {stats['total_alerts']}")
print(f"按類型統計: {stats['by_type']}")
print(f"按等級統計: {stats['by_level']}")
print(f"發送成功率: {stats['delivery_success_rate']}%")
```

### 查詢警報歷史

```python
# 獲取最近 50 筆警報
history = manager.get_alert_history(limit=50)

# 僅查詢地震警報
eq_alerts = manager.get_alert_history(limit=50, alert_type='earthquake')
```

---

## 🌐 外網部署

### 使用 Cloudflare Tunnel

在 `gateway/nginx.conf` 添加：

```nginx
location /alerts/ {
    proxy_pass http://host.docker.internal:8025/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

添加域名到 Tunnel：
```yaml
ingress:
  - hostname: alert.zhe-wei.net
    service: http://localhost:8025
```

### 使用自架 Ntfy 服務器

**優勢:**
- 無限推播次數
- 自訂域名
- 完全控制
- 更高可靠性

**部署步驟:**

```bash
# Docker 部署 Ntfy
docker run -d \
  --name ntfy \
  -p 8080:80 \
  -v /var/cache/ntfy:/var/cache/ntfy \
  binwiederhier/ntfy \
  serve --cache-file /var/cache/ntfy/cache.db

# 設定環境變數
NTFY_SERVER=https://notify.zhewei.tech
```

---

## 🔐 安全性考量

### 1. 認證機制
- 管理員帳號密碼（發送警報）
- 客戶端唯讀訂閱（接收警報）
- JWT Token 驗證（API 調用）

### 2. 防濫用
- 發送頻率限制
- IP 白名單
- API Key 驗證

### 3. 數據加密
- HTTPS 傳輸
- 敏感資訊加密儲存

---

## 📈 商業應用場景

### 1. 政府機關
- 災害防救中心
- 氣象局預警系統
- 消防局緊急通報

### 2. 企業應用
- 工地安全警報
- 物流運輸預警
- 金融風險通知

### 3. 社區服務
- 社區防災系統
- 學校安全通報
- 大樓管理警報

---

## 🎓 進階功能

### 1. 地理圍欄推播
```python
# 僅推送給特定區域
alert = manager.send_alert(
    alert_type=AlertType.EARTHQUAKE,
    alert_level=AlertLevel.CRITICAL,
    title="台北市地震警報",
    message="預測規模 M5.2",
    area="台北市",
    custom_data={
        'geo_fence': {
            'lat': 25.0330,
            'lon': 121.5654,
            'radius_km': 50
        }
    }
)
```

### 2. 多語言支援
```python
alert = manager.send_alert(
    title="Earthquake Alert",
    message="Magnitude 5.2 predicted",
    custom_data={
        'translations': {
            'zh-TW': {'title': '地震警報', 'message': '預測規模 M5.2'},
            'en': {'title': 'Earthquake Alert', 'message': 'M5.2 predicted'},
            'ja': {'title': '地震警報', 'message': 'M5.2予測'}
        }
    }
)
```

### 3. 優先級訂閱
```python
# 用戶可選擇接收的最低等級
subscriber_settings = {
    'min_level': AlertLevel.ALERT,  # 僅接收警報級別以上
    'types': ['earthquake', 'tsunami'],  # 僅訂閱特定類型
    'quiet_hours': {'start': '23:00', 'end': '07:00'}  # 勿擾時段
}
```

---

## 🛠️ 故障排除

### 問題 1: 推播未收到

**檢查清單:**
- [ ] 確認 Ntfy 服務器連線正常
- [ ] 檢查訂閱的 Topic 是否正確
- [ ] 驗證瀏覽器通知權限已開啟
- [ ] 查看 delivery_logs 表確認發送狀態

**解決方案:**
```python
# 測試 Ntfy 連線
import requests
response = requests.get('https://ntfy.sh/taiwan_earthquake_alert/json?poll=1')
print(response.json())
```

### 問題 2: PWA 無法安裝

**原因:** 需要 HTTPS 或 localhost

**解決:**
- 本地測試使用 localhost
- 生產環境使用 HTTPS (Cloudflare Tunnel)
- 確保 manifest.json 正確配置

### 問題 3: 警報延遲

**優化方案:**
- 使用 WebSocket 替代 SSE
- 部署自架 Ntfy 服務器
- 優化資料庫查詢索引

---

## 📝 資料庫結構

### alerts 表
```sql
CREATE TABLE alerts (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    alert_level INTEGER NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    area TEXT,
    prediction_id TEXT,
    expires_at TEXT,
    sent_count INTEGER DEFAULT 0,
    delivery_status TEXT DEFAULT 'pending',
    ntfy_response TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### subscribers 表
```sql
CREATE TABLE subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT UNIQUE,
    device_name TEXT,
    platform TEXT,
    subscribed_topics TEXT,
    subscribed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_active TEXT,
    is_active INTEGER DEFAULT 1
);
```

---

## 🎯 未來擴展

### 短期 (1-3 個月)
- [ ] AI 語音播報警報
- [ ] 地圖視覺化顯示
- [ ] 歷史警報回放
- [ ] 警報分享社群

### 中期 (3-6 個月)
- [ ] 機器學習優化觸發閾值
- [ ] 多語言自動翻譯
- [ ] 區塊鏈警報存證
- [ ] 跨國警報聯網

### 長期 (6-12 個月)
- [ ] 衛星通訊備援
- [ ] 量子加密傳輸
- [ ] 全球災害預警網絡
- [ ] AI 自動應變建議

---

## 📞 技術支援

- 📧 Email: allen34556@gmail.com
- 🌐 官網: https://jarvis.zhe-wei.net
- 📚 文檔: `prediction_modules/NATIONAL_ALERT_SYSTEM.md`
- 🐛 問題回報: GitHub Issues

---

© 2026 築未科技 Zhewei Tech - 國家級警報推播系統 v1.0.0

**⚠️ 免責聲明**: 本系統為預測輔助工具，不應作為唯一的災害預警依據。請以官方發布的警報為準。

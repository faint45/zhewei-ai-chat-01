# API 監控系統使用指南

> 築未科技統一API系統 - 實時監控與分析

---

## 📊 功能概覽

### 核心功能

| 功能 | 說明 |
|------|------|
| **實時監控** | 追蹤所有 API 請求的執行狀態 |
| **流量統計** | 按小時/日/週/月統計請求數量 |
| **費用追蹤** | 記錄每個請求的 token 使用和費用 |
| **性能分析** | 計算平均響應時間和成功率 |
| **告警機制** | 自動檢測異常費用和錯誤率 |
| **報告生成** | 生成日報/週報/月報 JSON 文件 |
| **可視化面板** | 直觀的圖表和數據展示 |

---

## 🚀 快速開始

### 1. 啟動監控面板

```bash
# Windows
啟動監控面板.bat

# 或手動啟動
python monitoring_dashboard.py
```

訪問: http://localhost:8001

### 2. 運行測試腳本

```bash
# Windows
test_monitoring.bat

# 或手動運行
python test_monitoring.py
```

測試腳本會模擬 50 個 API 請求，生成測試數據。

---

## 📖 使用說明

### 監控面板

訪問 http://localhost:8001 查看：

1. **指標卡片**
   - 總請求數
   - 成功率
   - 平均響應時間
   - 總 Token 數
   - 總費用
   - 失敗請求

2. **圖表**
   - 請求趨勢（小時）
   - 費用趨勢
   - 來源分佈
   - 響應時間分佈

3. **請求記錄**
   - 最近 50 個請求的詳細記錄
   - 時間、來源、用戶、命令、狀態、執行時間、Token、費用

4. **告警信息**
   - 費用告警（每日超過 $10）
   - 錯誤率告警（超過 10%）

### API 接口

#### 獲取指標

```
GET /api/metrics?period={period}&source={source}
```

參數:
- `period`: today, week, month
- `source`: telegram, discord, wechat, web (可選)

#### 獲取請求記錄

```
GET /api/requests?limit={limit}
```

參數:
- `limit`: 返回記錄數量（默認 50）

#### 獲取小時統計

```
GET /api/hourly-stats?hours={hours}
```

參數:
- `hours`: 小時數（默認 24）

#### 獲取每日統計

```
GET /api/daily-stats?days={days}
```

參數:
- `days`: 天數（默認 7）

#### 獲取告警

```
GET /api/alerts?limit={limit}
```

參數:
- `limit`: 返回告警數量（默認 20）

#### 記錄請求

```
POST /api/log-request
Content-Type: application/json

{
  "request_id": "req_123456",
  "source": "telegram",
  "user_id": "user_001",
  "command": "ai:你好",
  "status": "success",
  "execution_time": 0.5,
  "tokens_used": 150,
  "cost": 0.0003
}
```

#### 生成報告

```
GET /api/report/{report_type}
```

參數:
- `report_type`: daily, weekly, monthly

返回 JSON 報告，可下載保存。

---

## 🔧 集成到現有服務

### 在 website_server.py 中集成

```python
from monitoring_service import monitor
import time

@app.post("/api/chat")
async def chat(request: dict):
    start_time = time.time()
    
    try:
        # 執行 AI 對話
        response = await ai_service.generate_response(request['message'])
        
        # 記錄請求
        execution_time = time.time() - start_time
        await monitor.log_request(
            request_id=f"req_{int(time.time()*1000)}",
            source="web",
            user_id=request.get('user_id', 'anonymous'),
            command=request['message'][:100],
            status="success",
            execution_time=execution_time,
            tokens_used=estimate_tokens(response),  # 估算 token 數
            cost=calculate_cost(tokens_used)  # 計算費用
        )
        
        return {"response": response}
        
    except Exception as e:
        # 記錄失敗請求
        execution_time = time.time() - start_time
        await monitor.log_request(
            request_id=f"req_{int(time.time()*1000)}",
            source="web",
            user_id=request.get('user_id', 'anonymous'),
            command=request['message'][:100],
            status="error",
            execution_time=execution_time
        )
        raise
```

### 在 remote_control_server.py 中集成

```python
from monitoring_service import monitor
import time

@app.post("/v1/execute")
async def execute_command(request: UnifiedExecuteRequest):
    start_time = time.time()
    
    try:
        # 執行命令
        result = await process_command(request.command)
        
        # 記錄請求
        execution_time = time.time() - start_time
        await monitor.log_request(
            request_id=request.context_id or f"req_{int(time.time()*1000)}",
            source=request.source,
            user_id=request.user_id,
            command=request.command[:100],
            status="success",
            execution_time=execution_time
        )
        
        return result
        
    except Exception as e:
        # 記錄失敗
        execution_time = time.time() - start_time
        await monitor.log_request(
            request_id=request.context_id or f"req_{int(time.time()*1000)}",
            source=request.source,
            user_id=request.user_id,
            command=request.command[:100],
            status="error",
            execution_time=execution_time
        )
        raise
```

### 在 telegram_bot.py 中集成

```python
from monitoring_service import monitor
import time

async def handle_message(update, context):
    start_time = time.time()
    
    try:
        # 處理消息
        response = await process_message(update.message.text)
        
        # 記錄請求
        execution_time = time.time() - start_time
        await monitor.log_request(
            request_id=f"tg_{update.message.message_id}",
            source="telegram",
            user_id=str(update.message.from_user.id),
            command=update.message.text[:100],
            status="success",
            execution_time=execution_time
        )
        
        await update.message.reply_text(response)
        
    except Exception as e:
        # 記錄失敗
        execution_time = time.time() - start_time
        await monitor.log_request(
            request_id=f"tg_{update.message.message_id}",
            source="telegram",
            user_id=str(update.message.from_user.id),
            command=update.message.text[:100],
            status="error",
            execution_time=execution_time
        )
```

---

## ⚙️ 配置選項

### 修改費用閾值

編輯 `monitoring_service.py`:

```python
class APIMonitor:
    def __init__(self, db_path: str = "api_monitoring.db"):
        # ...
        self.cost_threshold = 10.0  # 修改每日費用閾值（USD）
        self.error_rate_threshold = 0.1  # 修改錯誤率閾值（10%）
```

### 修改監控端口

編輯 `monitoring_dashboard.py`:

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)  # 修改端口
```

---

## 📊 數據庫結構

### api_requests 表

| 字段 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | 主鍵 |
| request_id | TEXT | 請求唯一 ID |
| timestamp | TEXT | 請求時間 |
| source | TEXT | 來源（telegram/discord/wechat/web） |
| user_id | TEXT | 用戶 ID |
| command | TEXT | 命令內容 |
| status | TEXT | 狀態（success/error） |
| execution_time | REAL | 執行時間（秒） |
| tokens_used | INTEGER | 使用的 token 數 |
| cost | REAL | 費用（USD） |

### hourly_stats 表

| 字段 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | 主鍵 |
| hour | TEXT | 小時（YYYY-MM-DD HH:00） |
| source | TEXT | 來源 |
| requests | INTEGER | 請求數 |
| tokens | INTEGER | token 總數 |
| cost | REAL | 總費用 |
| errors | INTEGER | 錯誤數 |

### daily_stats 表

| 字段 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | 主鍵 |
| date | TEXT | 日期（YYYY-MM-DD） |
| source | TEXT | 來源 |
| requests | INTEGER | 請求數 |
| tokens | INTEGER | token 總數 |
| cost | REAL | 總費用 |
| errors | INTEGER | 錯誤數 |

### alerts 表

| 字段 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | 主鍵 |
| timestamp | TEXT | 告警時間 |
| alert_type | TEXT | 告警類型（cost_alert/error_rate_alert） |
| severity | TEXT | 嚴重程度（warning/critical） |
| message | TEXT | 告警信息 |
| resolved | BOOLEAN | 是否已解決 |

---

## 🎯 使用場景

### 場景 1: 監控每日費用

1. 訪問監控面板
2. 查看指標卡片的「總費用」
3. 如果超過閾值，會自動告警
4. 生成日報並保存

### 場景 2: 分析 API 性能

1. 查看「平均響應時間」
2. 查看「成功率」
3. 如果響應時間過長或成功率過低，檢查系統

### 場景 3: 了解用戶行為

1. 查看「來源分佈」圖表
2. 查看「請求趨勢」
3. 了解哪些平台使用最多

### 場景 4: 調試失敗請求

1. 查看「失敗請求」計數
2. 在「最近請求記錄」表格中篩選狀態為「失敗」的記錄
3. 分析失敗原因

---

## 🔍 故障排查

### 問題: 監控面板無法訪問

**解決方案:**
```bash
# 檢查端口是否被佔用
netstat -ano | findstr ":8001"

# 如果被佔用，停止占用進程或修改端口
```

### 問題: 數據庫文件不存在

**解決方案:**
```python
# 監控服務會自動創建數據庫
# 如果出錯，手動刪除數據庫文件讓其重新創建
del api_monitoring.db
```

### 問題: API 請求未記錄

**解決方案:**
1. 檢查監控服務是否正在運行
2. 檢查網絡連接
3. 查看日誌輸出

---

## 📈 優化建議

1. **定期清理數據**
   ```python
   # 刪除 30 天前的數據
   DELETE FROM api_requests WHERE timestamp < date('now', '-30 days')
   ```

2. **添加更多指標**
   - 用戶活躍度
   - 命令類型分佈
   - 錯誤類型統計

3. **集成告警通知**
   - 郵件通知
   - Telegram/Discord 機器人通知
   - 短信通知

4. **添加實時推送**
   - WebSocket 實時更新
   - 即時告警推送

---

## 📞 技術支持

如有問題，請檢查:
1. 日誌輸出
2. 數據庫文件是否存在
3. 網絡連接是否正常
4. Python 依賴是否完整安裝

---

**築未科技 API 監控系統 - 您的 API 可視化助手** 📊

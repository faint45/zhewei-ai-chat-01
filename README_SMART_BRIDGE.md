# 🌉 Smart Bridge - 智慧型對話橋接服務

## 概述

Smart Bridge 是築未科技的外網對話系統，提供：
- **兩階段智慧生成**：低成本模型建立框架 + 高品質模型精修
- **即時視覺反饋**：WebSocket 即時顯示 AI 運作過程
- **本地模型學習控制**：協助 Ollama 模型進行自動化學習

## 快速啟動

### 方法 1: 獨立啟動 (開發/測試)

```bash
# Windows
scripts\start_smart_bridge.bat

# 或直接執行
python smart_bridge.py
```

訪問：`http://localhost:8003`

### 方法 2: Docker Compose (生產環境)

```bash
# 啟動所有服務 (包含 Smart Bridge)
docker compose up -d

# 僅啟動 Smart Bridge
docker compose up -d smart_bridge

# 查看日誌
docker compose logs -f smart_bridge
```

訪問：
- 本地：`http://localhost:8003`
- 外網：`https://bridge.zhe-wei.net` (需 Cloudflare Tunnel)

## 核心功能

### 1. 兩階段智慧生成 (節省 70-80% 成本)

```
Phase 1 (80%) → Ollama 本地 / Groq 免費
    ↓
Phase 2 (20%) → Gemini / Claude 精修
```

**成本對比**：
- 傳統方式 (全用 Claude)：~$0.0015
- Smart Bridge：~$0.0003
- **節省：80%**

### 2. 即時視覺化運作過程

WebSocket 即時推送每個階段：
- 🚀 Phase 1 開始
- ⚙️ 低成本模型生成中
- ✅ Phase 1 完成
- 🎨 Phase 2 精修中
- 🎉 完成 + 成本統計

### 3. 本地 Ollama 學習控制

```python
# 檢查 Ollama 狀態
ws.send({"type": "learn", "action": "status"})

# 啟動學習主題
ws.send({
    "type": "learn",
    "action": "learn_topic",
    "topic": "FastAPI WebSocket 即時通訊",
    "depth": "standard"  # quick/standard/deep
})
```

學習流程：
1. 分析主題範圍
2. 查詢現有知識庫
3. 產生學習計劃
4. 多輪學習 + 萃取精華
5. 儲存到知識庫

## API 文檔

### REST API

#### GET /health
健康檢查

**回應**：
```json
{
    "status": "ok",
    "service": "smart-bridge",
    "version": "1.0.0",
    "sessions": 0
}
```

#### GET /api/cost-stats
成本統計

**回應**：
```json
{
    "ok": true,
    "total_cost": 0.0123,
    "saved_cost": 0.0456,
    "total_requests": 42,
    "efficiency": "78.8%"
}
```

#### POST /api/generate
兩階段生成

**請求**：
```json
{
    "prompt": "寫一個 Python WebSocket 伺服器",
    "task_type": "code"
}
```

**task_type 選項**：
- `code`: 程式碼生成
- `text`: 文字內容
- `analysis`: 分析報告
- `learning`: 學習材料

**回應**：
```json
{
    "ok": true,
    "content": "生成的內容...",
    "phase1": {
        "provider": "ollama",
        "duration_ms": 1234,
        "tokens": 500
    },
    "phase2": {
        "provider": "gemini",
        "duration_ms": 2345,
        "tokens": 600
    },
    "cost_usd": 0.0003,
    "saved_usd": 0.0012,
    "improvements": ["改進1", "改進2"]
}
```

### WebSocket API

**連接**：`ws://localhost:8003/ws`

#### 發送訊息格式

**對話訊息**：
```json
{
    "type": "chat",
    "text": "使用者輸入",
    "task_type": "code"
}
```

**學習控制**：
```json
{
    "type": "learn",
    "action": "status"
}
```

```json
{
    "type": "learn",
    "action": "learn_topic",
    "topic": "主題名稱",
    "depth": "standard"
}
```

#### 接收訊息格式

**連接成功**：
```json
{
    "type": "connected",
    "session_id": "session_abc123",
    "message": "🌉 Smart Bridge 已連接！"
}
```

**運作過程**：
```json
{
    "type": "operation",
    "stage": "phase1_start",
    "message": "🚀 Phase 1: 低成本模型建立框架...",
    "progress": 0
}
```

**最終結果**：
```json
{
    "type": "response",
    "content": "生成的內容",
    "meta": {
        "phase1_provider": "ollama",
        "phase2_provider": "gemini",
        "cost_usd": 0.0003,
        "saved_usd": 0.0012
    }
}
```

**學習狀態**：
```json
{
    "type": "learn_status",
    "status": "online",
    "models": [...]
}
```

## 環境變數

| 變數 | 預設 | 說明 |
|------|------|------|
| `SMART_BRIDGE_PORT` | 8003 | 服務端口 |
| `SMART_BRIDGE_HOST` | 0.0.0.0 | 綁定地址 |
| `OLLAMA_BASE_URL` | http://localhost:11434 | Ollama 服務地址 |
| `GEMINI_API_KEY` | - | Gemini API Key (必需) |
| `ANTHROPIC_API_KEY` | - | Claude API Key (選填) |

## 檔案結構

```
zhe-wei-tech/
├── smart_bridge.py                 # 主服務
├── ollama_learning_controller.py   # 學習控制模組
├── test_smart_bridge.py            # 整合測試
├── bridge_workspace/
│   └── static/
│       └── bridge.html             # 前端界面
├── scripts/
│   └── start_smart_bridge.bat     # Windows 啟動腳本
├── gateway/
│   └── nginx.conf                  # Nginx 配置
├── docker-compose.yml              # Docker 編排
└── docs/
    └── smart_bridge_deploy.md      # 部署文件
```

## 測試

執行整合測試：

```bash
python test_smart_bridge.py
```

測試項目：
- ✅ Health Check
- ✅ 成本統計 API
- ✅ 前端頁面
- ✅ 兩階段生成 API

## 成本分析

### 單次請求成本對比 (500 tokens 輸入 + 1000 tokens 輸出)

| 方案 | 成本 | 說明 |
|------|------|------|
| 全用 Claude Sonnet | $0.0150 | 高品質但昂貴 |
| 全用 Gemini Pro | $0.0015 | 中等成本 |
| **Smart Bridge** | **$0.0003** | **節省 80-98%** |
| 全用 Ollama | $0.0000 | 免費但品質較低 |

### Smart Bridge 成本結構

- Phase 1 (Ollama): $0.0000 (本地免費)
- Phase 2 (Gemini 20% tokens): $0.0003
- **總計**: $0.0003

### 月度成本估算 (1000 次請求/月)

- 傳統 Claude: $15.00/月
- **Smart Bridge**: $0.30/月
- **節省**: $14.70/月 (98%)

## 外網訪問設定

### Cloudflare Tunnel 配置

1. Nginx 配置已自動添加 (`gateway/nginx.conf`)：
   ```nginx
   server {
       listen 80;
       server_name bridge.zhe-wei.net;
       location / {
           proxy_pass http://host.docker.internal:8003;
           # WebSocket 支援
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection $connection_upgrade;
       }
   }
   ```

2. 重啟 Gateway 容器：
   ```bash
   docker compose restart gateway
   ```

3. 訪問：`https://bridge.zhe-wei.net`

## 故障排除

### Port 8003 已被佔用

```bash
# Windows
netstat -ano | findstr :8003
taskkill /F /PID <PID>

# Linux/Mac
lsof -ti:8003 | xargs kill -9
```

### Ollama 連接失敗

檢查 Ollama 是否運行：
```bash
curl http://localhost:11434/api/tags
```

### WebSocket 連接失敗

檢查防火牆設定，確保 8003 端口開放。

## 後續優化

- [ ] 添加用戶認證 (整合現有 auth_manager)
- [ ] 資料庫持久化對話歷史
- [ ] 更多模型支援 (DeepSeek, Mistral)
- [ ] 學習內容管理界面
- [ ] 成本告警與預算控制
- [ ] 多語言支援
- [ ] API Rate Limiting

## 授權

© 2026 築未科技 Zhe-Wei Tech. All rights reserved.

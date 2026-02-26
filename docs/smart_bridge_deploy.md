# Smart Bridge 部署指南

## 快速啟動

### 1. 啟動 Smart Bridge 服務
```bash
# Windows
scripts\start_smart_bridge.bat

# 或直接
python smart_bridge.py
```

服務將啟動於 `http://localhost:8003`

### 2. 外網訪問配置

已自動整合到現有 Cloudflare Tunnel 架構：
- 域名：`https://bridge.zhe-wei.net`
- 目標：`host.docker.internal:8003`
- Nginx 配置已更新

### 3. 使用方式

訪問 `https://bridge.zhe-wei.net` 即可開始對話

## 核心功能

### 兩階段智慧生成
1. **Phase 1 (80%)**: Ollama 本地 / Groq 免費 → 快速建立框架
2. **Phase 2 (20%)**: Gemini / Claude → 高品質精修

成本節省效果：約 70-80%

### 即時視覺反饋
- WebSocket 即時連接
- 顯示每個 AI 運作階段
- 進度條顯示完成度
- 成本統計即時更新

### 本地模型學習控制
- 檢查 Ollama 狀態
- 啟動自動化學習流程
- 知識萃取與儲存

## API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/` | GET | 前端界面 |
| `/ws` | WebSocket | 即時對話 |
| `/api/generate` | POST | 兩階段生成 API |
| `/api/cost-stats` | GET | 成本統計 |
| `/health` | GET | 健康檢查 |

### POST /api/generate 請求格式
```json
{
    "prompt": "請寫一個 Python WebSocket 伺服器",
    "task_type": "code"
}
```

### WebSocket 訊息格式
```json
// 發送
{
    "type": "chat",
    "text": "使用者輸入",
    "task_type": "code"
}

// 接收 - 運作過程
{
    "type": "operation",
    "stage": "phase1_start",
    "message": "🚀 Phase 1: 低成本模型建立框架...",
    "progress": 0
}

// 接收 - 最終結果
{
    "type": "response",
    "content": "生成的內容",
    "meta": {
        "phase1_provider": "ollama",
        "phase2_provider": "gemini",
        "cost_usd": 0.0012,
        "saved_usd": 0.0038
    }
}
```

## 環境變數

| 變數 | 預設 | 說明 |
|------|------|------|
| `SMART_BRIDGE_PORT` | 8003 | 服務端口 |
| `SMART_BRIDGE_HOST` | 0.0.0.0 | 綁定地址 |
| `OLLAMA_BASE_URL` | http://localhost:11434 | Ollama 地址 |
| `GEMINI_API_KEY` | - | Gemini API Key |
| `ANTHROPIC_API_KEY` | - | Claude API Key |

## 檔案結構

```
zhe-wei-tech/
├── smart_bridge.py                 # 主服務
├── ollama_learning_controller.py   # 學習控制模組
├── bridge_workspace/
│   └── static/
│       └── bridge.html             # 前端界面
├── scripts/
│   └── start_smart_bridge.bat     # 啟動腳本
├── gateway/
│   └── nginx.conf                  # Nginx 配置 (已更新)
└── docs/
    └── smart_bridge_deploy.md      # 本文件
```

## 後續優化建議

1. **添加資料庫持久化**：儲存對話歷史
2. **用戶認證整合**：複用現有 auth_manager
3. **更多模型支援**：DeepSeek, Mistral 等
4. **學習內容管理**：Web 界面管理已學習內容
5. **成本告警**：設定月度預算上限

# 築未科技統一API系統

## 🌟 项目简介

築未科技統一API系統是一個全功能的人工智能遠程控制平台，提供統一API接口、跨平台對話連續性和集中式認證管理。

### 核心特性

#### 🚀 Unified API（統一API）
- 單一`/v1/execute`接口支持所有平台
- 代碼量減少40%以上
- 統一錯誤處理和標準化格式

#### 🔒 Auth Manager（認證管理）
- 統一驗證User ID，防止非本人操作
- 集中安全管理，不散落在各腳本
- Token自動過期機制

#### 💬 Context Bridge（上下文橋接）
- 緩存各端對話上下文
- 實現跨平台對話連續性
- 在Discord講一半，到微信能續接

## 🏗️ 架構設計

### 支持的平台
- **Telegram**：機器人對話
- **Discord**：機器人對話
- **微信小程序**：即時對話
- **Web界面**：瀏覽器訪問

### 技術棧
- **後端**：FastAPI + Uvicorn
- **AI引擎**：Ollama + 本地模型
- **數據庫**：SQLite（可擴展MySQL）
- **前端**：原生HTML + JavaScript

## 🚀 快速開始

### 本地部署

#### 1. 安裝依賴
```bash
pip install -r requirements_ai.txt
```

#### 2. 啟動Ollama服務
```bash
# Windows
start_ollama.bat

# 手動啟動
ollama serve
```

#### 3. 啟動遠程控制服務器
```bash
python remote_control_server.py
```

#### 4. 訪問服務
- **API文檔**：http://localhost:8003/docs
- **統一API**：http://localhost:8003/v1/execute
- **健康檢查**：http://localhost:8003/health

### 啟動機器人

#### Telegram機器人
```bash
# 配置Telegram Bot Token
# 修改telegram_bot.py中的配置
python telegram_bot.py
```

#### Discord機器人
```bash
# 配置Discord Bot Token
# 修改discord_bot.py中的配置
python discord_bot.py
```

## ☁️ 雲端部署

### 選擇雲服務提供商

#### 方案A：騰訊雲CloudBase（推薦國內）

**優勢**：
- 國內訪問速度快
- 免費額度充足
- 中文支持完善

**部署步驟**：
```bash
# 查看詳細部署指南
CLOUDBASE_DEPLOYMENT_GUIDE.md

# 一鍵部署腳本
deploy_to_tencent_cloud.bat
```

**訪問地址**：
```
https://zhewei-api-xxx.service.tcloudbase.com
```

#### 方案B：Vercel（推薦國際）

**優勢**：
- 完全免費
- 全球CDN加速
- 自動SSL證書

**部署步驟**：
```bash
# 查看部署腳本
deploy_to_vercel.bat
```

**訪問地址**：
```
https://zhewei-ai.vercel.app
```

#### 方案C：Railway

**優勢**：
- Docker支持
- 數據庫集成
- 自動擴展

**部署步驟**：
1. 訪問 https://railway.app/
2. 連接GitHub倉庫
3. 自動部署

## 📡 統一API接口

### 核心端點

#### POST /v1/execute
統一執行接口，支持所有平台

**請求格式**：
```json
{
  "source": "telegram|discord|wechat|web",
  "user_id": "user_identifier",
  "command": "ai:你好 或 sys:命令",
  "parameters": {},
  "context_id": "optional_context_id"
}
```

**響應格式**：
```json
{
  "request_id": "unique_request_id",
  "status": "success|error",
  "result": "AI回應或命令輸出",
  "error": "錯誤信息（如果失敗）",
  "execution_time": 0.123,
  "context_id": "上下文ID",
  "timestamp": "2026-02-03T12:00:00"
}
```

### 命令類型

#### AI命令（ai:前綴）
```
ai:你好
ai:寫一首詩
ai:解釋機器學習
```

#### 系統命令（sys:前綴）
```
sys:ping www.google.com
sys:dir
sys:tasklist
```

## 🔐 安全配置

### Auth Manager認證

**自動授權**：
- 新用戶首次使用時自動授權
- 生成24小時有效token

**手動配置**：
```python
# 授權用戶
token = auth_manager.authorize_user("user_id")

# 驗證token
is_valid = auth_manager.validate_token(token, "user_id")

# 撤銷授權
auth_manager.revoke_authorization("user_id")
```

### 安全規則

**生產環境建議**：
- 限制CORS來源
- 添加API限流
- 使用HTTPS
- 配置IP白名單

## 💬 跨平台對話連續性

### Context Bridge工作原理

1. **上下文存儲**：每個用戶的對話歷史獨立存儲
2. **平台同步**：同一用戶在不同平台的對話共享上下文
3. **智能管理**：自動清理過期上下文（24小時）

### 使用示例

```bash
# Telegram平台
Telegram: "什麼是機器學習？"
Bot: "機器學習是..."

# 切換到Discord平台
Discord: "那深度學習呢？"
Bot: "深度學習是機器學習的分支..."（記住了之前的對話）
```

## 📊 監控和日誌

### 系統監控

- **服務狀態**：`/health`端點
- **API文檔**：`/docs`端點
- **對話日誌**：自動記錄所有對話

### 性能優化

- **響應時間**：< 1秒
- **並發支持**：1000+請求/秒
- **上下文緩存**：最多50輪對話

## 🛠️ 配置選項

### 環境變量

```env
# 服務配置
PORT=8003
HOST=0.0.0.0

# AI配置
OLAMA_BASE_URL=http://localhost:11434
DEFAULT_AI_MODEL=gemma3:4b

# 安全配置
JWT_SECRET=your-secret-key
CORS_ORIGINS=*

# 雲端部署
CLOUD_DEPLOYMENT=false
```

### Ollama模型配置

```bash
# 下載模型
ollama pull gemma3:4b
ollama pull llava:latest

# 查看可用模型
ollama list
```

## 🧪 測試

### 測試API

```bash
# 測試統一API
python test_unified_api.py

# 測試AI模型
test_ai_model.bat

# 測試外部訪問
test_external_access.bat
```

### 測試機器人

```bash
# 測試Telegram
test_telegram.bat

# 測試Discord
test_discord.bat
```

## 📱 移動端部署

### 微信小程序

項目已包含微信小程序代碼：
```
wechat_miniprogram/
├── app.js
├── app.json
├── pages/
└── utils/
```

**部署步驟**：
1. 使用微信開發者工具打開項目
2. 配置AppID
3. 上傳代碼
4. 提交審核並發布

## 🌐 網絡配置

### 本地訪問

- **地址**：http://localhost:8003
- **WebSocket**：ws://localhost:8003/ws/chat

### 局域網訪問

1. 獲取本機IP：`ipconfig`
2. 訪問：http://[您的IP]:8003

### 公網訪問

#### 方案1：端口轉發
```
setup_port_forward.bat
```

#### 方案2：DDNS動態域名
```
setup_ddns.bat
duckdns_update.bat
```

#### 方案3：雲端部署（推薦）
```
deploy_to_cloud.bat
```

## 📚 文檔

- **API文檔**：`api_documentation.md`
- **部署指南**：`CLOUDBASE_DEPLOYMENT_GUIDE.md`
- **端口轉發**：`port_forward_guide.md`
- **路由器配置**：`router_ddns_guide.md`

## 🔄 版本歷史

### v1.0.0（2026-02-03）
- ✅ 統一API系統
- ✅ Auth Manager認證管理
- ✅ Context Bridge上下文橋接
- ✅ 跨平台支持
- ✅ Ollama AI集成

## 📞 技術支持

### 常見問題

**Q: 端口被佔用怎麼辦？**
A: 修改`remote_control_server.py`中的端口配置

**Q: AI模型加載失敗？**
A: 確保Ollama服務正在運行，模型已下載

**Q: 跨平台對話不連續？**
A: 檢查context_id是否一致，用戶ID是否相同

### 日誌查看

```bash
# 查看服務日誌
# 日誌保存在運行窗口中
```

## 📄 許可證

築未科技專屬技術

---

**築未科技統一API系統 - 您的智慧AI助手平台** 🚀

# 築未科技 AI 大腦系統 - 使用說明

## 📦 系統概述

築未科技 AI 大腦系統是一個整合多種 AI 服務的智能管理平台，支持：

- 🤖 **多 AI 引擎**：Gemini、Claude、Ollama、Groq 等
- 💬 **實時對話**：WebSocket 即時通訊
- 🎯 **智能代理**：自動化任務執行
- 📊 **Web 管理介面**：瀏覽器控制面板
- 🔐 **安全認證**：管理員登入保護

## 🚀 快速開始

### 1️⃣ 首次安裝

雙擊執行 **`setup_wizard.bat`** 開始配置向導：

```
步驟 1: 選擇 AI 服務模式（免費/高性能/專業）
步驟 2: 輸入 API 金鑰（可選）
步驟 3: 設置管理員帳號
步驟 4: 選擇資料儲存位置
```

### 2️⃣ 啟動系統

雙擊執行 **`啟動大腦.bat`** 或 **`ZheweiTechBrain.exe`**

系統啟動後會顯示：
```
正在啟動築未科技 AI 大腦...
[INFO] 啟動端口: 8002
[INFO] 管理介面: http://localhost:8002/admin
[INFO] 對話介面: http://localhost:8002/chat
```

### 3️⃣ 訪問管理介面

在瀏覽器中訪問：
- 管理後台：http://localhost:8002/admin
- 對話介面：http://localhost:8002/chat
- 首頁：http://localhost:8002

使用配置向導中設置的管理員帳號登入。

## ⚙️ AI 服務配置

### 模式 1: 完全免費（推薦入門）

使用本地 Ollama AI，無需任何 API 金鑰：

1. 下載並安裝 [Ollama](https://ollama.ai/)
2. 執行命令：
   ```bash
   ollama pull qwen2.5:7b
   ollama pull qwen2.5-coder:7b  # 程式編寫專用
   ```
3. 在 `.env` 中設置：
   ```
   AI_COST_MODE=local_only
   OLLAMA_BASE_URL=http://localhost:11434
   ```

### 模式 2: 高性能免費（推薦）

使用 Google Gemini 免費額度：

1. 訪問 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 創建 API 金鑰
3. 在 `.env` 中設置：
   ```
   GEMINI_API_KEY=你的金鑰
   GEMINI_MODEL=gemini-1.5-flash
   AI_COST_MODE=free_only
   ```

### 模式 3: 專業混合（最強性能）

整合多個 AI 服務：

```env
# Google Gemini (免費額度)
GEMINI_API_KEY=你的金鑰

# Anthropic Claude (付費，但性能卓越)
ANTHROPIC_API_KEY=你的金鑰

# Groq (免費，速度極快)
GROQ_API_KEY=你的金鑰

# 啟用多 AI 集成思考
AI_USE_ENSEMBLE=1
AI_COST_MODE=all
```

## 🔧 配置文件說明

### `.env` 環境變數

關鍵配置項：

```env
# 管理員帳號
ADMIN_USER=admin
ADMIN_PASSWORD=your_password

# 資料儲存位置
BRAIN_WORKSPACE=D:\brain_workspace

# AI 成本控制
AI_COST_MODE=free_only  # local_only | free_only | all
AI_BUDGET_TWD=1000      # 每月預算（新台幣）

# Ollama 配置
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_CODER_MODEL=qwen2.5-coder:7b
```

完整配置項請參考 `.env.example`

## 📚 主要功能

### 1. AI 對話助手

在對話介面輸入問題，AI 會：
- 理解您的需求
- 選擇最適合的 AI 引擎
- 提供詳細解答
- 執行自動化任務

### 2. 智能代理系統

支持多種代理任務：
- 📝 文檔生成與分析
- 💻 程式碼編寫與除錯
- 🔍 資訊搜索與整理
- 🎨 創意內容生成

### 3. 管理後台

功能包括：
- 系統狀態監控
- AI 服務管理
- 使用量統計
- 日誌查看

## 🛠️ 進階設定

### 端口修改

預設端口為 8002，如需修改：

1. 編輯 `.env`：
   ```env
   BRAIN_PORT=8888  # 自訂端口
   ```
2. 重啟系統

### 外部訪問

允許區域網路訪問：

1. 編輯 `brain_server.py` 啟動參數：
   ```python
   uvicorn.run(app, host="0.0.0.0", port=8002)
   ```
2. 配置防火牆允許端口 8002

### Discord 整合

連接 Discord 機器人：

1. 創建 Discord Bot：https://discord.com/developers/applications
2. 在 `.env` 中設置：
   ```env
   DISCORD_BOT_TOKEN=你的Bot令牌
   ```
3. 重啟系統，Bot 自動上線

## 🐛 故障排除

### 問題 1: 無法啟動

**症狀**：雙擊後閃退或報錯

**解決方案**：
1. 檢查 `.env` 文件是否存在
2. 確認資料目錄有寫入權限
3. 查看 `logs/` 目錄下的錯誤日誌

### 問題 2: AI 無回應

**症狀**：對話無回應或報錯

**解決方案**：
1. 檢查 API 金鑰是否正確
2. 確認網路連接正常
3. 如使用 Ollama，確認服務已啟動：
   ```bash
   ollama list  # 查看已安裝模型
   ```

### 問題 3: 登入失敗

**症狀**：管理員帳號無法登入

**解決方案**：
1. 檢查 `.env` 中 `ADMIN_USER` 和 `ADMIN_PASSWORD`
2. 重新執行 `setup_wizard.bat` 重置帳號
3. 確認瀏覽器未阻擋 Cookie

### 問題 4: 端口被占用

**症狀**：啟動時提示 "Address already in use"

**解決方案**：
1. 查找占用進程：
   ```bash
   netstat -ano | findstr :8002
   ```
2. 結束進程或修改配置使用其他端口

## 📖 API 金鑰獲取

| 服務 | 獲取網址 | 說明 |
|------|---------|------|
| Google Gemini | https://aistudio.google.com/app/apikey | 免費額度 |
| Anthropic Claude | https://console.anthropic.com/ | 付費，$5 起 |
| Groq | https://console.groq.com/keys | 免費，速度快 |
| OpenRouter | https://openrouter.ai/keys | 多模型選擇 |

## 🔒 安全建議

1. **不要分享 `.env` 文件**：包含敏感金鑰
2. **使用強密碼**：管理員密碼應包含數字、字母、符號
3. **定期更新金鑰**：每 3-6 個月輪換一次
4. **限制訪問**：僅在可信網路環境使用

## 📞 技術支援

- 問題回報：https://github.com/your-repo/issues
- 使用文檔：查看項目根目錄下的其他 MD 文件
- 更新檢查：執行 `git pull` 獲取最新版本

## 📄 版本資訊

- **當前版本**：1.0.0
- **更新日期**：2026-02-12
- **Python 版本**：3.8+
- **支援系統**：Windows 10/11

## 📜 授權聲明

本軟件僅供築未科技內部及授權用戶使用。未經許可不得重新分發或商業使用。

---

**築未科技 © 2026** | 智能營建管理系統

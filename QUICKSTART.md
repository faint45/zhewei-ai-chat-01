# 🚀 築未科技 AI 大腦 - 快速開始

## 三步驟立即啟動

### 📥 方式一：打包版本（推薦給最終用戶）

#### Step 1: 下載並解壓縮
```
下載 ZheweiTechBrain_v1.0.zip
解壓縮到任意位置（例如：D:\ZheweiTech\）
```

#### Step 2: 運行配置向導
```
雙擊 setup_wizard.bat
按照提示完成配置（約 2 分鐘）
```

#### Step 3: 啟動系統
```
雙擊 啟動大腦.bat
瀏覽器訪問 http://localhost:8002
```

完成！🎉

---

### 💻 方式二：開發版本（推薦給開發者）

#### Step 1: 克隆項目
```bash
git clone https://github.com/your-repo/zhe-wei-tech.git
cd zhe-wei-tech
```

#### Step 2: 安裝依賴
```bash
pip install -r requirements-brain.txt
```

#### Step 3: 配置環境
```bash
# 複製配置範例
copy .env.example .env

# 編輯 .env，至少設置：
# ADMIN_USER=admin
# ADMIN_PASSWORD=your_password
```

#### Step 4: 啟動服務
```bash
python brain_server.py
```

訪問 http://localhost:8002

---

## 🎯 選擇 AI 服務

### ⚡ 免費方案 A：Ollama（完全本地）

**優點**：零費用、隱私保護、無需網路
**缺點**：需要較好的電腦配置

```bash
# 1. 安裝 Ollama
# 訪問 https://ollama.ai/ 下載安裝

# 2. 下載模型
ollama pull qwen2.5:7b
ollama pull qwen2.5-coder:7b

# 3. 配置 .env
AI_COST_MODE=local_only
OLLAMA_BASE_URL=http://localhost:11434
```

### 🚀 免費方案 B：Google Gemini（推薦）

**優點**：高性能、免費額度大、無需本地資源
**缺點**：需要 API 金鑰、需要網路

```bash
# 1. 獲取 API Key
訪問 https://aistudio.google.com/app/apikey

# 2. 配置 .env
GEMINI_API_KEY=你的金鑰
GEMINI_MODEL=gemini-1.5-flash
AI_COST_MODE=free_only
```

### 🔥 專業方案：多 AI 混合

**優點**：最強性能、多重備援、智能選擇
**缺點**：需要多個 API 金鑰

```bash
# 配置 .env
GEMINI_API_KEY=你的Gemini金鑰
ANTHROPIC_API_KEY=你的Claude金鑰
GROQ_API_KEY=你的Groq金鑰

AI_USE_ENSEMBLE=1  # 啟用集成思考
AI_COST_MODE=all
AI_BUDGET_TWD=1000  # 每月預算
```

---

## 🎮 快速體驗

### 第一次對話

啟動系統後，訪問對話介面：http://localhost:8002/chat

試試這些問題：

```
👋 你好，請自我介紹

💡 幫我寫一個 Python 快速排序函數

📊 分析一下這段代碼的時間複雜度

🔍 搜尋關於機器學習的最新資訊

✍️ 幫我寫一封專業的商務郵件
```

### 管理後台

訪問管理介面：http://localhost:8002/admin

功能：
- 📊 系統狀態監控
- 🤖 AI 服務管理
- 📈 使用量統計
- 📝 日誌查看

---

## ⚙️ 進階配置

### 修改端口

編輯啟動命令或配置文件：
```python
# brain_server.py 最後一行
uvicorn.run(app, host="0.0.0.0", port=8888)  # 改為 8888
```

### 允許外部訪問

1. 修改啟動主機：
```python
uvicorn.run(app, host="0.0.0.0", port=8002)  # 0.0.0.0 允許外部
```

2. 配置防火牆：
```bash
# Windows 防火牆
netsh advfirewall firewall add rule name="ZheweiTechBrain" dir=in action=allow protocol=TCP localport=8002
```

### Discord 機器人整合

```bash
# 1. 創建 Discord Bot
訪問 https://discord.com/developers/applications

# 2. 配置 .env
DISCORD_BOT_TOKEN=你的Bot令牌

# 3. 重啟系統
```

---

## 🐛 快速故障排除

### ❌ 無法啟動

```bash
# 檢查 Python 版本
python --version  # 需要 3.8+

# 檢查依賴
pip install -r requirements-brain.txt

# 查看錯誤日誌
cat logs/error.log  # 或在 Windows: type logs\error.log
```

### ❌ AI 無回應

```bash
# 測試 Ollama 連接
curl http://localhost:11434/api/tags

# 測試 Gemini API
# 在 .env 中確認 GEMINI_API_KEY 正確

# 檢查網路
ping 8.8.8.8
```

### ❌ 無法登入

```bash
# 重置管理員密碼
# 重新運行 setup_wizard.bat

# 或手動編輯 .env
ADMIN_USER=admin
ADMIN_PASSWORD=newpassword
```

---

## 📚 更多資源

- 📖 [完整使用說明](README_軟件使用說明.md)
- 🔧 [打包部署指南](PACKAGING_GUIDE.md)
- 💬 問題回報：GitHub Issues
- 📧 技術支援：support@築未科技.com

---

## ✅ 檢查清單

打包分發前確認：

- [ ] 所有依賴已安裝
- [ ] .env.example 已創建（不包含真實金鑰）
- [ ] 靜態文件已包含
- [ ] 啟動腳本可執行
- [ ] 配置向導運行正常
- [ ] 在乾淨環境測試通過
- [ ] 使用說明文檔完整
- [ ] 版本號已更新

打包命令：
```bash
build_installer.bat
```

---

**🎉 歡迎使用築未科技 AI 大腦系統！**

有任何問題歡迎聯繫我們。

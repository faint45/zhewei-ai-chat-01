# 築未科技七階段指揮作戰系統

## 📋 系統概述

七階段指揮作戰系統是一個完全自動化的 AI 開發平台，從模糊需求到最終交付，全程無需人工干預。

## 🎯 七階段流程

```
[1] 需求提出 (手機/遠端)
    ↓
[2] 接收與翻譯 (意圖解構)
    ↓
[3] 指揮官決定與分配 (核心調度)
    ↓
[4] 處理人員工作 (實體執行)
    ↓
[5] 處理完回報 (內部呈報)
    ↓
[6] 指揮官確認成果 (二次驗證)
    ↓
[7] 終極回報 (成功導向)
```

## 👥 職位角色分配

| 角色 | 職責 | 軟體 | 說明 |
|------|------|------|------|
| **總指揮官** | 決策中樞 | Gemini Pro | 處理長文本規範，分配任務，最終驗證 |
| **首席開發官** | 代碼架構師 | Claude Pro | 編寫核心邏輯，解決難題 |
| **實體執行員** | 實體落地 | Cursor Pro / Windsurf | 在 D:\brain_workspace 開發 |
| **地端勤務兵** | 隱私與初審 | Ollama (Qwen) | 本地檢索、代碼檢測 |
| **情報與驗證** | 異構驗證 | 千問/元寶/CodeBuddy | 第二意見，確保成果無誤 |
| **基礎設施** | 環境封裝 | Docker | 獨立容器運行 |

## 🚀 快速開始

### 1. 配置環境變量

複製 `.env.seven_stage` 到 `.env` 並填入 API 密鑰：

```bash
cp .env.seven_stage .env
# 編輯 .env 填入：
# - GEMINI_API_KEY
# - ANTHROPIC_API_KEY
# - 其他必要的 API 密鑰
```

### 2. 啟動系統

```bash
# 使用啟動腳本
啟動_七階段系統.bat

# 或直接運行
python seven_stage_system.py
```

### 3. 測試系統

輸入測試命令：

```bash
# 測試網頁開發
"幫我弄個網頁，要有企業形象和聯絡表單"

# 測試 AI 視覺
"分析這張圖片中的交通流量"

# 測試代碼開發
"寫一個 Python 腳本來處理 Excel 文件"
```

## 📁 目錄結構

```
D:\brain_workspace\
├── vision/          # 視覺任務輸出
├── development/     # 開發任務輸出
├── retrieval/       # 檢索任務輸出
├── reports/         # 系統報告
└── logs/           # 系統日誌
```

## 🔧 API 集成

### Gemini Pro (總指揮官)

```python
import google.generativeai as genai

genai.configure(api_key="YOUR_API_KEY")
model = genai.GenerativeModel('gemini-1.5-pro')
```

### Claude Pro (首席開發官)

```python
import anthropic

client = anthropic.Anthropic(api_key="YOUR_API_KEY")
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=2000,
    messages=[{"role": "user", "content": "你的提示詞"}]
)
```

### Ollama (地端勤務兵)

```bash
# 啟動 Ollama 服務
ollama serve

# 使用 Qwen 模型
curl http://localhost:11461/api/generate -d '{
  "model": "qwen2.5:latest",
  "prompt": "你的提示詞"
}'
```

## 📊 工作流程示例

### 示例 1：網頁開發

**輸入：** "幫我弄個網頁，要有企業形象和聯絡表單"

**流程：**

1. **[階段 1]** iPhone 15 Pro 通過 https://brain.zhe-wei.net 發送需求
2. **[階段 2]** Gemini Pro 解析為：
   ```json
   {
     "intent": "create_website",
     "subtasks": [
       {"description": "設計網頁結構", "role": "lead_dev"},
       {"description": "編寫 HTML/CSS", "role": "executor"},
       {"description": "本地代碼檢測", "role": "local_guard"}
     ]
   }
   ```
3. **[階段 3]** 分配任務給各專家
4. **[階段 4]** Claude Pro 設計 → Windsurf 編寫 → Ollama 檢測
5. **[階段 5]** 回報進度給指揮官
6. **[階段 6]** 千問/元寶進行異構驗證
7. **[階段 7]** iPhone 收到：
   ```
   [成功] 任務完成！

   [結果] 位置：D:\brain_workspace\development\website.html
   [時間] 執行：30分鐘
   [質量] 評分：0.95

   您可以立即使用！
   ```

## ⚙️ 配置選項

### .env 配置

```env
# 工作區
WORKSPACE=D:/brain_workspace

# 超時設定
TASK_TIMEOUT=3600  # 1小時

# 驗證閾值
VERIFICATION_THRESHOLD=0.9

# 重試次數
MAX_RETRIES=3
```

### 角色切換

```python
# 只使用本地 Ollama（無 API 費用）
system = SevenStageSystem(local_mode=True)

# 使用所有雲端 API（最高質量）
system = SevenStageSystem(local_mode=False)
```

## 🔒 安全特性

- **隱私保護**：敏感任務在本地 Ollama 處理
- **代碼掃描**：自動檢測安全漏洞
- **異構驗證**：多個 AI 交叉驗證
- **權限控制**：只報喜，不暴露內部錯誤

## 🐛 故障排除

### 問題：API 密鑰無效

**解決：**
```bash
# 檢查環境變量
echo $ANTHROPIC_API_KEY

# 更新 .env 文件
```

### 問題：Ollama 連接失敗

**解決：**
```bash
# 檢查 Ollama 服務
curl http://localhost:11461/api/version

# 重啟 Ollama
taskkill /F /IM ollama.exe
ollama serve
```

### 問題：Docker 容器啟動失敗

**解決：**
```bash
# 檢查 Docker 服務
docker ps

# 查看容器日誌
docker logs container_id
```

## 📈 性能優化

- **並行執行**：多個任務同時處理
- **緩存機制**：重複任務使用緩存結果
- **增量更新**：只修改必要部分

## 🎓 最佳實踐

1. **明確需求**：儘量提供詳細的需求描述
2. **測試頻繁**：在每個階段後進行測試
3. **備份代碼**：定期備份 D:\brain_workspace
4. **監控日誌**：檢查 logs/ 目錄了解運行狀態

## 📞 支持與文檔

- **API 文檔**：`api_documentation.md`
- **部署指南**：`CLOUDBASE_DEPLOYMENT_GUIDE.md`
- **項目路線**：`PROJECT_ROADMAP.md`

---

**築未科技七階段指揮作戰系統** - 您的 AI 自動化平台 🚀

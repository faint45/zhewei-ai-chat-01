# 築未科技 Construction Brain — 方案總覽
> 建立日期：2026-02-24｜換主力電腦後從這裡開始

---

## 📁 本目錄文件說明

| 文件 | 說明 |
|------|------|
| `README.md` | 本文件，換電腦後的啟動指引 |
| `SPEC.md` | 完整產品規格書（架構/模組/授權/SKU/安全邊界） |
| `ROADMAP.md` | 4週開發路線圖（每週任務清單+驗收標準） |
| `SCHEMA.md` | 資料欄位定版（CSV欄位/JSON格式/SQLite建表） |
| `Modelfile_新增段落.md` | 貼入 Modelfile 的施工日誌抽取規則 |

---

## 🚀 換主力電腦後第一件事（照順序做）

### Step 1：修掉 ai_service.py 的 Merge Conflict
```powershell
# 搜尋有問題的行
Select-String -Path "ai_service.py" -Pattern "^<<<<<<<|^=======|^>>>>>>>"
```
找到後手動保留正確段落，刪掉衝突標記。

### Step 2：安裝環境
```powershell
# 安裝 Ollama
winget install Ollama.Ollama

# 安裝 Python 依賴（等 requirements.txt 建好後用）
pip install fastapi uvicorn faster-whisper python-dotenv httpx

# 安裝 cloudflared
winget install Cloudflare.cloudflared
```

### Step 3：Pull Repo
```powershell
git clone https://github.com/faint45/zhewei-ai-chat-01
cd zhewei-ai-chat-01
```

### Step 4：更新 Modelfile
把 `Modelfile_新增段落.md` 的 SYSTEM 內容貼進 `Modelfile`，然後：
```powershell
ollama create zhewei-brain -f Modelfile
```

### Step 5：建立測試專案目錄
```powershell
mkdir C:\ZheweiConstruction\projects\test_project_001\01_Input\Photos\LINE
mkdir C:\ZheweiConstruction\projects\test_project_001\01_Input\Voice\LINE
mkdir C:\ZheweiConstruction\projects\test_project_001\02_Output\Reports
mkdir C:\ZheweiConstruction\projects\test_project_001\03_KB
mkdir C:\ZheweiConstruction\db
mkdir C:\ZheweiConstruction\logs
mkdir C:\ZheweiConstruction\config
```

### Step 6：開始 Week 1
> 先寫 `extract_work_events.py`，讓語音/文字 → JSON 跑通

---

## 🎯 產品定位（一句話版）

**「像 CAD/Word 一樣，安裝在客戶電腦，自動從 LINE 抓語音/照片，填寫公共工程施工日誌」**

---

## 🏗️ 系統架構（一頁版）

```
LINE 群組
  │
  ▼（Webhook via Cloudflare Tunnel）
line_receiver.py（FastAPI）
  │
  ├─ 語音 → Whisper → transcript.txt
  │                        │
  ├─ 文字 ─────────────────┤
  │                        ▼
  │               extract_work_events.py
  │                （Ollama + zhewei-brain）
  │                        │
  │                        ▼
  │                 work_events.json
  │                        │
  │          ┌─────────────┼──────────────┐
  │          ▼             ▼              ▼
  │   DailyReport.md  Progress.csv  SafetyIssues.csv
  │
  └─ 照片 → ingest.py（分類/hash/索引）
                │
                ├─ 01_Input/Photos/施工進度/...
                ├─ 01_Input/Photos/工安缺失/...
                └─ SQLite index.db
```

---

## 💰 商業模式

| 方案 | 月費 | 功能 |
|------|------|------|
| A 入門版 | NT$ 499 | 日報或工安模組擇一 |
| B 專業版 | NT$ 1,499 | 日報+工安+LINE接入+多專案 |
| C 企業版 | NT$ 3,999 | B全部+高階回連200點/月 |

- 授權：Node-locked 離線 license.json，年度維護費
- 高階回連：你的 5070Ti+4060Ti 桌機，超量加購點數

---

## 📋 今日規劃摘要（2026-02-24）

### 已完成規格定版
- [x] 產品定位（主業：營建自動化，被動：訂閱授權）
- [x] 系統架構（客戶端本地推理 + 你主機高階回連）
- [x] 核心模組清單（4個程式檔）
- [x] 輸出欄位（Progress.csv / SafetyIssues.csv / DailyReport.md）
- [x] Modelfile 施工日誌抽取 Prompt 規則
- [x] 公共工程施工日誌欄位對應表
- [x] 照片自動分類規則（3層標籤+命名規範）
- [x] LINE Receiver 架構（Messaging API + Cloudflare Tunnel）
- [x] 授權模式（Node-locked + 年度維護費）
- [x] 訂閱 SKU 3個方案（含定價）
- [x] 4週開發路線圖

### 待主力電腦回來再做
- [ ] 清 merge conflict（`ai_service.py`）
- [ ] `extract_work_events.py`（Week 1 核心）
- [ ] `ingest.py`（語音+照片入庫）
- [ ] `daily_report_writer.py`（日報引擎）
- [ ] `line_receiver.py`（LINE Webhook）
- [ ] 一鍵安裝包 `setup.ps1`
- [ ] 授權驗證模組
- [ ] Web UI（最小版）

# 築未科技 Construction Brain — 4 週開發路線圖
> 版本：v0.1｜日期：2026-02-24

---

## 前置條件（換主力電腦後第一天做）

- [ ] 清掉 `ai_service.py` 的 merge conflict（搜尋 `<<<<<<<` / `=======` / `>>>>>>>`）
- [ ] 安裝環境：Python 3.11+、Ollama、faster-whisper、FastAPI、uvicorn、cloudflared
- [ ] Pull repo：`git clone https://github.com/faint45/zhewei-ai-chat-01`
- [ ] 更新 Modelfile：把 `Modelfile_新增段落.md` 的內容貼入，執行 `ollama create zhewei-brain -f Modelfile`
- [ ] 建立測試專案目錄：`C:\ZheweiConstruction\projects\test_project_001\`

---

## 第 1 週：Core + 抽取引擎（最重要，其他都靠它）

### 目標
語音/文字輸入 → 結構化 JSON → 基本 `DailyReport.md`

### 任務清單
- [ ] **`extract_work_events.py`**
  - 接收 `transcript.txt` 或文字字串
  - 呼叫本地 Ollama（zhewei-brain）
  - 解析回傳 JSON → 存為 `work_events.json`
  - 錯誤處理：JSON 解析失敗時重試一次，還是失敗就存 raw 並標記人工檢核
- [ ] **`ingest.py`（語音部分）**
  - 監控 `01_Input/Voice/LINE/YYYY-MM-DD/` 目錄
  - 新檔案觸發：faster-whisper 轉寫 → `transcript.txt`
  - 寫入 SQLite 索引（message_id, date, source, path, hash, status）
  - 轉寫完成後自動呼叫 `extract_work_events.py`
- [ ] **`daily_report_writer.py`（最小版）**
  - 讀取 `work_events.json`
  - 輸出 `DailyReport.md`（對應公共工程施工日誌格式）
  - 同一天重跑只更新不重複追加（用 date + project_id 做 key）
- [ ] **資料夾初始化腳本** `init_project.py`
  - 輸入 project_id、工程名稱、開工日期
  - 自動建立標準資料夾結構 + `project.json`

### 驗收標準
> 手動丟一段語音（或貼一段文字）→ 系統自動輸出正確格式的 `DailyReport.md`
> 相同輸入重跑兩次，日報內容不會重複

---

## 第 2 週：進度模組 + 照片分類入庫

### 目標
日報完整輸出（含 `Progress.csv`）+ 照片自動進庫分類

### 任務清單
- [ ] **`daily_report_writer.py`（進度部分）**
  - 從 `work_items[]` 彙總輸出 `Progress.csv`
  - 欄位：`project_id, date, section, trade, work_item, progress_percent, status, notes, source`
  - 同一天/同一工項重跑時更新（不重複新增列）
- [ ] **`ingest.py`（照片部分）**
  - 監控 `01_Input/Photos/LINE/YYYY-MM-DD/` 目錄
  - 新照片觸發：
    - 抽取 EXIF（時間/GPS）
    - 計算 hash（去重）
    - 呼叫本地視覺模型分類（第1層+第2層標籤）
    - 從對應訊息索引抓第3層（位置）
    - 依規則重命名並移入分類資料夾
    - 寫入 SQLite 索引
- [ ] **SQLite 索引庫建表**
  - `messages`（訊息流水）
  - `photos`（照片索引：path, hash, type, sub_type, location, date, project_id）
  - `work_events`（結構化工項）
  - `daily_reports`（日報生成紀錄）

### 驗收標準
> 丟 3 張照片 → 自動分類到正確子資料夾，SQLite 有對應紀錄
> 日報 + 進度 CSV 欄位正確，重跑不重複

---

## 第 3 週：工安模組 + LINE Receiver 雛形

### 目標
工安缺失自動產出 + LINE Webhook 可接收訊息

### 任務清單
- [ ] **`safety_engine.py`**
  - 從 `work_events.json` 的 `safety_issues[]` 抽取
  - 從照片辨識結果的 `safety_issues[]` 抽取
  - 合併輸出 `SafetyIssues.csv`
  - 欄位：`issue_id, project_id, date, location, issue_type, severity, suggestion, owner, due_date, status, photo_path, photo_hash`
  - 自動產出 `RectifyPlan.md`（今日新增缺失摘要 + 逐項整改）
- [ ] **`line_receiver.py`（雛形）**
  - FastAPI + LINE Messaging API Webhook
  - 接收：文字/語音/圖片
  - 文字 → 寫入 `raw_messages.jsonl` → 觸發 `extract_work_events.py`
  - 語音 → 下載到 `01_Input/Voice/` → 觸發 `ingest.py`
  - 圖片 → 下載到 `01_Input/Photos/LINE/` → 觸發 `ingest.py`
- [ ] **Cloudflare Tunnel 設定文件**（補充到 DEPLOY.md）
  - 安裝 cloudflared
  - 建立 Tunnel → 對應 localhost:8003
  - 設定 LINE Webhook URL

### 驗收標準
> LINE 傳照片 → 系統自動下載分類 → 工安缺失寫入 CSV
> LINE 傳語音 → 自動轉寫抽取 → 日報更新

---

## 第 4 週：一鍵安裝包 + 授權啟用 + Web UI

### 目標
客戶可用的完整交付版本

### 任務清單
- [ ] **一鍵安裝腳本 `setup.ps1`**
  - 檢查 Python / Ollama / NVIDIA Driver
  - 安裝 Python 依賴（`requirements.txt`）
  - 下載並建立 zhewei-brain 模型
  - 安裝 Windows Service（NSSM）
  - 建立桌面捷徑
  - 引導輸入 License Key → 驗證 → 寫入 `config/license.json`
- [ ] **授權驗證模組 `license_validator.py`**
  - 讀取 `license.json`
  - 驗證 machine_id（WMI 硬體 hash）
  - 驗證到期日
  - 依 `modules[]` 開放對應功能
- [ ] **Web UI（最小版）**
  - 選擇專案
  - 上傳/拖曳照片/語音
  - 查看今日日報
  - 下載輸出（DailyReport.md / CSV）
  - 工安缺失列表（可篩選/搜尋）
- [ ] **`requirements.txt`**（鎖版本）
- [ ] **`README_客戶安裝版.md`**（給客戶的安裝說明）

### 驗收標準
> 全新 Windows 電腦執行 `setup.ps1` → 服務啟動 → Web UI 可用 → 能產出完整報表
> 沒有網路也能跑核心功能（離線模式）

---

## 被動收入產出（每週同步做）

| 週次 | 產出的可販售資產 |
|------|----------------|
| 第1週 | 工地日誌 Prompt 包（Modelfile + 抽取規則）|
| 第2週 | 施工日誌 CSV 欄位規範 + 照片命名 SOP |
| 第3週 | 工安缺失字典（50類） + RectifyPlan 模板 |
| 第4週 | 一鍵安裝包 + 授權授權條款草案 |

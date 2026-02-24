# 築未科技 工地大腦（Construction Brain）產品規格書
> 版本：v0.1｜日期：2026-02-24｜作者：築未科技

---

## 一、產品定位

- **主業**：營建自動化（施工日誌/工安巡檢/影像辨識/報表）
- **目標客群**：施工單位、工地主任、監造、中小型營造公司
- **交付模式**：一鍵安裝包（Windows 私有部署），不依賴客戶端外網
- **被動收入**：主業產出的可複製交付物（模板/授權/訂閱更新）
- **商業模式**：訂閱制為主（基本功能包月；高階回連用點數/按次補充）

---

## 二、系統架構

```
客戶端（私有部署，客戶電腦跑）
├── LINE Receiver (FastAPI Webhook) ←── Cloudflare Tunnel（不開port）
├── Whisper（語音轉寫，CPU可跑，GPU加速）
├── Ollama + zhewei-brain Modelfile（本地推理主力）
├── Agent Tools（安全白名單工具層）
├── SQLite 索引庫（自動抓取/快速查找/去重）
├── 報表引擎
│   ├── DailyReport.md（公共工程施工日誌格式）
│   ├── Progress.csv（進度表）
│   ├── SafetyIssues.csv（工安缺失追蹤）
│   └── RectifyPlan.md（整改計畫書）
└── Web UI (localhost) ＋ Desktop Tray（捷徑殼）

築未科技主機（5070Ti+4060Ti+64GB，你家桌機）← 高階回連
├── 重型視覺辨識（精準工安/跨圖整合）
├── 跨文件長上下文分析
└── 訂閱額度管理（API Key + 配額 + 日誌）
```

---

## 三、核心模組清單

| 模組 | 程式檔 | 功能 | 輸出 |
|------|--------|------|------|
| LINE Receiver | `line_receiver.py` | 接 Webhook，下載文字/語音/照片 | `raw_messages.jsonl` |
| 語音轉寫 | `ingest.py` | Whisper 轉寫語音 | `transcript.txt` |
| 自動入庫 | `ingest.py` | 照片命名/分類/hash/寫 SQLite | 分類資料夾 + 索引庫 |
| 工項抽取 | `extract_work_events.py` | Ollama + Prompt → 結構化 JSON | `work_events.json` |
| 日報引擎 | `daily_report_writer.py` | JSON → DailyReport.md | `DailyReport.md` |
| 進度引擎 | `daily_report_writer.py` | JSON → Progress.csv | `Progress.csv` |
| 工安引擎 | `safety_engine.py` | 照片辨識+文字 → 缺失 | `SafetyIssues.csv` / `RectifyPlan.md` |
| 照片分類 | `ingest.py` | AI分類 → 資料夾+索引 | 分類資料夾結構 |

---

## 四、標準資料夾結構（每台客戶電腦）

```
C:\ZheweiConstruction\
├── projects\
│   └── <project_id>\
│       ├── 01_Input\
│       │   ├── Photos\
│       │   │   └── LINE\YYYY-MM-DD\
│       │   │       ├── 施工進度\
│       │   │       ├── 工安缺失\
│       │   │       ├── 材料入場\
│       │   │       ├── 機具運作\
│       │   │       └── 其他\
│       │   └── Voice\
│       │       └── LINE\YYYY-MM-DD\
│       ├── 02_Output\
│       │   ├── Reports\YYYY-MM-DD\
│       │   │   ├── DailyReport.md
│       │   │   ├── Progress.csv
│       │   │   ├── SafetyIssues.csv
│       │   │   └── RectifyPlan.md
│       │   └── Transcripts\
│       └── 03_KB\          ← 從 Google Drive 同步來的智庫
├── db\
│   └── index.db            ← SQLite 索引庫
├── logs\
└── config\
    ├── project.json        ← 專案設定（名稱/開工日/里程/工項字典）
    └── license.json        ← 授權檔（離線驗證）
```

---

## 五、照片自動分類規則

### 3 層標籤
```
第 1 層（必定分）→ 照片類型
  施工進度 / 工安缺失 / 材料入場 / 機具運作 / 竣工查驗 / 環境天候 / 其他

第 2 層（本地模型分）→ 具體內容
  施工進度 → 鋼筋/模板/混凝土/開挖/回填/鋪面/管線
  工安缺失 → 未戴安全帽/開口未防護/電線亂拉/高處未繫
  材料入場 → 鋼筋/預拌混凝土/砂石/水泥

第 3 層（從訊息推斷）→ 位置/工區
  K12+300 / A工區 / 2F / 主橋段
```

### 命名規則
```
YYYYMMDD_HHMMSS_<類型>_<位置>_<子類型>.jpg
例：20260224_143022_施工進度_K12+300_鋼筋.jpg
    20260224_151200_工安缺失_K12+380_未戴安全帽.jpg
```

---

## 六、授權模式（類 CAD/Word）

| 授權類型 | 說明 | 驗證方式 |
|---------|------|---------|
| Node-locked（單機） | 綁定 1 台電腦 | 離線 license.json |
| 公司版（N台） | 允許公司內 N 台 | 人工發 N 份 license |
| 年度維護費 | 付費才能取得更新/新模組 | 到期後功能鎖定，資料不刪 |

### License 檔結構（JSON）
```json
{
  "licensee": "公司名稱",
  "plan": "professional",
  "modules": ["daily_report", "safety"],
  "seats": 1,
  "machine_id": "xxxxx",
  "issued_at": "2026-02-24",
  "expires_at": "2027-02-24",
  "remote_boost_credits": 200
}
```

---

## 七、訂閱 SKU

| 方案 | 功能 | 月費（建議） |
|------|------|-------------|
| A 入門版 | 日報或工安模組擇一，本機推理，1 專案 | NT$ 499 |
| B 專業版 | 日報+工安全開，多專案，模板更新，LINE接入 | NT$ 1,499 |
| C 企業版 | B全部 + 高階回連 200點/月 + 優先更新 | NT$ 3,999 |

- 超量加購：每 100 點 NT$ 299
- 公司授權（多席）：另報價（基本 × 席位數 × 0.7）

---

## 八、安全邊界（對外提供必做）

### 客戶可用工具（白名單）
- 上傳/整理資料到專案白名單資料夾
- 觸發報表產出
- 查詢/下載報表
- 檢視索引庫（只讀）

### 禁止對外開放
- `run_command`（任意系統指令）
- 任意路徑 `write_file`
- `deploy_service`
- 任何影響系統的操作

### 管理員入口（僅你/管理員）
- 透過 Cloudflare Access 限制帳號才能進
- 服務版本更新、自癒重啟、配置修改

---

## 九、混合算力策略

| 任務類型 | 執行位置 | 觸發條件 |
|---------|---------|---------|
| 一般對話/報表/摘要 | 客戶本機 Ollama | 預設 |
| 照片基本分類 | 客戶本機（輕量模型） | 有照片進入 |
| 重型視覺/精準缺失辨識 | 你的主機（回連） | 用戶手動選「高階」或訂閱額度內 |
| 跨文件長上下文 | 你的主機（回連） | 任務超過本機上下文限制 |

### 回連規則
- 只傳「摘要/標籤/座標」，不傳整包工地資料
- 每個客戶 tenant 隔離（project_id + license_key）
- 速率限制：企業版 200點/月，超量加購

---

## 十、等主力電腦回來的啟動清單

1. **清掉 `ai_service.py` 的 merge conflict**（搜尋 `<<<<<<<`/`=======`/`>>>>>>>` 並手動解決）
2. **安裝環境**：Python 3.11+、Ollama、Whisper、FastAPI、cloudflared
3. **Pull repo**：`git clone https://github.com/faint45/zhewei-ai-chat-01`
4. **更新 Modelfile**：加入 `construction-brain/Modelfile_新增段落.md` 的內容
5. **新建專案目錄**：`C:\ZheweiConstruction\projects\<test_project>\`
6. **開始 Week 1**：先跑通 `extract_work_events.py`（語音/文字 → JSON）

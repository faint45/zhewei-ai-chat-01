# 築未科技 Construction Brain — 資料欄位規格（定版）
> 版本：v0.1｜日期：2026-02-24

---

## 一、work_events.json（核心中間資料，不對外）

每次語音/文字被抽取後產生，作為所有報表的「唯一來源」。

```json
{
  "event_id": "uuid-v4",
  "project_id": "string",
  "date": "YYYY-MM-DD",
  "source": "line_voice | line_text | manual",
  "source_ref": "message_id 或 transcript 檔名",
  "created_at": "ISO8601",
  "weather_am": "晴|陰|雨|其他|null",
  "weather_pm": "晴|陰|雨|其他|null",
  "work_items": [
    {
      "item": "施工項目名稱",
      "location": "工區/里程/層別",
      "unit": "公尺|m³|噸|式|個|...",
      "qty_today": "數字或null",
      "progress_pct": "0-100 或null",
      "notes": "備註"
    }
  ],
  "materials": [
    {
      "name": "材料名稱",
      "unit": "單位",
      "qty_today": "數字或null",
      "supplier": "廠商名稱或null",
      "notes": ""
    }
  ],
  "labor": [
    {
      "trade": "工別",
      "count_today": "數字或null"
    }
  ],
  "equipment": [
    {
      "name": "機具名稱",
      "count_today": "數字或null"
    }
  ],
  "safety_issues": [
    {
      "description": "缺失描述",
      "location": "位置/里程",
      "severity": "low|medium|high"
    }
  ],
  "problems": ["string"],
  "plan_tomorrow": ["string"],
  "notices": ["string"],
  "important_notes": ["string"],
  "parse_status": "ok|partial|failed",
  "raw_input": "原始逐字稿或文字（debug用）"
}
```

---

## 二、Progress.csv（進度追蹤表，可用 Excel 開）

| 欄位名 | 類型 | 說明 | 範例 |
|--------|------|------|------|
| `project_id` | string | 專案代碼 | `PRJ-2026-001` |
| `date` | YYYY-MM-DD | 日期 | `2026-02-24` |
| `section` | string | 工區/里程/層別 | `K12+300~K12+450` |
| `trade` | string | 分包/工種 | `鋼筋工` |
| `work_item` | string | 工項名稱 | `路床整平` |
| `unit` | string | 單位 | `公尺` |
| `qty_today` | float | 本日完成數量 | `150` |
| `qty_cumulative` | float | 累計完成數量（系統計算） | `350` |
| `qty_contract` | float | 契約數量（專案設定） | `1200` |
| `progress_pct` | float | 進度% | `29.2` |
| `status` | string | planned/in_progress/done/blocked | `in_progress` |
| `notes` | string | 備註 | `下午雨停工2小時` |
| `source` | string | 資料來源 | `line_voice` |
| `event_id` | string | 對應 work_event ID（追溯用） | `uuid` |

---

## 三、SafetyIssues.csv（工安缺失追蹤表）

| 欄位名 | 類型 | 說明 | 範例 |
|--------|------|------|------|
| `issue_id` | string | 缺失唯一ID（自動流水） | `SAF-20260224-001` |
| `project_id` | string | 專案代碼 | `PRJ-2026-001` |
| `date` | YYYY-MM-DD | 發現日期 | `2026-02-24` |
| `location` | string | 位置/里程/工區 | `K12+380` |
| `issue_type` | string | 缺失類型（見字典） | `未戴安全帽` |
| `severity` | string | low/medium/high | `medium` |
| `description` | string | 詳細描述 | `A工班工人未戴安全帽` |
| `suggestion` | string | 改善建議 | `立即配戴，並告誡工班` |
| `owner` | string | 責任單位/人 | `A工班` |
| `due_date` | YYYY-MM-DD | 改善期限 | `2026-02-25` |
| `status` | string | open/fixed/verified/closed | `open` |
| `photo_path` | string | 照片相對路徑 | `01_Input/Photos/工安缺失/...jpg` |
| `photo_hash` | string | SHA256（去重追溯） | `abc123...` |
| `source` | string | line_photo/line_text/manual | `line_photo` |
| `verified_by` | string | 確認人 | `工地主任` |
| `verified_at` | YYYY-MM-DD | 確認日期 | `null` |
| `event_id` | string | 對應 work_event ID | `uuid` |

---

## 四、工安缺失類型字典（issue_type 標準值）

### 個人防護具
- 未戴安全帽
- 未穿反光背心
- 未繫安全帶（高處作業）
- 未穿安全鞋
- 未戴防塵口罩

### 開口/邊緣防護
- 開口未設護欄
- 邊緣未設安全網
- 坑洞未設警示
- 模板開口未防護

### 電氣/機電
- 電線亂拉/裸露
- 臨時用電無漏電斷路器
- 電箱未上鎖

### 機具/設備
- 機具未設安全裝置
- 吊掛作業無專人指揮
- 車輛倒車無指揮

### 環境/整潔
- 通道堆放雜物
- 材料未固定堆放
- 廢棄物未清除

### 施工程序
- 未辦理動火許可
- 未辦理侷限空間作業許可
- 未設施工圍籬

---

## 五、DailyReport.md 章節對應（公共工程施工日誌）

| 章節 | 資料來源 | 自動/人工 |
|------|---------|---------|
| 表頭（工程名稱/日期/天氣/工期計算） | project.json + work_events.json | **自動** |
| 一、施工概況（工項/數量/進度） | work_items[] | **自動** |
| 二、材料管理 | materials[] | **自動** |
| 三、人員機具 | labor[] + equipment[] | **自動** |
| 四、技術士（勾選） | 人工勾選（UI提供） | 半自動 |
| 五、工安衛生（施工前檢查/缺失） | safety_issues[] + 照片辨識 | **自動** |
| 六、取樣試驗 | 人工輸入 | 人工 |
| 七、通知廠商 | notices[] | **自動** |
| 八、重要事項 | important_notes[] + problems[] | **自動** |
| 簽章 | 留空（紙本簽） | 人工 |

---

## 六、SQLite 資料表結構（index.db）

```sql
-- 訊息流水
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  project_id TEXT,
  date TEXT,
  source TEXT,  -- line_voice|line_text|line_photo|manual
  sender TEXT,
  group_id TEXT,
  content TEXT,
  file_path TEXT,
  hash TEXT,
  status TEXT,  -- pending|processed|failed
  created_at TEXT
);

-- 照片索引
CREATE TABLE photos (
  id TEXT PRIMARY KEY,
  project_id TEXT,
  date TEXT,
  original_path TEXT,
  classified_path TEXT,
  photo_type TEXT,
  sub_type TEXT,
  location_hint TEXT,
  hash TEXT,
  exif_time TEXT,
  exif_gps TEXT,
  message_id TEXT,
  status TEXT,
  created_at TEXT
);

-- 工項事件
CREATE TABLE work_events (
  id TEXT PRIMARY KEY,
  project_id TEXT,
  date TEXT,
  source TEXT,
  source_ref TEXT,
  json_data TEXT,
  parse_status TEXT,
  created_at TEXT
);

-- 日報生成紀錄
CREATE TABLE daily_reports (
  id TEXT PRIMARY KEY,
  project_id TEXT,
  date TEXT,
  report_path TEXT,
  progress_csv_path TEXT,
  safety_csv_path TEXT,
  generated_at TEXT,
  event_ids TEXT  -- JSON array of work_event IDs
);
```

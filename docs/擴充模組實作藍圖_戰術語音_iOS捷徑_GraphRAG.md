# 築未科技 — 三大擴充模組實作藍圖

> 痛點導向：開車/工地無法打字、手機操作太慢、RAG 無法理解圖表

---

## 1. 聽覺模組：戰術語音指揮 (Tactical Voice Command)

### 痛點
開車（Tucson 油電）或工地巡視（戴手套、拿 RS10）時無法打字輸入 `!ask` 或 `!memo`。

### 技術架構

```
Discord 語音頻道 → Bot 加入 → 監聽麥克風 → 錄音 → Whisper (Local) 轉文字
    → Task Butler 處理 → 語音合成 (TTS) 回覆
```

### 現有基礎
- `discord.py` + `commands.Bot`：已有文字指令 `!ask`、`!memo`
- `brain_modules/task_butler.py`：`run_one_round()` 可處理文字任務
- `brain_server.py`：`POST /api/agent/tasks/...` 可建立任務

### 實作步驟

| 步驟 | 項目 | 說明 |
|------|------|------|
| 1 | 語音頻道連線 | `discord.py` 內建 `VoiceClient`，需 `commands.Bot` 支援 `VoiceGateway` |
| 2 | 錄音 | 從 `AudioSource` 讀取 PCM 音頻 → 存成 WAV |
| 3 | Whisper (Local) | 安裝 `openai-whisper`；i7-14700 跑 `medium` 模型約即時 |
| 4 | 文字 → Task Butler | 呼叫 `POST /api/agent/tasks` 建立 `semantic-route` 任務，或直接呼叫 `run_one_round` |
| 5 | TTS 回覆 | 使用 `edge-tts`、`pyttsx3` 或 Ollama 內建 TTS |
| 6 | 拍照觸發 | 語音「拍照存證」→ 呼叫 `POST /api/agent/tasks/screen-vlm` 或 Line 相關任務 |

### 關鍵檔案（已實作）

- `Jarvis_Training/jarvis_discord_bot.py`：新增 `!voice join/leave`、`!talk`
- `Jarvis_Training/jarvis_voice_commander.py`：Whisper 轉錄、edge-tts TTS、Task Butler 分流

### 環境變數

```env
WHISPER_MODEL=medium
WHISPER_DEVICE=cpu
TTS_PROVIDER=edge-tts
TTS_VOICE=zh-TW-HsiaoChenNeural
```

### 場景對應

| 語音指令 | 系統行為 |
|----------|----------|
| 「賈維斯，幫我念一下剛剛業主傳來的 Line 訊息重點。」

 | `line_read_vlm` → `question` 含「業主訊息重點」→ `Task Butler` 處理 → TTS 回覆 |
| 「賈維斯，記錄一下：B 區 3 樓樑筋綁紮間距不足，拍照存證。」 | `POST /api/agent/tasks/local-command` 或 `screen-vlm` + 備註存檔 |

---

## 2. 觸覺模組：iOS 捷徑 (Shortcuts) 深度整合

### 痛點
手機開 Web Admin 太慢，需要「一鍵觸發」。

### 技術架構

```
iPhone 捷徑 → 動作「取得 URL 內容」→ POST 到 FastAPI
    → 可選：驗證 Header (X-Shortcut-Token) 或 API Key
```

### 現有基礎
- `brain_server.py` 已有 `POST /api/agent/tasks/local-command`、`POST /api/agent/tasks/line-read-vlm` 等
- `monitor_runtime_and_notify.py` 的白名單與 `host_command` 已處理

### 新增 API 端點

| 端點 | 用途 | 捷徑按鈕 |
|------|------|----------|
| `POST /api/shortcuts/panic` | 緊急備份：關閉視窗、備份、鎖定螢幕 | 🔴 緊急備份 |
| `POST /api/shortcuts/mining` | 執行 Start_Mining.bat | 🟢 挖礦模式 |
| `POST /api/shortcuts/site-report` | 天氣 + 待辦 + Line 未讀 → 總結 → TTS | 🔵 工地回報 |

### 實作步驟

| 步驟 | 項目 | 說明 |
|------|------|------|
| 1 | 新增路由 | `brain_server.py` 新增 `/api/shortcuts/panic`、`/api/shortcuts/mining`、`/api/shortcuts/site-report` |
| 2 | 驗證 | 讀取 `X-Shortcut-Token` 或 `Authorization: Bearer <token>` |
| 3 | 任務派發 | 寫入 `agent_host_jobs.json` 或直接呼叫對應 bat |
| 4 | 捷徑設定 | iOS 捷徑 → 加入動作「取得 URL 內容」→ POST 到 `https://你的域名/api/shortcuts/panic` |

### iOS 捷徑範例（JSON）

```json
{
  "name": "緊急備份",
  "actions": [
    {
      "type": "url",
      "url": "https://brain.zhe-wei.net/api/shortcuts/panic",
      "method": "POST",
      "headers": {"X-Shortcut-Token": "YOUR_SECRET"}
    }
  ]
}
```

### Panic 流程（緊急備份）

1. 寫入 `agent_host_jobs.json`：`job_type: "panic_backup"`
2. `monitor_runtime_and_notify.py` 新增 `panic_backup` 處理：
   - 關閉所有視窗（可選）
   - 備份資料（同步到 Z 槽）
   - 鎖定螢幕（`rundll32.exe user32.dll,LockWorkStation`）

---

## 3. 知識增強：RAG 的「圖表理解」能力 (Graph RAG)

### 痛點
RAG 僅搜文字，營建精華在圖表、施工大樣圖。

### 技術架構

```
PDF → 轉成圖片（每頁）→ VLM (Gemini/Claude) 描述圖片細節
    → 存成文字向量 + 圖元索引
    → 查詢時：文字搜尋 + 圖元索引回傳 → 回傳原圖 + 標註位置
```

### 現有基礎
- `brain_modules/brain_rag.py`：Chroma + sentence-transformers 文字向量
- `brain_server.py`：Qdrant 健康檢查
- `ai_service.py`：Gemini API 已整合

### 實作步驟

| 步驟 | 項目 | 說明 |
|------|------|------|
| 1 | PDF → 圖片 | `pdf2image` 或 `PyMuPDF` 每頁轉 PNG |
| 2 | VLM 描述 | `Gemini 1.5 Pro` 或 `Claude` 送圖片 → 描述圖表細節（含「搭接長度」等） |
| 3 | 向量儲存 | 文字描述存 Chroma/Qdrant；metadata 含 `image_path`、`page_index` |
| 4 | 查詢流程 | 問「連續壁母單元鋼筋搭接長度」→ 搜向量 → 回傳原圖 + 描述 |
| 5 | 標註（進階） | VLM 可額外輸出「搭接長度」在圖中的 bounding box → 前端圈出 |

### 向量儲存格式

```json
{
  "id": "doc_001_page_3",
  "text": "連續壁母單元鋼筋搭接長度為 60 倍直徑，見圖第 3 頁右上角大樣圖。",
  "metadata": {
    "source": "連續壁設計圖.pdf",
    "page": 3,
    "image_path": "Z:/Zhewei_Brain/Knowledge/continuous_wall_p3.png",
    "bounding_box": null
  }
}
```

### 關鍵檔案（已實作）

- `brain_modules/brain_graph_rag.py`：PDF→圖（PyMuPDF/pdf2image）、Gemini VLM 描述、Chroma 儲存
- `agent_tools.py`：新增 `search_graph_rag`、`ingest_graph_rag_pdf` 工具
- `brain_server.py`：`POST /api/graph-rag/ingest`、`GET /api/graph-rag/search`

### 依賴

```
pdf2image
PyMuPDF
google-generativeai  # 已有
```

### 場景對應

| 查詢 | 系統行為 |
|------|----------|
| 「連續壁的母單元鋼筋搭接長度是多少？」 | 查向量 → 回傳「60 倍直徑」+ 附圖頁 3 + 可選標註位置 |

---

## 優先順序建議

| 優先順序 | 模組 | 難度 | 預估工時 |
|----------|------|------|----------|
| 1 | iOS 捷徑 | 低 | 0.5–1 天 |
| 2 | 戰術語音 | 中 | 2–3 天 |
| 3 | Graph RAG | 高 | 3–5 天 |

---

## 架構規則（勿動）

- 嚴禁修改 `agent_tools.py` 第 213–234 行 `run_vision_engine` 跨環境呼叫邏輯
- 嚴禁更動 `report_generator.py` 中影像報表與語音報表分流路徑
- 維持 D:/brain_workspace 與 Z:/Zhewei_Brain 的分流架構

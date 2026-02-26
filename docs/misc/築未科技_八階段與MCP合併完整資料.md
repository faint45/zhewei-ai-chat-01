# 築未科技 — 八階段工作流與 MCP 合併完整資料

**用途**：供 AI 軟體合併使用；內含八階段定義、Win MCP 清單、工作流對照、部署與啟動、路徑規範。  
**來源**：需求到完成八階段流程.md、可以符合的Win_MCP清單.md、各項工作流完成說明.md、brain_workspace/DEPLOY.md。

---

## 一、八階段總覽（需求到完成）

| 階段 | 名稱 | 負責組件 | 說明 |
|------|------|----------|------|
| **1** | 需求 (Requirement) | 網頁管理員 | 接收指令 |
| **2** | 整合理解 (Understanding) | 管理員 (Gemini) | 從 Z 槽提取記憶，理解任務複雜度 |
| **3** | 安排 (Arrangement) | 大腦 (Manager) | 產出計畫；涉及影像則調度 Grok，涉及程式則調度 Claude |
| **4** | 執行 (Execution) | Claude / Jimeng / Ollama | 編碼、媒體、本地資料清洗 |
| **5** | 確認 (Confirmation I) | 本地代理人 (Ollama) | 基礎合規檢核 |
| **6** | 回饋修正 (Feedback & Fix) | Claude 3.5 + Cursor Pro | 錯誤碼精準修復，最終代碼調校 |
| **7** | 確認 (Confirmation II) | 管理員 (Gemini) | 多模型交叉驗證，確保邏輯 $100\%$ 正確 |
| **8** | 完成與佈署 (Completion) | 大腦 | 觸發佈署指令、LaTeX 報表至 Z 槽、更新網頁後台 |

---

## 二、八階段與 MCP 實體動作合併對照

階段編號與名稱以「需求到完成八階段流程」為準；MCP 欄為該階段之「實體動作」執行者（誰做「手腳」）。

| 階段 | 名稱（八階段） | 負責 MCP | 實體動作 (Action) |
|------|----------------|----------|-------------------|
| **1** | 需求 (Requirement) | — | 網頁管理員／brain_server；無 MCP 實體。 |
| **2** | 整合理解 (Understanding) | — | AgentManager／Gemini、TOOLS；無 MCP 實體。 |
| **3** | 安排 (Arrangement) | **Windows-MCP** | 擷取螢幕或打開影像目錄供 YOLOv8／計畫產出用。 |
| **4** | 執行 (Execution) | **Windows-MCP**、**GitHub MCP** | 啟動本地 Python／PowerShell；代碼推送遠端 Repo 版控。 |
| **5** | 確認 (Confirmation I) | — | 本地代理人／Ollama、TOOLS；無 MCP 實體。 |
| **6** | 回饋修正 (Feedback & Fix) | **GitHub MCP** | 修正後代碼推送到遠端 Repo 進行版控。 |
| **7** | 確認 (Confirmation II) | — | 管理員／Gemini 交叉驗證；無 MCP 實體。 |
| **8** | 完成與佈署 (Completion) | **Playwright MCP**、**Filesystem** | 登入雲端控制台或微信小程式上架；監控日誌實時寫入 Z 槽 cache。 |

---

## 三、八階段各階段詳述（對應組件與路徑）

- **1. 需求**：brain_server WebSocket（`/ws`）接收 `{"text":"..."}` 或 `{"message":"..."}`。
- **2. 整合理解**：AgentManager `_load_long_term_memory()` 從 Z:/Zhewei_Brain/Rules/master_rules.md 載入；`_classify_task()` 判斷 vision / complex / conversation。
- **3. 安排**：agent_logic 引擎分流 — 視覺任務 Gemini（或 Grok）；程式任務 Claude；影像鏈 YOLOv8 + vision_worker。
- **4. 執行**：TOOLS（run_command、write_file、read_file、list_dir）經 AgentManager；產出落地 D:\brain_workspace（路徑限 D/Z）。編碼 Claude、媒體 Jimeng、本地 Ollama。
- **5. 確認 I**：ReAct Observation 合規或觸發修復；Ollama 檢核，校對 Log 寫 D/Z。
- **6. 回饋修正**：Observation 異常時切換 Gemini/Claude；write_file 覆蓋 D 槽；Cursor Pro Composer 微調。
- **7. 確認 II**：AgentManager `_cross_validate_results()` — Gemini 深度分析 → 第二意見檢核 → 定稿或「待確認」。進度 LaTeX。
- **8. 完成與佈署**：run_command 觸發腳本或佈署 API；report_generator 寫 Z:/Zhewei_Brain/Reports/（JSONL、CSV、Daily_Voice_Logs.md）；update_web_admin；路徑限 D/Z。

---

## 四、Win MCP 清單（依用途分類）

### 4.1 Windows 桌面／系統整合

| 名稱 | Repo / 來源 | 安裝方式 | 符合點 |
|------|-------------|----------|--------|
| **Windows-MCP** | https://github.com/CursorTouch/Windows-MCP | Cursor：MCP → 新增 → command `uvx`、args `["windows-mcp"]`（需 Python 3.13+、uv） | 輕量、Win 7–11、UI 自動化、開 App、鍵鼠、PowerShell、DOM；與 Cursor 相容 |
| **mcp-windows-desktop-automation** | https://github.com/mario-andreschak/mcp-windows-desktop-automation | `npm install` + Cursor MCP 設 command `node`、args 指向 build 後 main | TypeScript、AutoIt、滑鼠／鍵盤／視窗／行程／截圖；stdio + WebSocket |

### 4.2 瀏覽器自動化

| 名稱 | Repo / 來源 | 安裝方式 | 符合點 |
|------|-------------|----------|--------|
| **cursor-ide-browser** | Cursor 內建 | 無需安裝 | 視窗／分頁、導覽、snapshot、click/type；本機執行 |
| **Playwright MCP** | https://github.com/microsoft/playwright-mcp | Cursor MCP → command `npx`、args `["@playwright/mcp@latest"]` | 跨平台、accessibility tree、Chrome/Firefox/Edge |

### 4.3 程式／版控／部署

| 名稱 | Repo / 來源 | 安裝方式 | 符合點 |
|------|-------------|----------|--------|
| **GitHub MCP** | https://github.com/github/github-mcp-server | Cursor MCP 或官方說明設定 | Repo / Issue / PR / Actions；Windows 本機 stdio |
| **Filesystem** | modelcontextprotocol/servers（參考實作） | 自建或社群版，command 指向 D/Z 允許目錄 | 讀寫檔、列目錄；可限制在 D/Z |

### 4.4 Cursor 使用要點

- **傳輸**：以 stdio 為主；WebSocket 需另開 port、在 Cursor 填 URL。
- **路徑**：MCP 寫檔建議限制在 D 槽或 Z 槽，與 agent_tools、本地手腳一致。
- **啟動**：Cursor 以 command + args 啟動 process；需已安裝 Node / Python / uv。

### 4.5 建議優先試

1. **Windows-MCP** — 本地手腳：鍵鼠、開 App、PowerShell、擷取畫面／DOM。
2. **cursor-ide-browser** — 已有、免裝，網頁操作用。
3. **Playwright MCP** — 進階瀏覽器自動化（錄影、多瀏覽器）。

---

## 五、工作流與完成對照（agent_tools 對齊）

| 工作流 | 完成方式 | 負責組件 | 工具／動作 | 產出位置 |
|--------|----------|----------|------------|----------|
| **編碼** | 寫入程式碼 | Claude / AgentManager | write_file、run_command | D:\brain_workspace 或 D:\Project\{任務}\Draft |
| **撰寫** | 寫入文件、報表、日誌 | AgentManager | write_file、manage_construction_log、generate_voice_report | Z 槽 Reports、Daily_Voice_Logs.md；D 槽限 D/Z |
| **運算** | 視覺辨識、資料處理 | vision_worker / Ollama | run_vision_engine、run_command（D 槽清洗） | 辨識 JSON；大批資料落 D 槽 |
| **分配** | 任務分類與引擎分流 | AgentManager (階段 2–3) | _classify_task()、引擎選擇 | 無檔案產出 |
| **執行** | 跑指令、寫檔、呼叫 API | AgentManager | run_command、write_file、read_file、list_dir、run_vision_engine 等 TOOLS | D 槽 Draft；路徑限 D/Z |
| **回饋** | 錯誤修復、修正覆蓋 | Claude 3.5 / Gemini | write_file 覆蓋、ReAct 再一輪 | D:\Project\{任務}\Fix 或 D 槽覆蓋 |
| **生成** | 報表、語音日誌、媒體 | report_generator / agent_tools | generate_progress_report、generate_voice_report、generate_media | Z 槽 Reports（JSONL/CSV/MD）；媒體 → D:\brain_workspace\output |
| **佈署** | 階段 8 | deploy_service | 觸發佈署腳本或 API | — |
| **網頁後台** | 生成／完成 | update_web_admin | 更新狀態，進度可含 LaTeX $X\%$ | — |

---

## 六、八階段與工作流對齊（完成標誌）

| 階段 | 名稱 | 主要工作流 | 完成標誌 |
|------|------|------------|----------|
| 1 | 需求 | — | 收到 WebSocket 指令 |
| 2 | 整合理解 | 分配（分類） | 載入 Z 槽記憶、任務分類 |
| 3 | 安排 | 分配 | 產出計畫、引擎分流 |
| 4 | 執行 | 編碼、撰寫、運算、執行 | Draft 寫入 D 槽；TOOLS 執行完畢 |
| 5 | 確認 I | 執行（檢核） | Observation 合規或觸發修復 |
| 6 | 回饋修正 | 回饋 | Fix 覆蓋或 ReAct 修復完成 |
| 7 | 確認 II | 運算（多模型檢核） | 交叉驗證通過／定稿 |
| 8 | 完成與佈署 | 生成、執行 | 報表至 Z 槽、佈署觸發、update_web_admin |

---

## 七、路徑與格式規範

- **產出路徑**：僅 D 槽、Z 槽；報表與長期記憶以 Z 槽為準；**資料都放 D 槽**時設 `ZHEWEI_MEMORY_ROOT=D:\brain_workspace`，Reports、cache 寫入 D 槽。
- **進度數值**：LaTeX 格式，例 `$85\%$`（report_generator、update_web_admin）。
- **Draft / Fix / Done**：Draft/Fix 用 D 槽，Done 可搬至 Z 槽 Reports 或專案 Done。
- **主腦與視覺根目錄**：D:\brain_workspace。目錄：input、processed、models、output、cache、Reports、Rules、Contract、static。

---

## 八、部署與啟動（摘要）

### 8.1 一鍵部署（資料都放 D 槽）

- 專案根目錄雙擊 **一鍵部屬到D槽.bat**，或執行：  
  `powershell -ExecutionPolicy Bypass -File scripts\deploy_to_d_drive.ps1`
- 腳本會：建立 D:\brain_workspace 及子目錄、同步 brain_workspace 與主腦核心腳本、建立 venv_vision（ultralytics/torch）、寫入或追加 .env（BRAIN_WORKSPACE、ZHEWEI_MEMORY_ROOT=D:\brain_workspace）。

### 8.2 啟動方式

- **僅主腦**：專案根目錄 `python brain_server.py`；管理介面 http://localhost:8000/static/index.html。
- **全系統（D 槽）**：`cd D:\brain_workspace` → `.\start_all.ps1`（brain_server + site_monitor + 視覺檢查）。
- **本地工作流**：雙擊 `執行_單次任務.bat`、`執行_視覺與報表.bat`；或 `python scripts/run_workflow_step.py --step 單次任務|運算|生成|視覺與報表`（參數見本地手腳說明.md）。

### 8.3 環境變數

- `BRAIN_WORKSPACE`：視覺引擎根目錄（預設 D:\brain_workspace）。
- `ZHEWEI_MEMORY_ROOT`：報表與長期記憶根目錄（預設 Z:\Zhewei_Brain；資料都放 D 時設 D:\brain_workspace）。

---

## 九、對照文件索引（合併時可對齊）

| 文件 | 對應內容 |
|------|----------|
| 需求到完成八階段流程.md | 八階段定義、各階段詳述、對照表 |
| 可以符合的Win_MCP清單.md | Win MCP 分類、與八階段合併對照（六） |
| 各項工作流完成說明.md | 工作流與完成對照、工具對應、八階段與工作流對齊 |
| brain_workspace/DEPLOY.md | D 槽路徑、一鍵部署、手動步驟、環境變數 |
| 本地手腳說明.md | run_workflow_step.py 參數、雙擊 bat、與工作流對齊 |
| 架構守則、全系統架構鎖定規則 | D/Z 分流、agent_tools run_vision_engine、report_generator 分流路徑 禁止修改 |

---

*本資料為合併用完整摘要；實作請遵守架構守則與路徑 D/Z 限制；進度使用 LaTeX（如 $100\%$）。*

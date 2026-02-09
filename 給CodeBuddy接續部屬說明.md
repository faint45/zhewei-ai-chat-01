# 築未科技 — 給 CodeBuddy 接續部屬說明

**對象**：CodeBuddy（接續部屬的 AI／開發者）  
**目的**：依本說明與專案既有文件，接續完成本地 AI 系統（築未大腦）的部屬與缺口補齊。  
**專案路徑**：`c:\Users\user\Desktop\zhe-wei-tech`（Windows）。

- **最新移交狀態**：見 **接續部屬移交報告.md**（當前系統狀態、已完成事項、待辦缺口、移交注意事項、建議下一步）。

---

## 一、目前狀態（接手時）

| 項目 | 狀態 |
|------|------|
| **專案** | 築未科技大腦（zhe-wei-tech）；程式碼就緒，Docker 已停止。 |
| **核心代碼** | 就緒（brain_server.py, agent_logic.py, ai_service.py 等）；架構鎖定，禁止修改指定區域。 |
| **D 槽部署** | 已完成（D:\brain_workspace 目錄結構就緒）；通過 deploy_to_d_drive.ps1 執行。 |
| **環境變數** | .env 配置完成（含 BRAIN_WORKSPACE, ZHEWEI_MEMORY_ROOT）；需確認 CLOUDFLARE_TOKEN 是否填寫。 |
| **本地服務** | 可啟動（python brain_server.py）；管理介面：http://localhost:8000/static/index.html 或 http://localhost:8000/admin。 |
| **外網訪問** | 未啟用；需 docker compose up -d 且 .env 有 CLOUDFLARE_TOKEN；網址：https://brain.zhe-wei.net。 |
| **架構鎖定** | 嚴禁修改 agent_tools.py 第 213–234 行 run_vision_engine；嚴禁更動 report_generator.py 影像/語音報表分流路徑；所有產出路徑限 **D 槽或 Z 槽**；進度數值用 **LaTeX**（如 `$100\%$`）。 |

---

## 二、接續部屬步驟（依優先順序執行）

### 步驟 1：環境與依賴

1. 確認 **Python 3.10+** 已安裝，在專案根目錄執行：  
   `pip install -r requirements-brain.txt`
2. 若專案根目錄無 **.env**，自 **.env.example** 複製一份，至少設定：  
   - `GEMINI_API_KEY`（可選，有則用 Gemini）  
   - `CLOUDFLARE_TOKEN`（若需外網 https://brain.zhe-wei.net）
3. **資料都放 D 槽**時：執行一鍵 D 槽部屬（步驟 2），腳本會寫入或追加 .env 的 `BRAIN_WORKSPACE=D:\brain_workspace`、`ZHEWEI_MEMORY_ROOT=D:\brain_workspace`。

### 步驟 2：D 槽部屬（資料都放 D 槽）

於專案根目錄執行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy_to_d_drive.ps1
```

或雙擊 **一鍵部屬到D槽.bat**。

腳本會：建立 `D:\brain_workspace` 及子目錄（input、processed、models、output、cache、Reports、Rules、Contract、static）、同步 brain_workspace 與主腦核心腳本至 D 槽、建立 **venv_vision**（Python 3.12）並安裝 ultralytics、torch、寫入或追加 .env 之 D 槽設定。

### 步驟 3：啟動驗證

1. **診斷**（可選）：`python startup_diagnostics.py`  
   - 若無 Z 槽，診斷可能因 Z 槽未掛載而部分失敗；可改為資料都放 D 槽（.env 已設 ZHEWEI_MEMORY_ROOT=D:\brain_workspace）。
2. **啟動主腦**：`python brain_server.py`（確認端口 8000 僅一進程）  
   - 管理介面：http://localhost:8000/static/index.html 或 http://localhost:8000/admin  
   - 健康檢查：http://localhost:8000/health（含 ollama、venv_vision、static_dir、progress_dir）
3. **測試**：另開終端執行 `python scripts/test_brain_server.py`，驗證 /health、/、/static/index.html 或 /admin。

### 步驟 4：接線與營運（高優先、程式已留介面）

| 項目 | 檔案／位置 | 接續工作 |
|------|------------|----------|
| **update_web_admin** | agent_tools.py、brain_server.py | brain_server 訂閱/讀取 D 槽 progress 檔並經 WebSocket 廣播；或 agent_logic 階段完成時呼叫 update_web_admin 再推播。 |
| **deploy_service** | agent_tools.py | 實際指令限 D/Z 下白名單（如 nssm 路徑或 `D:\brain_workspace\start_all.ps1`），避免任意指令。 |
| **generate_media** | agent_tools.py | 對接 Jimeng 或 Grok API，產出寫入 `D:\brain_workspace\output`。 |
| **Claude** | ai_service.py、agent_logic.py、.env | .env 補 Claude API Key，agent_logic 注入 claude_service，階段 4／6 啟用。 |

### 步驟 5：MCP 當手腳（可選，給 Cursor 使用者）

- 見 **可以符合的Win_MCP清單.md** 安裝 Windows-MCP、GitHub MCP、Playwright MCP、Filesystem MCP。  
- 運用方式見 **如何運用MCP當手腳.md**。  
- 八階段與 MCP 對照見 **可以符合的Win_MCP清單.md** 第六節。

### 步驟 6：外網（可選）

- .env 有 `CLOUDFLARE_TOKEN` 後，在專案根目錄執行：`docker compose up -d`  
- 外網網址：https://brain.zhe-wei.net、https://brain.zhe-wei.net/static/index.html  

### 步驟 7：部屬到 Railway（可選）

- 將專案推送到 GitHub，在 [Railway](https://railway.app) 新建專案並從 Repo 部署。  
- 專案已含 **Procfile**（`web: python brain_server.py`）、**requirements.txt**（`-r requirements-brain.txt`）、**runtime.txt**（Python 3.11）；Railway 會注入 `PORT`，brain_server 已讀取 `PORT` 或 `BRAIN_WS_PORT`。  
- 在 Railway 專案 **Variables** 設定環境變數（勿提交 .env）：  
  - `GEMINI_API_KEY`、`ANTHROPIC_API_KEY` 或 `CLAUDE_API_KEY`（有則啟用對應引擎）  
  - 可選：`BRAIN_WORKSPACE`、`ZHEWEI_MEMORY_ROOT`（雲端無 D/Z 槽時可不設，使用預設或暫存目錄）  
- 部署完成後，管理介面：`https://<你的服務>.up.railway.app/static/index.html` 或 `/admin`；健康檢查：`/health`。  

### 步驟 8：測試與 E2E（可選）

- 若 Z 槽已掛載且 D:\brain_workspace 就緒、input 內有 test.jpg 或實際圖片，可跑一輪「視覺→報表→Z 寫入」驗證（或改為 D 槽寫入）。  
- 指令範例：`python scripts/run_workflow_step.py --step 視覺與報表 --input D:\brain_workspace\input`  
- E2E：啟動 Ollama 或在 `D:\brain_workspace\input` 放一張圖片後，執行：`python scripts/run_e2e.py`。

---

## 三、常見狀況與對應

| 狀況 | 對應方式 |
|------|----------|
| **管理介面仍 404** | 目前端口 8000 可能被佔用。請先關閉佔用 8000 的程式（或舊 brain_server），再執行 `python brain_server.py`；或使用備用入口 http://localhost:8000/admin。 |
| **Claude / 外網** | 在 .env 填寫 `ANTHROPIC_API_KEY`（或 `CLAUDE_API_KEY`）以啟用 Claude。外網需先啟動 Docker Desktop，並在 .env 填寫 `CLOUDFLARE_TOKEN` 後執行 `docker compose up -d`。 |
| **E2E** | 啟動 Ollama 或在 `D:\brain_workspace\input` 放一張圖片後，執行：`python scripts/run_e2e.py`。 |
| **部屬到 Railway** | 見步驟 7；Procfile、requirements.txt、runtime.txt 已就緒；在 Railway Variables 設定 API keys 與可選路徑變數。 |

---

## 四、關鍵檔案與指令一覽

| 類別 | 檔案／指令 |
|------|------------|
| **專案根目錄** | c:\Users\user\Desktop\zhe-wei-tech |
| **入口** | brain_server.py |
| **邏輯／工具** | agent_logic.py、agent_tools.py、ai_service.py、report_generator.py |
| **視覺** | brain_workspace/vision_worker.py；run_vision_engine 呼叫 D:\brain_workspace\venv_vision |
| **D 槽一鍵部屬** | 一鍵部屬到D槽.bat 或 `powershell -ExecutionPolicy Bypass -File scripts\deploy_to_d_drive.ps1` |
| **本地工作流** | scripts/run_workflow_step.py（--step 單次任務|運算|生成|視覺與報表）；執行_單次任務.bat、執行_視覺與報表.bat |
| **全系統啟動（D 槽）** | cd D:\brain_workspace → .\start_all.ps1 |
| **診斷** | python startup_diagnostics.py |
| **服務測試** | 先 python brain_server.py，再 python scripts/test_brain_server.py |
| **環境變數** | BRAIN_WORKSPACE（預設 D:\brain_workspace）、ZHEWEI_MEMORY_ROOT（預設 Z:\Zhewei_Brain；資料都放 D 時設 D:\brain_workspace） |
| **Railway 部屬** | Procfile（web: python brain_server.py）、requirements.txt（-r requirements-brain.txt）、runtime.txt（Python 3.11）；Railway 注入 PORT，brain_server 已讀取 PORT 或 BRAIN_WS_PORT。 |

---

## 五、缺口清單與文件索引（接續時對照）

- **最新移交報告**：**接續部屬移交報告.md**（當前系統狀態、已完成事項、待辦缺口、移交注意事項、建議下一步；可直接移交其他 AI 或開發者）。  
- **完整缺口清單**：**本地AI系統缺口清單.md**（環境、接線、MCP、測試、商用等）。  
- **交接清單**：**交接清單_2026-02-08.md**（建置狀況、啟動/停止、測試指令、已知問題）。  
- **八階段與 D 槽**：**需求到完成八階段流程.md**、**八階段與D槽對照.md**。  
- **部屬細節**：**brain_workspace/DEPLOY.md**、**佈署指南.md**。  
- **架構鎖定**：**.cursor/rules/全系統架構鎖定規則.mdc**、**架構守則.md**。  
- **代碼規範**：**.cursorrules**（代碼最簡化、完整檔案產出、路徑 D/Z、LaTeX 進度）。

---

## 六、禁止與必須遵守

1. **禁止**修改 agent_tools.py 第 213–234 行 **run_vision_engine** 跨環境呼叫邏輯。  
2. **禁止**更動 report_generator.py 中影像報表（CSV/JSONL）與語音報表（Markdown）的**分流路徑**。  
3. **所有**檔案／產出路徑限 **D 槽或 Z 槽**（或專案內 zhewei_memory）；進度數值使用 **LaTeX**（如 `$100\%$`）。  
4. **代碼更新**須提供「修正後的完整檔案」，不提供局部片段。

---

## 七、接續後建議回報

接續部屬完成後，建議回報：  
- 步驟 1–3 是否通過（環境、D 槽、啟動與 test_brain_server）。  
- 步驟 4 哪些已接線（update_web_admin、deploy_service、generate_media、Claude）。  
- 步驟 5–7 是否執行（MCP、外網、E2E）。  
- 是否更新 **本地AI系統缺口清單.md** 之勾選狀態。

---

*本說明供 CodeBuddy 接續部屬使用；實作請遵守架構守則與全系統架構鎖定規則。*

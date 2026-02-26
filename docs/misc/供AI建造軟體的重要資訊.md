# 供 AI 建造軟體的重要資訊（含可擴充點）

築未科技大腦 — 邊緣計算與橋接系統。本文檔供外部軟體、設備、網頁或 AI 建造流程接入與擴充時參考。

---

## 一、系統架構鐵則（必讀）

- **身份**：本專案為築未科技大腦，各子系統皆屬其一部分，功能不重複、職責單一。
- **隔離**：子系統修改不得影響其他子系統；共享邏輯集中於 `guard_core.py` 等共用模組，禁止在各處複製。
- **金鑰**：`%USERPROFILE%\.openclaw\.env` 內之 `GEMINI_API_KEY`、`DISCORD_BOT_TOKEN`、`TELEGRAM_BOT_TOKEN` 一旦存在且非空，**禁止**被專案 `.env` 覆寫。

---

## 二、邊緣計算系統（edge_compute.py）

### 2.1 現有功能

| 功能 | 說明 |
|------|------|
| **節點註冊** | `register_node(name, role)`，role 預設 `"compute"` |
| **本地推理** | `local_inference(prompt)` → 呼叫 Ollama `gemma3:4b`，不經雲端 |
| **服務偵測** | `ping_ollama()` → 偵測 `http://localhost:11434` 是否就緒，回傳 (成功, 延遲 ms) |
| **吞吐統計** | `record_op(bytes_count)`、`get_throughput_mbps()`、`get_ops_rate()` |
| **系統資訊** | `get_system_info()` → host、os、cwd、uptime_sec、ops、throughput_mbps |
| **邊緣守護** | `run_edge_daemon(on_status=None)` → 每 10 秒 ping、更新節點狀態，可選每輪呼叫 `on_status(info)` |

單例取得：`from edge_compute import get_edge` → `get_edge()` 回傳全域 `EdgeCompute` 實例。

### 2.2 可擴充點（後續可由 AI 建造軟體擴充）

- **多節點角色**：`EdgeNode.role` 目前僅用 `"compute"`，可擴充為 `sensor`、`gateway`、`display` 等，並在 `get_system_info()` 或上報結構中區分。
- **推理後端**：`local_inference()` 目前固定 Ollama + `gemma3:4b`。可改為可配置（env：`OLLAMA_MODEL`、`OLLAMA_BASE_URL`），或新增 `local_inference_via(url, model, prompt)` 支援多後端。
- **任務佇列**：類別說明已含「任務佇列」，目前未實作。可擴充為 `submit_task(payload)` → 佇列，由 daemon 或背景 worker 消費並呼叫 `local_inference` 或自訂 handler。
- **上報端點**：`run_edge_daemon(on_status=...)` 目前僅回呼；可擴充為將 `info` 定期 POST 至 `EDGE_REPORT_URL`（需在 guard_core 或 env 約定）。
- **多服務 ping**：除 Ollama 外，可新增 `ping_xxx()`（例如視覺服務、自訂 API），並在 daemon 中一併更新節點狀態或 `info`。

---

## 三、共用邏輯與入口（guard_core.py）

### 3.1 對外介面

- **process_message(content, user_id, base_url, model)**  
  處理單一訊息，與 Discord/API 一致。回傳 `(reply: str, msg_type: str)`。  
  - 會先處理系統指令（授權、檢核、修復 AI 視覺等）、再分流問答/開發/Agent。
- **run_agent(user_msg, user_id)**  
  執行 Agent（呼叫 `agent_tools.TOOL_MAP`、LLM 產出 TOOL 呼叫）。回傳單一字串。
- **get_weather(msg)**、**get_time()**  
  天氣、時間，供組裝 prompt 或直接 API 回傳。
- **grant_auth / revoke_auth / _is_authorized**  
  授權與本機指令控管。
- **run_system_check()**  
  檢核 Ollama、AI 提供者、知識庫、AI 視覺、Brain Bridge、Discord Token、Agent 工具數。

### 3.2 可擴充點

- **STRATEGIST_CONFIG**：軍師協議用；`test_execution` 失敗時可介入預留函式（見專案規則）。
- **意圖分流**：`get_intent()` 回傳 `code | question | system | general`；可加新意圖並在 `process_message` 內分流。
- **Agent 觸發關鍵字**：`is_agent_task()` 內關鍵字串；新增工具或場景時可在此加入觸發詞。
- **handle_action()**：系統指令（授權、檢核、修復 AI 視覺等）；可在此加新指令類型，保持單一職責。

---

## 四、Agent 工具（agent_tools.py）

### 4.1 工具清單（TOOL_MAP）

- 檔案：`read_file`、`write_file`、`list_dir`、`diff_files`
- 運算與時間：`calc`、`get_time`
- 建置與部署：`run_build`、`run_deploy_vercel`、`run_self_check`、`run_git_push`
- 知識與學習：`search_github`、`learn_from_github`、`run_self_learn`、`search_knowledge`
- 執行與搜尋：`run_python`、`web_search`、`fetch_url`
- 創意（ai_creative_tools）：`text_to_image`、`generate_3d` 等（若已安裝）
- 視覺（ai_vision_tools）：`edge_detect`、`image_analyze`、`object_detect`、`scene_simulate`（若已安裝）
- CodeBuddy（codebuddy_integration）：`codebuddy_ask`、`codebuddy_review`、`codebuddy_fix`、`codebuddy_generate`（若已安裝）

呼叫格式：`TOOL: 工具名(["參數1","參數2"])`，由 `parse_tool_call()` 解析，`run_tool(name, args)` 執行。

### 4.2 可擴充點

- **新增工具**：在 `agent_tools.py` 中實作函式，並在 `TOOL_MAP` 與 `tool_descriptions()` 中註冊；或透過可選模組（如 `ai_vision_tools.VISION_TOOL_MAP`）`update` 進 `TOOL_MAP`。
- **邊緣推理工具**：可新增例如 `edge_inference`，內部呼叫 `get_edge().local_inference(prompt)`，供 Agent 直接使用邊緣推理。
- **描述與權限**：新工具需在 `tool_descriptions()` 中補上一行說明，並遵守 `_safe_path`、`_blocked` 等安全規則。

---

## 五、大腦橋接 API（brain_bridge_fastapi.py）

### 5.1 端點摘要

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /health | 服務健康 |
| GET | /login, /demo | 登入頁、運算 Demo 頁 |
| POST | /chat | 對話，body: `message`, `user_id`；內部 `process_message` |
| POST | /agent | Agent，body: `message`, `user_id`；內部 `run_agent` |
| POST | /compute | 統一運算，body: `message`, `user_id`, `source`(device/software/web), `device_id`；內部 `process_message` |
| GET | /weather, /time | 天氣、時間 |
| POST | /auth/grant, /auth/revoke, GET /auth/status | 授權 |
| POST | /auth/login, /auth/logout, GET /auth/me | 帳密登入與 Session |
| GET | /integrations/info | 接入資訊（端點、版本、sources） |
| POST | /integrations/query | 知識庫查詢，body: `query`, `limit` |

認證：`X-API-Key` 或 `api_key` 查參 或 Session（登入後）。  
環境：`BRAIN_BRIDGE_API_KEY`、`AUTH_USERS`、`RATE_LIMIT_PER_MIN`、`SESSION_TTL`、`OLLAMA_BASE_URL`、`OLLAMA_MODEL` 等。

### 5.2 可擴充點

- **邊緣狀態 API**：新增 GET `/edge/status`，內部 `get_edge().get_system_info()` 並加上 `ping_ollama()` 結果，供設備/軟體查詢邊緣節點狀態。
- **邊緣推理 API**：新增 POST `/edge/inference`，body: `prompt`，內部 `get_edge().local_inference(prompt)`，回傳文字結果。
- **Webhook 或 MQ**：若需設備主動上報，可新增 POST `/edge/report` 或訂閱佇列，寫入共用儲存或轉發至現有 daemon `on_status`。

---

## 六、知識與檢索

- **brain_knowledge**：`add()`、`search()`、`get_stats()`；資料檔由 `brain_data_config` 設定（如 `brain_knowledge.ndjson`）。
- **brain_retrieve**：統一檢索 Chroma → brain_knowledge → Mem0，回傳可注入 prompt 的上下文。
- **brain_rag**：Chroma 向量與同步；可擴充為邊緣側專用索引或多集合。

---

## 七、環境變數（常用）

| 變數 | 說明 |
|------|------|
| OLLAMA_BASE_URL | Ollama 位址，預設 http://127.0.0.1:11434 |
| OLLAMA_MODEL | 對話/推理模型，如 qwen2.5:7b、gemma3:4b |
| BRAIN_BRIDGE_API_KEY | 橋接 API 金鑰 |
| AUTH_USERS | 帳密登入，格式 user:pass 或 user:sha256 |
| AUTHORIZED_USER_ID | 可執行本機/授權指令的 user_id |
| ZHEWEI_BRAIN_URL | Brain Bridge 基底 URL（檢核用） |
| DISCORD_BOT_TOKEN, TELEGRAM_BOT_TOKEN | 傳令兵（勿被專案覆寫） |
| STRATEGIST_API_KEY, USE_PREMIUM_STRATEGIST | 軍師協議／付費軍師 |

使用者優先憑證：`%USERPROFILE%\.openclaw\.env`，專案 `.env` 不得覆寫已存在且非空的鍵。

---

## 八、整合與儀表板

- **messenger_dashboard**：可選 `from edge_compute import get_edge`，`run_edge_daemon(on_edge_status=...)` 將狀態寫入儀表板資料（如 `db.edge_info`）。
- **public/brain-api-demo.html**：可呼叫 `/chat`、`/agent`、`/compute` 等，作為網頁端運算範例。
- **local_robot**：本機主控台，直接使用 `process_message`，可作為設備或腳本整合範本。

---

## 九、AI 建造軟體擴充檢查表

1. **邊緣節點**：是否需新 role、新 ping 目標、或任務佇列？→ 擴充 `edge_compute.py`。
2. **新後端/模型**：是否改用或並存其他本地模型？→ 擴充 `local_inference` 或新增方法，並以 env 切換。
3. **新 Agent 工具**：是否要讀寫專案檔、呼叫外部 API、或呼叫邊緣推理？→ 在 `agent_tools.TOOL_MAP` 與描述中註冊。
4. **新 API**：設備/網頁是否需要邊緣狀態或邊緣推理？→ 在 `brain_bridge_fastapi.py` 新增 `/edge/*` 或 `/compute` 擴充。
5. **新系統指令**：是否要新關鍵字觸發檢核、授權或修復？→ 在 `guard_core.handle_action()` 與 `is_agent_task()` 中擴充，不複製既有邏輯。
6. **上報與監控**：是否要將邊緣狀態上報到雲端或監控後端？→ 在 `run_edge_daemon(on_status=...)` 內或新端點實作上報，並用 env 設定 URL/開關。

以上為供 AI 建造軟體使用的重要資訊與可擴充點，後續擴充時請維持單一職責與模組隔離。

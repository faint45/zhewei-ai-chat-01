# 築未科技 — 整個本地 AI 系統還缺什麼

**用途**：盤點本地 AI 系統（築未大腦 + 八階段工作流 + MCP 手腳）目前缺口，方便依優先順序補齊。  
**依據**：交接清單_2026-02-08、系統完整度彙整與優化建議_2026-02-08、築未科技大腦_缺口與優化清單、全系統功能測試報告_2026-02-05。

---

## 一、環境與依賴（交接清單未勾選＝缺）

| 項目 | 狀態 | 說明 |
|------|------|------|
| **Python 3.10+** | [ ] | 已安裝並 `pip install -r requirements-brain.txt` |
| **.env** | [ ] | 專案根目錄有 `.env`，至少設 `GEMINI_API_KEY`（可選）、`CLOUDFLARE_TOKEN`（外網用） |
| **Ollama** | [ ] 可選 | 本機 `http://localhost:11434` 可用於地端檢核（階段 5） |
| **D 槽 brain_workspace** | [ ] 可選 | 有 `D:\brain_workspace` 且已跑過「一鍵部屬到D槽」則熱資料落 D |
| **Z 槽** | [ ] 可選 | Rclone 掛載 `Z:\Zhewei_Brain` 時報表與長期記憶寫 Z；無則用 D 槽或 `./zhewei_memory` |
| **venv_vision（Python 3.12）** | [ ] | D:\brain_workspace\venv_vision 已建且已裝 ultralytics、torch（視覺辨識用） |
| **NSSM（Windows 服務）** | [ ] 可選 | 若要開機常駐，需 NSSM 並執行「安装築未大腦服務.bat」 |

---

## 二、接線與營運（高優先：程式碼已留、實際 API 未接）

| 項目 | 現狀 | 缺口 |
|------|------|------|
| **generate_media** | stub（建空檔） | 對接 Jimeng 或 Grok API，產出寫入 `D:\brain_workspace\output` |
| **update_web_admin** | ✅ 已接線 | agent_tools 寫入 D 槽 output/web_admin_progress.json；brain_server 每 2 秒讀取並經 WebSocket 廣播。 |
| **deploy_service** | ✅ 已接線 | 白名單：nssm 服務名（ZheweiBrain/Ollama/Rclone）或 D/Z 下 .bat/.cmd/.ps1 路徑。 |
| **Claude 接線** | agent_logic 可注入 claude_service | .env 或設定檔補 Claude API Key，階段 4／6 啟用 |
| **Grok／Jimeng** | 文件提及、未接 | 影像擴充／媒體產出可選接 Grok、Jimeng API |
| **階段 7 第二意見** | 元寶、千問已預留 | ai_service 內 TencentService、AliyunService 接 API 後啟用交叉驗證 |

---

## 三、MCP 當手腳（在 Cursor 裡用 AI 代執行）

| 項目 | 狀態 | 說明 |
|------|------|------|
| **Windows-MCP** | [ ] | 安裝並在 Cursor MCP 新增（uvx windows-mcp）；階段 3／4 跑腳本、開目錄、擷取畫面 |
| **GitHub MCP** | [ ] | 安裝並設定認證；階段 4／6 代碼推送遠端 Repo |
| **Playwright MCP** | [ ] | 安裝（npx @playwright/mcp）；階段 8 登入雲端控制台／小程式上架 |
| **Filesystem MCP** | [ ] | 自建或社群版，限制 D/Z；階段 8 監控日誌寫 Z 槽 cache（或 D 槽） |
| **運用說明** | ✅ | 見 **如何運用MCP當手腳.md** |

---

## 四、對外與外網

| 項目 | 狀態 | 說明 |
|------|------|------|
| **本機 8000** | [ ] | `python brain_server.py` 或 Windows 服務 ZheweiBrain |
| **Cloudflare Tunnel** | [ ] | .env 有 `CLOUDFLARE_TOKEN` 且 `docker compose up -d` 時，外網 https://brain.zhe-wei.net 可連 |
| **DNS** | ✅ | brain.zhe-wei.net → CNAME cfargotunnel 已設 |

---

## 五、可觀測性與維運

| 項目 | 現狀 | 缺口 |
|------|------|------|
| **API 呼叫日誌** | 無系統性紀錄 | 誰、何時、哪個端點、user_id；寫入 D/Z 日誌或 DB |
| **健康檢查擴充** | ✅ 已接線 | /health 回傳 ollama、venv_vision、static_dir、progress_dir 等依賴狀態。 |
| **告警** | 無 | 服務掛掉、錯誤率過高、預算快盡時 Webhook／郵件（可後期） |
| **備份排程** | 有 backup-brain-data.py | 未排程、未含 Chroma；可加 Windows 工作排程器＋Chroma 目錄 |

---

## 六、測試與 E2E

| 項目 | 狀態 | 說明 |
|------|------|------|
| **startup_diagnostics.py** | [ ] | 執行通過（Z 槽可選；D 槽、venv_vision、Port 8000 等） |
| **test_brain_server.py** | [ ] | 先啟動 brain_server（確認 8000 僅一進程），再跑；驗證 /health、/、/static/index.html 或 /admin |
| **E2E 視覺→報表→Z 寫入** | [ ] | 需 Z 槽掛載、D:\brain_workspace 就緒、input 內有 test.jpg 或實際圖片 |

---

## 七、商用／訂閱制（若要做訂閱制才補）

| 項目 | 現狀 | 缺口 |
|------|------|------|
| **方案分級** | 無 | 免費/個人/團隊/企業；額度或 API Key 群組 |
| **依 user_id／API Key 用量** | 僅全站 | 分用戶／Key 統計，依方案限額、計費 |
| **額度檢查** | 僅全站預算 | 呼叫前檢查該用戶/Key 是否超額，403 或降級 |
| **Session 持久化** | 記憶體 | Redis 或 DB，避免重啟全員重登 |
| **計費與帳單** | 無 | 可後期；金流或內部帳務 |

---

## 八、體驗與文件（中／低優先）

| 項目 | 說明 |
|------|------|
| **管理介面進度** | 改為解析 WebSocket 推送的 LaTeX（如 $95\%$）更新總進度，取代 logs.length×10 |
| **快截按鈕** | 「產出影像報表」「重啟 Ollama」綁定實際 WebSocket 指令或 deploy_service |
| **代理人狀態真實化** | 左欄 Gemini/Claude/Ollama/Media 改為依引擎可用性（ping、API key）回報 |
| **OpenAPI／錯誤碼** | 補端點說明、範例、統一錯誤格式（code + message） |

---

## 九、建議優先順序（本地先跑順）

1. **環境勾選**：Python、.env（GEMINI_API_KEY）、D 槽一鍵部署、venv_vision、Ollama（可選）。
2. **啟動驗證**：`python brain_server.py` → `python scripts/test_brain_server.py`；必要時 `python startup_diagnostics.py`。
3. **Z 槽或 D 槽擇一**：有 Rclone 就掛 Z；否則設 `ZHEWEI_MEMORY_ROOT=D:\brain_workspace`（資料都放 D）。
4. **接線三項**：update_web_admin（進度推播）、deploy_service（白名單指令）、generate_media（可後補）。
5. **MCP 當手腳**：至少 Windows-MCP + GitHub MCP，依 **如何運用MCP當手腳.md** 在 Cursor 裡下指令。
6. **E2E 可選**：Z 槽＋D:\brain_workspace＋test.jpg 齊備後跑一輪「視覺→報表→Z 寫入」。

---

*本清單依專案既有文件彙整；實作請遵守架構守則與 D/Z 路徑限制。*

# 築未科技 — 可以符合的 Win MCP 清單

**說明**：在 Windows 上可運行、且可與 Cursor／本地工作流搭配的 MCP 伺服器；依用途分類。

- **專案 MCP 設定**：已加入 **.cursor/mcp.json**（Windows-MCP、Playwright、GitHub）；GitHub 的 token 不寫入檔案，請用 Cursor 或系統環境變數設定。
- **可呼叫的 MCP 工具名稱**：見 **可呼叫的MCP工具.md**（各伺服器工具名稱、在 Cursor 裡怎麼看到、速查與驗證方式）。
- **如何運用 MCP 當手腳**：見 **如何運用MCP當手腳.md**（在 Cursor 對話中下指令，由 AI 透過 MCP 代你執行跑腳本、推代碼、登入後台、寫日誌等實體動作）。

---

## MCP 設定與依賴檢查

1. **讓 Cursor 讀到設定**：重載視窗或重開 Cursor（MCP 會依 `.cursor/mcp.json` 載入）。
2. **本機依賴**  
   - **Windows-MCP**：安裝 [uv](https://github.com/astral-sh/uv) 並有 Python 3.13+。  
   - **Playwright / GitHub**：已用 `npx`，需有 Node.js。
3. **GitHub**：在 Cursor 的環境變數或系統環境變數中設定 `GITHUB_PERSONAL_ACCESS_TOKEN`（勿把 token 寫入 `.cursor/mcp.json` 或提交到 git）。若要在 mcp.json 的 `github.env` 裡填，僅限本機、且勿 commit。
4. **cursor-ide-browser**：Cursor 內建，不需寫入 mcp.json。
5. **Filesystem MCP**：若要用，需自建或使用社群版，再在 `.cursor/mcp.json` 的 `mcpServers` 裡新增一筆。
6. **運用方式**：見 **如何運用MCP當手腳.md**。

---

## 一、Windows 桌面／系統整合（最符合「本地手腳」）

| 名稱 | Repo / 來源 | 安裝方式 | 符合點 |
|------|-------------|----------|--------|
| **Windows-MCP** | https://github.com/CursorTouch/Windows-MCP | Cursor：MCP → 新增 → command `uvx`、args `["windows-mcp"]`（需 Python 3.13+、uv） | 輕量、Win 7–11、UI 自動化、開 App、鍵鼠、PowerShell、DOM 模式可抓網頁；與 Cursor 相容 |
| **mcp-windows-desktop-automation** | https://github.com/mario-andreschak/mcp-windows-desktop-automation | `npm install` + 在 Cursor MCP 設 command `node`、args 指向 build 後 main | TypeScript、AutoIt、滑鼠／鍵盤／視窗／行程／截圖；stdio + WebSocket |

---

## 二、瀏覽器自動化（Windows 上可用）

| 名稱 | Repo / 來源 | 安裝方式 | 符合點 |
|------|-------------|----------|--------|
| **cursor-ide-browser** | Cursor 內建 | 無需安裝，Cursor 已含 | 視窗／分頁操作、導覽、snapshot、click/type；本機執行 |
| **Playwright MCP** | https://github.com/microsoft/playwright-mcp | Cursor MCP → command `npx`、args `["@playwright/mcp@latest"]` | 跨平台含 Windows、accessibility tree、Chrome/Firefox/Edge |

---

## 三、程式／版控／部署（Windows 上可用）

| 名稱 | Repo / 來源 | 安裝方式 | 符合點 |
|------|-------------|----------|--------|
| **GitHub MCP** | https://github.com/github/github-mcp-server | Cursor MCP 或官方說明設定 | Repo / Issue / PR / Actions；Windows 本機跑 stdio |
| **Filesystem** | modelcontextprotocol/servers（參考實作） | 自建或社群版，command 指向 D/Z 允許目錄 | 讀寫檔、列目錄；可限制在 D/Z 對齊築未路徑 |

---

## 四、在 Cursor 裡怎麼「符合」

- **傳輸**：以 **stdio** 為主（Cursor 在 Windows 上穩定）；若 MCP 支援 WebSocket，需另開 port、在 Cursor 填 URL。
- **路徑**：若 MCP 會寫檔，建議限制在 **D 槽或 Z 槽**，與 `agent_tools`、本地手腳一致。
- **啟動**：Cursor 會用設定的 `command` + `args` 在本機啟動 process；需已安裝對應執行環境（Node / Python / uv）。

---

## 五、建議優先試（符合你目前工作流）

1. **Windows-MCP** — 補足「本地手腳」：鍵鼠、開 App、PowerShell、擷取畫面／DOM，可直接在 Cursor 對話裡操作 Windows。
2. **cursor-ide-browser** — 已有、免裝，網頁相關操作用。
3. **Playwright MCP** — 若要更進階的瀏覽器自動化（含錄影、多瀏覽器），可再加。

---

## 六、與八階段工作流合併對照

對齊 **需求到完成八階段流程.md** 之階段編號與名稱；下表為各階段對應之 MCP 實體動作（誰做「手腳」）。

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

- 階段名稱與編號以 **需求到完成八階段流程.md** 為準；MCP 欄為該階段之「實體動作」執行者。
- 路徑與格式：Z 槽 cache、Reports 依架構守則；進度使用 LaTeX（如 $100\%$）。

---

*清單會隨 MCP 生態更新；實作時請遵守架構守則與路徑 D/Z 限制。*

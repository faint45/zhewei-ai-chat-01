# 築未科技 — 可呼叫的 MCP 工具

**用途**：列出本專案已設定的 MCP 伺服器與其**可呼叫工具名稱**，供在 Cursor Composer 中由 AI 代為執行。  
**設定檔**：`.cursor/mcp.json`（Windows-MCP、Playwright、GitHub）。

---

## 一、在 Cursor 裡怎麼看到可呼叫的 MCP 工具

1. 開啟 **Cursor Settings** → **Features** → **MCP**。  
2. 確認已載入的 MCP 伺服器（本專案：windows-mcp、playwright、github）。  
3. 點 **重新整理** 可更新工具列表；每個伺服器底下的工具即為「可呼叫的 MCP 工具」。  
4. **Composer Agent** 會依你的自然語言請求自動選用對應工具；也可在對話中**指名工具或功能**（例如「用 Windows-MCP 執行 PowerShell…」「用瀏覽器打開 localhost:8000」）。

**注意**：MCP 工具僅在 **Composer Agent** 中可用，且依 Cursor 與模型支援而定。

---

## 二、本專案已設定的 MCP 與可呼叫工具

### 1. Windows-MCP（`windows-mcp`）

**啟動**：`python -m uv tool run windows-mcp`（見 `.cursor/mcp.json`）。  
**依賴**：Python 3.13+、[uv](https://github.com/astral-sh/uv)。

| 工具名稱 | 說明 |
|----------|------|
| **Click** | 在指定座標點擊螢幕。 |
| **Type** | 在元素上輸入文字（可選清除原內容）。 |
| **Scroll** | 在視窗或區域上下／左右捲動。 |
| **Move** | 移動滑鼠或拖曳（drag=True）到座標。 |
| **Shortcut** | 按下鍵盤快捷鍵（如 Ctrl+c、Alt+Tab）。 |
| **Wait** | 暫停指定時間。 |
| **Snapshot** | 擷取桌面與 UI 狀態（可選 use_dom=True 僅網頁內容、use_vision=True 含截圖）。 |
| **App** | 從開始選單啟動應用、調整視窗、切換 App。 |
| **Shell** | 執行 **PowerShell** 指令。 |
| **Scrape** | 擷取整個網頁內容。 |

**在對話中可這樣呼叫**：  
「請用 Windows-MCP 的 Shell 在 D:\brain_workspace 執行 `python brain_server.py`。」  
「請用 Windows-MCP 擷取螢幕並存到 D:\brain_workspace\input\capture.png。」

---

### 2. Playwright MCP（`playwright`）

**啟動**：`npx -y @playwright/mcp@latest`。  
**依賴**：Node.js。

| 工具名稱 | 說明 |
|----------|------|
| **browser_navigate** | 導覽至指定 URL。 |
| **browser_snapshot** | 擷取目前頁面無障礙快照（優於截圖）。 |
| **browser_click** | 點擊頁面元素（需 ref）。 |
| **browser_fill_form** | 填寫表單欄位。 |
| **browser_type** | 在元素上輸入文字。 |
| **browser_hover** | 滑鼠懸停於元素。 |
| **browser_press_key** | 按下鍵盤按鍵。 |
| **browser_drag** | 拖曳元素。 |
| **browser_select_option** | 選擇下拉選項。 |
| **browser_navigate_back** | 返回上一頁。 |
| **browser_resize** | 調整瀏覽器視窗大小。 |
| **browser_handle_dialog** | 處理 alert/confirm/prompt。 |
| **browser_evaluate** | 在頁面執行 JavaScript。 |
| **browser_run_code** | 執行 Playwright 程式碼片段。 |
| **browser_take_screenshot** | 截圖。 |
| **browser_console_messages** | 取得主控台訊息。 |
| **browser_network_requests** | 列出網路請求。 |
| **browser_file_upload** | 上傳檔案。 |
| **browser_close** | 關閉頁面。 |

**在對話中可這樣呼叫**：  
「請用 Playwright 打開 http://localhost:8000/admin 並擷取 snapshot。」  
「請用 browser_navigate 打開 https://brain.zhe-wei.net/health。」

---

### 3. GitHub MCP（`github`）

**啟動**：`npx -y @modelcontextprotocol/server-github`。  
**依賴**：Node.js；需設定 `GITHUB_PERSONAL_ACCESS_TOKEN`（勿寫入 mcp.json、勿提交）。

常見可呼叫工具（依官方 server 實作為準）：  
**get_file**、**search_code**、**create_branch**、**create_pull_request**、**list_pull_requests**、**list_issues**、**read_file**、**edit_file**、**push_files** 等與 Repo／Issue／PR 相關操作。

**在對話中可這樣呼叫**：  
「請用 GitHub MCP 把目前變更 push 到遠端。」  
「請用 GitHub MCP 列出 open PR 並 merge 最新一筆。」

---

### 4. cursor-ide-browser（Cursor 內建）

**說明**：Cursor 內建瀏覽器 MCP，不需寫入 `.cursor/mcp.json`。  
**常見工具**：`browser_navigate`、`browser_snapshot`、`browser_click`、`browser_type`、`browser_tabs`、`browser_lock`／`browser_unlock` 等（以 Cursor 實際提供為準）。

**在對話中可這樣呼叫**：  
「請用瀏覽器打開 http://localhost:8000/admin 並擷取畫面。」  
「請用 cursor-ide-browser 導覽到 Railway 並檢查部署狀態。」

---

## 三、速查：依用途選 MCP

| 用途 | 建議 MCP | 可呼叫工具範例 |
|------|----------|----------------|
| 本機跑腳本、PowerShell | Windows-MCP | **Shell** |
| 擷取螢幕、開 App、鍵鼠 | Windows-MCP | **Snapshot**、**App**、**Click**、**Type** |
| 打開網頁、填表、點擊 | Playwright 或 cursor-ide-browser | **browser_navigate**、**browser_snapshot**、**browser_click**、**browser_fill_form** |
| 推代碼、PR、Issue | GitHub MCP | **push_files**、**create_pull_request**、**list_pull_requests** 等 |

---

## 四、驗證工具是否可呼叫

1. 在 Composer 輸入：「請用 Windows-MCP 的 Shell 執行 `echo hello`。」  
2. 或：「請用 Playwright 打開 http://localhost:8000/health 並擷取 snapshot。」  
3. 若 Cursor 彈出工具呼叫與參數並詢問是否執行，表示該 MCP 工具可被呼叫。

若某伺服器未出現在 MCP 列表或工具為空，請檢查：  
- `.cursor/mcp.json` 是否正確、  
- 本機是否已安裝 uv/Node、  
- 是否已重載 Cursor 視窗。

---

## 五、在 Cursor 裡實際呼叫 MCP 的步驟

**MCP 工具只在 Composer Agent 裡可用**，一般 Chat 不會有 browser_navigate、Windows-MCP Shell 等工具。請依下列步驟操作：

1. **開啟 Composer**：`Ctrl+I`（Windows）或 `Cmd+I`（Mac）。  
2. **選 Agent 模式**：在 Composer 中選擇 Agent（可呼叫 MCP 工具）。  
3. **確認 MCP 已啟用**：**Settings** → **Features** → **MCP**，確認 **playwright**（與 **windows-mcp**、**github**）已啟用且無錯誤。  
4. **在 Composer 輸入指令**，例如：  
   - 「請用 Playwright 打開 http://localhost:8000/admin 並擷取 snapshot。」  
   - 「請用 Windows-MCP 的 Shell 執行 `echo hello`。」  
5. **讓 Agent 執行**：若 Playwright 正常，Agent 會呼叫 `browser_navigate` 與 `browser_snapshot` 並回傳結果；若 Windows-MCP 正常，會呼叫 **Shell** 工具執行指令。

**補充**：  
- 若要用 **Windows-MCP 的 Shell** 跑指令，必須在 **Composer Agent** 裡下指令，Agent 才會真的呼叫 Windows-MCP 的 Shell 工具。  
- 在一般 Chat 裡用 Cursor 的**終端工具**跑 `echo hello`，效果是「在本機執行 echo hello」，但**不是**透過 Windows-MCP。

---

*本清單依專案 `.cursor/mcp.json` 與各 MCP 官方文件彙整；實際工具名稱以 Cursor 設定頁與執行時為準。*

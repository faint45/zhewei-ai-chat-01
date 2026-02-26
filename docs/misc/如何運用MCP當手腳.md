# 築未科技 — 如何運用 MCP 當成手腳

**目的**：在 Cursor 裡，透過 MCP 執行實體動作（跑腳本、推代碼、開瀏覽器、寫日誌），把 MCP 當成你的「手腳」；本說明提供具體運用方式與可下達的指令範例。

---

## 一、什麼叫「MCP 當手腳」

- **手腳**：本地可雙擊或 CLI 執行的腳本（如 `執行_單次任務.bat`、`run_workflow_step.py`）加上 **在 Cursor 對話中由 AI 透過 MCP 工具代你執行的動作**。
- **MCP 當手腳**：你在 Cursor 裡用自然語言下指令，AI 會呼叫對應的 MCP 工具（例如 Windows-MCP 跑 PowerShell、GitHub MCP 推代碼、Playwright 登入後台、Filesystem 寫日誌），等同於你親手操作鍵鼠、終端、瀏覽器與檔案。

先安裝並啟用對應 MCP（見 **可以符合的Win_MCP清單.md**），之後在對話中即可用下列方式運用。

---

## 二、Windows-MCP：當成「本地手腳」

**負責的實體動作**：啟動 Python 腳本、執行 PowerShell、擷取螢幕、打開影像目錄供 YOLOv8、操作本機 App。

### 2.1 啟動本地 Python 腳本（階段 3、4）

在 Cursor 對話中可這樣下指令，讓 AI 透過 Windows-MCP 代你執行：

- 「請用 Windows-MCP 在 D:\brain_workspace 執行 `python vision_worker.py`，傳入一張 input 目錄裡的圖片路徑。」
- 「請用 PowerShell 執行：`cd D:\brain_workspace; python scripts\run_workflow_step.py --step 視覺與報表 --input D:\brain_workspace\input`。」
- 「請啟動本地腳本：`python brain_server.py`，工作目錄設為專案根目錄。」

AI 會透過 Windows-MCP 的 **執行命令／PowerShell** 類工具在本地跑上述指令，等同你親自在終端執行。

### 2.2 打開影像目錄、擷取螢幕（階段 3、視覺處理）

- 「請打開 D:\brain_workspace\input 資料夾，讓 YOLOv8 可以讀取裡面的圖片。」
- 「請擷取目前螢幕畫面並存到 D:\brain_workspace\input\capture.png。」

AI 會用 Windows-MCP 的 **開資料夾／截圖** 等工具完成，供後續視覺辨識或計畫產出使用。

### 2.3 運用要點

- 路徑一律用 **D 槽或 Z 槽**（如 `D:\brain_workspace\...`、`Z:\Zhewei_Brain\...`），與架構守則一致。
- 若 MCP 需「工作目錄」參數，指定為 `D:\brain_workspace` 或專案根目錄即可。

---

## 三、GitHub MCP：當成「版控手腳」

**負責的實體動作**：把修正後的代碼推送到遠端 Repo（階段 4、6）。

### 3.1 推送修正後的代碼（階段 4 執行、階段 6 回饋修正）

在 Cursor 對話中可這樣下指令：

- 「請用 GitHub MCP 把目前專案的變更 commit 並 push 到遠端 Repo。」
- 「請用 GitHub 建立一個 PR：把 fix/xxx 分支的修正合併到 main，標題寫『階段 6 回饋修正』。」
- 「請列出目前 Repo 的 open PR，並把最新一個 merge。」

AI 會透過 GitHub MCP 的 **git 操作／PR／push** 等工具代你完成版控，等同你在本機或網頁做 commit、push、PR。

### 3.2 運用要點

- 需先在 Cursor 的 MCP 設定中正確配置 GitHub MCP（含認證）；Repo 需已 clone 到本機（路徑可在 D 槽）。
- 代碼產出若在 `D:\brain_workspace` 或專案目錄，可先由 Windows-MCP 或本機 git 同步到 Repo 目錄，再由 GitHub MCP 推送。

---

## 四、Playwright MCP：當成「部署／上架手腳」

**負責的實體動作**：自動登入雲端控制台、微信小程式開發工具進行上架（階段 8）。

### 4.1 登入雲端控制台或小程式上架（階段 8 完成與佈署）

在 Cursor 對話中可這樣下指令：

- 「請用 Playwright 打開雲端控制台登入頁，填入帳密並登入，然後到『上架』頁面點擊發布。」
- 「請用 Playwright 打開微信小程式開發工具，登入後對當前專案執行『上傳』並填寫版本號。」

AI 會透過 Playwright MCP 的 **瀏覽器導覽／填表／點擊** 等工具代你完成登入與上架步驟。

### 4.2 運用要點

- 帳密或敏感資訊勿寫在對話裡，可請 AI 使用環境變數或「請在本地提示我輸入」方式處理。
- 若網頁有驗證碼或 2FA，可說明「我會手動完成驗證，你負責後續點擊與填表」。

---

## 五、Filesystem MCP：當成「監控／日誌手腳」

**負責的實體動作**：把監控日誌實時寫入 Z 槽的 cache 目錄（階段 8）；若資料都放 D 槽則寫入 `D:\brain_workspace\cache`。

### 5.1 寫入監控日誌到 Z 槽 cache（階段 8 監控）

在 Cursor 對話中可這樣下指令：

- 「請用 Filesystem 在 Z:\Zhewei_Brain\cache 建立今日的監控日誌檔，寫入一筆：時間、服務名稱、狀態為運行中。」
- 「若 Z 槽不存在，請改寫到 D:\brain_workspace\cache\monitor.log，內容同上。」

AI 會透過 Filesystem MCP 的 **寫入檔案／列目錄** 等工具代你寫入日誌；路徑需限制在 D 或 Z（MCP 設定時可限制）。

### 5.2 運用要點

- 路徑限 **D 槽或 Z 槽**；若使用「資料都放 D 槽」，則統一用 `D:\brain_workspace\cache`、`D:\brain_workspace\Reports`。
- 進度或數值若需呈現在報表，使用 LaTeX 格式（如 `$100\%$`）。

---

## 六、依八階段「怎麼下指令」速查

| 階段 | 名稱 | 可下的指令範例（讓 AI 用 MCP 當手腳） |
|------|------|----------------------------------------|
| **3** | 安排 | 「用 Windows-MCP 打開 D:\brain_workspace\input 並擷取一張畫面存到 input 目錄。」 |
| **4** | 執行 | 「用 Windows-MCP 在 D:\brain_workspace 執行 `python run_workflow_step.py --step 運算 --input D:\brain_workspace\input`。」「用 GitHub MCP 把目前變更 push 到遠端。」 |
| **6** | 回饋修正 | 「用 GitHub MCP 把 fix 分支 push 並開 PR 合併到 main。」 |
| **8** | 完成與佈署 | 「用 Playwright 登入雲端控制台並執行發布。」「用 Filesystem 在 Z:\Zhewei_Brain\cache 寫入一筆監控日誌。」 |

階段 1、2、5、7 由 AgentManager／Gemini／Ollama 與 TOOLS 處理，不需 MCP 當手腳；若要「手動觸發」本地腳本，仍可用 Windows-MCP 執行 `run_workflow_step.py` 或雙擊 bat。

---

## 七、與現有本地手腳的關係

| 方式 | 誰執行 | 何時用 |
|------|--------|--------|
| **雙擊 bat / CLI run_workflow_step.py** | 你本機手動 | 不需開 Cursor，直接跑單次任務、視覺與報表 |
| **MCP 當手腳** | AI 在 Cursor 對話中呼叫 MCP 工具 | 在對話裡用自然語言請 AI 跑腳本、推代碼、登入後台、寫日誌 |

兩者並存：本地手腳負責「雙擊即跑」的固定流程；MCP 當手腳負責「在對話中隨指令執行」的實體動作。路徑與格式依架構守則（D/Z、LaTeX 進度）。

---

*實作時請遵守架構守則與路徑 D/Z 限制；MCP 安裝與設定見 **可以符合的Win_MCP清單.md**。*

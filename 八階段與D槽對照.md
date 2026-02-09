# 築未科技 — 八階段與 D 槽對照（搜尋結果）

**說明**：D 槽裡「八階段」所提的路徑與目錄整理；八階段定義全文見 **需求到完成八階段流程.md**（專案內）。

---

## 一、D 槽裡八階段「提」的目錄與用途

八階段工作流在 D 槽的落地處為 **D:\brain_workspace**，各階段對應目錄如下：

| 階段 | 名稱 | D 槽路徑／用途 |
|------|------|----------------|
| **1** | 需求 | brain_server 接收指令；無固定 D 槽目錄。 |
| **2** | 整合理解 | 記憶從 Z 槽載入；必要時 Rules 可放 `D:\brain_workspace\Rules`。 |
| **3** | 安排 | 計畫產出；影像輸入可來自 `D:\brain_workspace\input`。 |
| **4** | 執行 | **D:\brain_workspace** 為主產出根目錄；Draft／編碼落 `D:\brain_workspace` 或 `D:\brain_workspace\development`；視覺輸入 `input\`、輸出 `processed\`、模型 `models\`。 |
| **5** | 確認 I | 檢核結果、Log 可寫 `D:\brain_workspace` 或 Z 槽。 |
| **6** | 回饋修正 | Fix 覆蓋或新檔落 `D:\brain_workspace`、`development\`、`tasks\`。 |
| **7** | 確認 II | 交叉驗證無固定目錄；產出仍以 D 槽為準。 |
| **8** | 完成與佈署 | 報表可寫 `D:\brain_workspace\reports` 或 Z 槽；監控日誌可寫 `D:\brain_workspace\cache`（若資料都放 D 槽）。 |

---

## 二、D:\brain_workspace 目前結構（搜尋結果）

依目前 D 槽實際目錄，與八階段相關的結構如下：

| 目錄／檔案 | 八階段對應 | 說明 |
|------------|------------|------|
| **input\** | 階段 3、4 | 待辨識影像、暫存輸入。 |
| **processed\** | 階段 4、5 | 已處理影像。 |
| **models\** | 階段 3、4 | YOLOv8 權重（如 best.pt）。 |
| **output\** | 階段 4、8 | 主腦輸出、媒體產出。 |
| **reports\** | 階段 8 | 本地報表（.md）。 |
| **Zhewei_Brain\Reports\** | 階段 8 | 任務報表（.json）；若 Z 槽未掛載可當 D 槽 Reports。 |
| **tasks\** | 階段 4、6 | 任務 JSON。 |
| **development\** | 階段 4、6 | 開發中腳本與執行紀錄。 |
| **brain_server.py, agent_logic.py, agent_tools.py, ...** | 全階段 | 主腦與 TOOLS 執行實體。 |
| **vision_worker.py, report_tools.py, site_monitor.py** | 階段 3、4、8 | 視覺、報表、監控。 |
| **venv_vision\** | 階段 3、4 | 視覺辨識用 Python 環境。 |

---

## 三、八階段定義文件位置

- **完整八階段定義**：專案內 **需求到完成八階段流程.md**（`c:\Users\user\Desktop\zhe-wei-tech\`）。
- **D 槽**：目前未發現同名「需求到完成八階段流程」檔案；D:\brain_workspace 內有 **EXECUTION_PROTOCOL.md**、**SOP.md**、**STORAGE_POLICY.md**（儲存與執行協定），與八階段互補。
- 若要在 D 槽保留八階段對照，可將本檔或 **築未科技_八階段與MCP合併完整資料.md** 複製到 `D:\brain_workspace\`。

---

## 四、D 槽其他與「階段」相關的專案

搜尋結果：

- **D:\zhewei-tech**：多個 .md 提到「階段」（第一階段、第二階段、送審階段、階段管理等），屬該專案自己的開發／送審階段，**非**築未大腦的「需求到完成八階段」。
- **D:\zhewei_brain_data**：未搜到「八階段」關鍵字。
- **D:\zhe-wei-tech**：未搜到「八階段」關鍵字。

---

*本對照依目前 D 槽目錄與專案內八階段文件整理；路徑請遵守架構守則（D/Z）。*

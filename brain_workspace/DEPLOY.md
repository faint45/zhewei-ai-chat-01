# 築未科技 — D:\brain_workspace 全系統部署說明

## 路徑對齊

- **主腦與視覺根目錄**：`D:\brain_workspace`
- **雲端報表**：`Z:\Zhewei_Brain`（Google 雲端掛載 Z 槽）；若**資料都放 D 槽**則設 `ZHEWEI_MEMORY_ROOT=D:\brain_workspace`，報表與 cache 會寫入 `D:\brain_workspace\Reports`、`D:\brain_workspace\cache`。
- **目錄**：`input`（待辨識影像）、`processed`（已處理）、`models`（YOLOv8 權重，如 `best.pt`）、`output`、`cache`、`Reports`、`Rules`、`Contract`。

## 一鍵部署（資料都放在 D 槽）

於專案根目錄雙擊 **一鍵部屬到D槽.bat**，或執行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy_to_d_drive.ps1
```

腳本會：建立 `D:\brain_workspace` 及子目錄（input、processed、models、output、cache、Reports、Rules、Contract、static）、同步 `brain_workspace` 與主腦核心腳本至 D 槽、建立 `venv_vision` 並安裝 ultralytics/torch、在專案根目錄寫入或追加 `.env`（`BRAIN_WORKSPACE`、`ZHEWEI_MEMORY_ROOT` 指向 `D:\brain_workspace`）。之後報表與監控日誌皆寫入 D 槽。

## 手動部署步驟

1. **將本 brain_workspace 複製到 D 槽**
   - 複製整個 `brain_workspace` 至 `D:\brain_workspace`，或於 `D:\brain_workspace` 建立 `input`、`processed`、`models`，並放入 `vision_worker.py`、`report_tools.py`、`site_monitor.py`、`start_all.ps1`。

2. **建立 Python 3.12 虛擬環境（視覺用）**
   ```powershell
   cd D:\brain_workspace
   py -3.12 -m venv venv_vision
   .\venv_vision\Scripts\activate
   pip install ultralytics torch
   ```

3. **主腦 brain_server（Python 3.14 或預設）**
   - 可將專案根目錄的 `brain_server.py`、`agent_logic.py`、`ai_service.py`、`agent_tools.py` 等一併複製到 `D:\brain_workspace`，或從專案根目錄執行 `python brain_server.py`（端口 8000）。

4. **啟動全系統**
   ```powershell
   cd D:\brain_workspace
   .\start_all.ps1
   ```
   - 會同步啟動 brain_server.py 與 site_monitor.py；按任意鍵結束。

## 環境變數（可選）

- `BRAIN_WORKSPACE`：覆寫視覺引擎根目錄（預設 `D:\brain_workspace`）
- `ZHEWEI_MEMORY_ROOT`：覆寫報表與長期記憶根目錄（預設 `Z:\Zhewei_Brain`）。**資料都放 D 槽**時設為 `D:\brain_workspace`，Reports、cache 會寫入 D 槽。

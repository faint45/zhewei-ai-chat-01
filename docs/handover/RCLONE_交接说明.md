# Rclone 掛載 Google Drive（Z 槽）— 辦理情況與交接說明

**對象**：整合 AI / 後續接手者  
**日期**：2026/02/04  
**專案**：築未科技 zhe-wei-tech，將 4TB Google Drive 掛載為 Windows Z 槽

---

## 一、目前辦理情況（已完成）

### 1. 環境安裝
| 項目 | 狀態 | 說明 |
|------|------|------|
| rclone | ✅ 已安裝 | 路徑：`C:\tools\rclone\rclone.exe`，已加入使用者 PATH |
| WinFsp | ✅ 已安裝 | 掛載磁碟機必要，已以 MSI 安裝 |
| gdrive 遠端 | ✅ 已設定 | 使用者已完成 OAuth，`rclone listremotes` 可看到 `gdrive:` |

### 2. 本專案已建立的檔案（zhe-wei-tech 目錄下）
| 檔案 | 用途 |
|------|------|
| `挂载 Google Drive 为 Z 槽.bat` | 以**管理員**執行後掛載 gdrive 為 Z:，須保持視窗開啟 |
| `卸载 Google Drive.bat` | 卸載 Z 槽（net use / taskkill rclone） |
| `test_rclone_mount.bat` | 測試 rclone 版本、gdrive 連線、Z 槽讀寫、同步乾跑 |
| `設定 gdrive 遠端.bat` | 啟動 `rclone config`，供重新設定或新增遠端用 |
| `安装 Rclone 開機任務.bat` | 用 **schtasks** 建立「登入時自動掛載 Z 槽」排程（需管理員） |
| `卸载 Rclone 開機任務.bat` | 移除上述開機掛載排程 |
| `安装 Rclone 服务.bat` | 用 NSSM 建立 Windows 服務（依賴 NSSM，目前 nssm.cc 503 無法下載，未使用） |
| `卸载 Rclone 服务.bat` | 移除 NSSM 服務用 |
| `RCLONE_USAGE.md` | 使用說明：快速開始、常用操作、排錯 |
| `RCLONE_CONFIG_NOTES.md` | 給 Cursor/開發者的配置注意事項與禁止事項 |
| `RCLONE_交接說明.md` | 本交接文件 |

### 3. 掛載參數（已寫入腳本）
- `--vfs-cache-mode full`（必要）
- `--no-modtime`、`--dir-cache-time 1h`、`--vfs-cache-max-size 10G`
- `--no-checksum`、`--links`（解決 Google Drive 根目錄 symlink 錯誤）
- 已移除 `--allow-non-empty`（Windows 無效）

### 4. 腳本顯示文字修正
- 曾發生 CMD 將 `[檢查 1/5]`、`--- 資訊 ---`、雙引號內文誤判為指令。
- 已改為無方括號、無斜線、無雙引號包住的純文字（例如「檢查步驟 1 of 5」「資訊」「提示：」），避免再觸發錯誤。

### 5. 版本與路徑
- rclone：v1.73.0，位置 `C:\tools\rclone\rclone.exe`
- 設定檔（Windows 預設）：`C:\Users\user\AppData\Roaming\rclone\rclone.conf`（勿提交 Git）
- `.gitignore` 已加入 `.config/`、`rclone.conf`，避免敏感檔入庫

---

## 二、交接事項（整合 AI 須知）

### 1. 禁止操作（築未科技準則）
- **勿修改**：`website_server.py`、`ai_service.py`、`monitoring_service.py`、`brain_server.py` 及既有 .bat 啟動腳本。
- **勿變更埠**：8000、8001、11434。
- **勿刪除**：`.env`、`cloudbase.json`、資料庫檔。
- **勿提交**：`rclone.conf`、`.config/rclone/` 等含憑證的內容。

### 2. 使用者日常操作
- **手動掛載**：右鍵「挂载 Google Drive 为 Z 槽.bat」→ 以系統管理員身分執行，保持視窗開啟。
- **卸載**：執行「卸载 Google Drive.bat」或關閉掛載視窗。
- **開機自動掛載**：右鍵「安装 Rclone 開機任務.bat」→ 以系統管理員身分執行（使用 schtasks，不依賴 NSSM）。
- **取消開機掛載**：執行「卸载 Rclone 開機任務.bat」。

### 3. 驗收狀態
- Z 槽可掛載並存取（掛載腳本執行後會出現「The service rclone has been started」）。
- `rclone listremotes` 顯示 `gdrive:`。
- `rclone about gdrive:` 可看到約 5 TiB 總量、約 4 TiB 可用。
- 開機自動掛載採「工作排程」方式，NSSM 方案因官網 503 暫未啟用。

### 4. 若需進一步自動化（給整合 AI）
- 開機掛載目前為「登入時執行」的 schtasks 任務 `RcloneMountGDrive`；若要改為「開機即掛載（未登入也掛載）」需改用 Windows 服務，並需 NSSM 或等效工具（目前 nssm.cc 不可用可註記，待恢復後再評估）。
- 所有 Rclone 相關邏輯均未改動既有網站/API/監控服務，僅新增/修改本說明所列之 .bat 與 .md。

### 5. 相關文件路徑（供整合 AI 讀取）
- 使用說明：`RCLONE_USAGE.md`
- 配置與禁止事項：`RCLONE_CONFIG_NOTES.md`
- 本交接：`RCLONE_交接說明.md`

---

## 三、一句話摘要（可貼給整合 AI）

「Rclone 與 WinFsp 已安裝，gdrive 已設定並可掛載為 Z 槽；專案內含掛載/卸載/測試/開機任務等 .bat 與 RCLONE_*.md 說明；開機自動掛載以 schtasks 實作；未改動既有服務與埠；詳細禁止事項與路徑見 RCLONE_交接說明.md。」

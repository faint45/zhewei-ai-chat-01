# Rclone 配置注意事項（給 Cursor 的說明）

## 📋 專案目標

將 4TB Google Drive 掛載為 Windows 本地的 **Z 槽**，實現：
- 本地檔案存取（如 `Z:\` 磁碟代號）
- 自動同步檔案到雲端
- 遠端存取 4TB 儲存空間

---

## ⚠️ 關鍵注意事項（必讀）

### 🔴 1. 不要重複安裝依賴

- 專案可能已有 `winfsp` 與 `rclone` 相關工具
- 不要重新下載這些工具，優先使用系統既有 rclone

**檢查方式：**
```powershell
rclone version
```

### 🔴 2. Google Drive 授權

- Rclone 會透過瀏覽器完成 Google OAuth 授權
- **務必使用與 4TB Google Drive 相同的帳號**

**授權後產生：**
- 設定檔：`C:\Users\<使用者名稱>\.config\rclone\rclone.conf`
- **勿將此檔提交至 Git**

### 🔴 3. 掛載權限

- 掛載 Z 槽需**管理員權限**
- 掛載腳本需「以系統管理員身分執行」

### 🔴 4. 效能參數（本專案已採用）

| 參數 | 說明 |
|------|------|
| `--vfs-cache-mode full` | 完整快取，避免檔案損壞，**必須** |
| `--no-modtime` | 關閉修改時間檢查，提升效能 |
| `--dir-cache-time 1h` | 目錄快取 1 小時 |
| `--vfs-cache-max-size 10G` | 本機快取上限 10GB |

### 🔴 5. 不破壞現有服務

- 不修改：`website_server.py`、`ai_service.py`、`monitoring_service.py`、`brain_server.py`
- 不變更埠：8000、8001、11434

---

## 📝 本專案已建立的檔案

| 檔案 | 用途 |
|------|------|
| `挂载 Google Drive 为 Z 槽.bat` | 以管理員掛載 gdrive 為 Z: |
| `卸载 Google Drive.bat` | 卸載 Z 槽（net use / taskkill） |
| `test_rclone_mount.bat` | 測試 rclone、gdrive、Z 槽讀寫與同步 |
| `RCLONE_USAGE.md` | 使用指南（快速開始、操作、排錯） |
| `安装 Rclone 服务.bat` | 使用 NSSM 建立開機自動掛載服務 |
| `卸载 Rclone 服务.bat` | 移除 RcloneMount 服務 |

---

## 🚫 禁止操作

- 不修改現有服務程式與埠
- 不刪除 `.env`、`cloudbase.json`、資料庫檔
- 不將 `.config/rclone/`、`rclone.conf` 提交至 Git（已加入 `.gitignore`）

---

## 📚 參考

- Rclone：<https://rclone.org/>
- Google Drive 遠端：<https://rclone.org/drive/>
- 掛載指令：<https://rclone.org/commands/rclone_mount/>
- WinFsp：<https://winfsp.dev/rel/>
- NSSM：<https://nssm.cc/download>

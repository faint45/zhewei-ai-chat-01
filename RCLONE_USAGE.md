# 築未科技 — Rclone 使用指南（Google Drive 掛載 Z 槽）

## 快速開始

### 首次使用

1. **安裝 rclone 與 WinFsp**（若尚未安裝）
   - rclone：<https://rclone.org/downloads/>，解壓後將 `rclone.exe` 所在目錄加入系統 PATH。
   - WinFsp：<https://winfsp.dev/rel/>，安裝後才能掛載為磁碟機。

2. **建立 Google Drive 遠端**
   ```powershell
   rclone config
   ```
   - 選 `n`（new remote）
   - Name：`gdrive`
   - Type：選 `drive`（Google Drive）
   - 其餘依提示操作，完成時會開啟瀏覽器做 OAuth，請使用與 4TB Google Drive 相同的帳號授權。
   - 設定檔位置：`C:\Users\<使用者名稱>\.config\rclone\rclone.conf`（勿提交至 Git）。

3. **掛載為 Z 槽**
   - 右鍵「**挂载 Google Drive 为 Z 槽.bat**」→ **以系統管理員身分執行**。
   - 保持該視窗開啟，關閉即卸載。

4. **卸載**
   - 執行「**卸载 Google Drive.bat**」，或關閉掛載腳本視窗。

### 每次開機後

- 直接以**系統管理員身分**執行「挂载 Google Drive 为 Z 槽.bat」即可，無需再跑 `rclone config`。

---

## 常用操作

| 操作       | 方式 |
|------------|------|
| 掛載 Z 槽  | 以管理員執行「挂载 Google Drive 为 Z 槽.bat」 |
| 卸載 Z 槽  | 執行「卸载 Google Drive.bat」或關閉掛載視窗 |
| 測試環境   | 執行「test_rclone_mount.bat」 |
| 檢查空間   | `rclone about gdrive:` |
| 列出根目錄 | `rclone lsd gdrive:` 或 `rclone ls gdrive:` |
| 重新授權   | `rclone config reconnect gdrive:` |

---

## 掛載參數說明（本專案使用）

| 參數 | 說明 |
|------|------|
| `--vfs-cache-mode full` | 完整快取，避免寫入損壞，**必須使用** |
| `--no-modtime` | 不檢查修改時間，減少 API 呼叫 |
| `--dir-cache-time 1h` | 目錄快取 1 小時 |
| `--vfs-cache-max-size 10G` | 本機快取上限 10GB |
| `--no-checksum` | 不做校驗，加快傳輸 |
| `--allow-non-empty` | 允許掛載到已有內容的目錄（Z:） |

---

## 效能優化建議

1. **快取目錄**  
   若希望快取在 SSD，可加參數：  
   `--cache-dir C:\rclone_cache`（需在掛載指令中一併加入）。

2. **API 限流**  
   Google Drive 有每日流量與請求限制，大量傳輸時可加：  
   `--bwlimit 50M` 或 `--transfers 4` 依需求調整。

3. **重試**  
   網路不穩可加：  
   `--retries 3 --low-level-retries 10`。

---

## 故障排查

### Z 槽看不到或無法存取

- 確認已**以系統管理員身分**執行掛載腳本。
- 確認 WinFsp 已安裝。
- 執行「test_rclone_mount.bat」檢查 rclone 與 gdrive 連線。

### 找不到 rclone

- 確認已安裝 rclone 且安裝目錄已加入系統 **PATH**。
- 在「命令提示字元」或 PowerShell 執行 `rclone version` 應能看到版本。

### gdrive 連線失敗 / 未授權

- 執行：`rclone config reconnect gdrive:` 重新授權。
- 確認 `C:\Users\<使用者>\.config\rclone\rclone.conf` 存在且未遭刪除。

### 卸載後 Z 槽仍存在

- 先執行「卸载 Google Drive.bat」。
- 若仍存在，關閉「挂载 Google Drive 为 Z 槽.bat」的視窗，或重新開機。

### 寫入很慢或卡頓

- 確認使用 `--vfs-cache-mode full`（本專案腳本已包含）。
- 可將 `--vfs-cache-max-size` 調大（例如 20G），前提是本機磁碟空間足夠。

---

## 注意事項

- **勿提交敏感檔**：`.config\rclone\`、`rclone.conf` 勿加入 Git。
- **掛載視窗**：執行掛載後請勿關閉該 CMD 視窗，關閉即卸載。
- **現有服務**：本腳本不修改 `website_server.py`、`ai_service.py`、`monitoring_service.py` 及埠 8000、8001、11434。

---

## 參考

- Rclone 官網：<https://rclone.org/>
- Google Drive 遠端說明：<https://rclone.org/drive/>
- 掛載指令說明：<https://rclone.org/commands/rclone_mount/>

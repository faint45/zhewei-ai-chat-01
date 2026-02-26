@echo off
chcp 65001 >nul
title 築未科技 - 設定 Rclone 連接 Backblaze B2

where rclone >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 請先安裝 rclone：https://rclone.org/downloads/
    pause
    exit /b 1
)

echo ============================================================
echo 築未科技 - Backblaze B2 Rclone 設定
echo ============================================================
echo.
echo 步驟 1：前往 https://www.backblaze.com/b2/cloud-storage.html
echo         註冊帳號（免費 10GB）
echo.
echo 步驟 2：登入後 → B2 Cloud Storage → App Keys
echo         建立 Application Key，取得：
echo         - keyID（Application Key ID）
echo         - applicationKey（Application Key）
echo.
echo 步驟 3：建立 Bucket（如 zhewei-brain-backup）
echo.
echo 步驟 4：執行 rclone config，依提示輸入：
echo         n) New remote
echo         name> b2
echo         Storage> b2
echo         account> [貼上 keyID]
echo         key> [貼上 applicationKey]
echo.
pause

rclone config

echo.
echo 設定完成後，可用以下指令測試：
echo   rclone lsd b2:
echo   rclone mkdir b2:zhewei-brain-backup
echo.
pause

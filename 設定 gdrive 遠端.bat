@echo off
chcp 65001 >nul
title 築未科技 - 設定 gdrive 遠端（Google Drive）

echo ============================================================
echo 築未科技 - rclone 設定 gdrive（Google Drive）
echo ============================================================
echo.
echo 請依下列步驟操作：
echo   1. 選 n （new remote）
echo   2. name^> 輸入：gdrive
echo   3. Storage^> 選 drive （Google Drive）
echo   4. 其餘選項可直接按 Enter 使用預設
echo   5. 會開啟瀏覽器，請用「4TB Google Drive 的帳號」登入並授權
echo.
echo ============================================================
echo.

set "RCLONE_EXE=C:\tools\rclone\rclone.exe"
if not exist "%RCLONE_EXE%" (
    echo [錯誤] 找不到 %RCLONE_EXE%
    echo 若 rclone 已安裝在其他位置，請改為執行：rclone config
    pause
    exit /b 1
)

"%RCLONE_EXE%" config
pause

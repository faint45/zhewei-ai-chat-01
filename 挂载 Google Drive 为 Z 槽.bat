@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title 築未科技 - 掛載 Google Drive 為 Z 槽

echo ============================================================
echo 築未科技 - 掛載 Google Drive 為 Z 槽
echo ============================================================
echo.

:: 檢查管理員權限（掛載 Z 槽需要）
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 錯誤：請以「以系統管理員身分執行」此腳本。
    echo 右鍵本檔案 ^> 以系統管理員身分執行
    pause
    exit /b 1
)

:: 檢查 1 of 5
echo 檢查步驟 1 of 5：Z 槽狀態...
if exist Z:\ (
    echo Z 槽已存在。若為先前掛載，請先執行「卸載 Google Drive.bat」後再掛載。
    set "ZEXIST=1"
) else (
    set "ZEXIST=0"
    echo Z 槽未佔用，可掛載。
)
echo.

:: 檢查 2 of 5
echo 檢查步驟 2 of 5：rclone 安裝...
where rclone >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 錯誤：找不到 rclone，請先安裝並加入 PATH。
    echo 下載：https://rclone.org/downloads/
    pause
    exit /b 1
)
rclone version
echo.

:: 檢查 3 of 5
echo 檢查步驟 3 of 5：Google Drive 連線...
rclone listremotes | findstr /C:"gdrive:" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 錯誤：未找到遠端 gdrive，請先執行 rclone config
    echo 建立名稱為 gdrive 的 Google Drive 遠端。
    pause
    exit /b 1
)

rclone lsd gdrive: --max-depth 1 >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 錯誤：無法連線至 gdrive，請檢查網路與 OAuth 授權。
    echo 可執行：rclone config reconnect gdrive:
    pause
    exit /b 1
)
echo gdrive 連線正常。
echo.

:: 顯示儲存空間（掛載前）
echo 資訊
echo   掛載點: Z:\
echo   遠端: gdrive (Google Drive)
rclone about gdrive: 2>nul
echo.

:: [檢查 4/5] 若 Z 已存在則詢問
if "%ZEXIST%"=="1" (
    set /p "REPLY=是否仍要嘗試掛載並覆蓋 Z 槽？(y/N): "
    if /i not "!REPLY!"=="y" (
        echo 已取消。
        pause
        exit /b 0
    )
)

:: 檢查 5 of 5
echo 檢查步驟 5 of 5：準備掛載...
echo.

echo 掛載中：正在掛載到 Z:...
echo.
echo 提示：
echo   - 保持此視窗開啟以維持掛載
echo   - 按 Ctrl+C 或關閉視窗可卸載
echo   - 檔案會自動同步到雲端
echo.

rclone mount gdrive: Z: ^
  --vfs-cache-mode full ^
  --no-modtime ^
  --dir-cache-time 1h ^
  --vfs-cache-max-size 10G ^
  --no-checksum ^
  --links

:: 掛載結束（使用者關閉或 Ctrl+C）
echo.
echo 已卸載 Z:。
pause

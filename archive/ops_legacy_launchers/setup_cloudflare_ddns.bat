@echo off
chcp 65001 >nul
title 設定 Cloudflare DDNS 自動更新

echo.
echo ════════════════════════════════════════════════════
echo   設定 Cloudflare DDNS 每 5 分鐘自動更新
echo ════════════════════════════════════════════════════
echo.

:: 檢查是否以管理員權限運行
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 需要管理員權限
    echo.
    echo 請右鍵此文件，選擇「以管理員身分執行」
    echo.
    pause
    exit /b 1
)

echo [1/5] 配置環境變數...
set TASK_NAME=Cloudflare DDNS 每5分鐘更新
set SCRIPT_PATH=%~dp0cloudflare_ddns_update.ps1

echo 任務名稱: %TASK_NAME%
echo 腳本路徑: %SCRIPT_PATH%
echo.

echo [2/5] 設定系統環境變數...
setx CLOUDFLARE_ZONE_ID "8ba45d8905b38792b061bdcadac6dd39" /M >nul 2>&1
setx CLOUDFLARE_API_TOKEN "JS6dXN0-fQ4efSgUbunBTBMYM83bZKPND6872Rrc" /M >nul 2>&1
setx CLOUDFLARE_DOMAIN "zhe-wei.net" /M >nul 2>&1
echo ✅ 環境變數已設定
echo.

echo [3/5] 刪除舊任務（如果存在）...
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 舊任務已刪除
) else (
    echo ℹ️  沒有舊任務需要刪除
)
echo.

echo [4/5] 建立工作排程器任務...
schtasks /Create /TN "%TASK_NAME%" ^
    /TR "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File \"%SCRIPT_PATH%\"" ^
    /SC DAILY /ST 00:00 ^
    /RU "%USERNAME%" ^
    /F >nul 2>&1

if %errorlevel% neq 0 (
    echo ❌ 工作排程器任務創建失敗
    pause
    exit /b 1
)

echo ✅ 基本任務已創建
echo.

echo [5/5] 設定重複執行（每 5 分鐘）...
schtasks /Change /TN "%TASK_NAME%" /RI 5 /DU 9999:59 >nul 2>&1

if %errorlevel% neq 0 (
    echo ⚠️  重複執行設定失敗，請手動設定
) else (
    echo ✅ 重複執行已設定（每 5 分鐘）
)
echo.

echo ════════════════════════════════════════════════════
echo ✅ Cloudflare DDNS 自動更新設置完成！
echo.
echo 配置信息：
echo   域名: www.zhe-wei.net
echo   Zone ID: 8ba45d8905b38792b061bdcadac6dd39
echo   更新頻率: 每 5 分鐘
echo.
echo 🌐 訪問地址：
echo   • HTTPS: https://www.zhe-wei.net
echo   • HTTP: http://www.zhe-wei.net
echo.
echo 💡 後續步驟：
echo   1. 測試任務：在「工作排程器」中執行該任務
echo   2. 檢查日誌：%USERPROFILE%\Cloudflare_DDNS_Log.txt
echo   3. 啟動多代理服務：執行 start_multi_agent.bat
echo   4. 設定路由器埠轉發（參考 ROUTER_PORT_FORWARD_GUIDE.md）
echo   5. 在 Cloudflare 設定 SSL/TLS → Flexible
echo.
echo ════════════════════════════════════════════════════
echo.

pause

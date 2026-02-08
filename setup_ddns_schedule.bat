@echo off
chcp 65001 >nul
title 設置 DuckDNS 自動更新排程

echo.
echo ════════════════════════════════════════════════════
echo   設置 DuckDNS 每 5 分鐘自動更新
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

echo [1/4] 配置參數...
set TASK_NAME=DuckDNS 每5分鐘更新
set SCRIPT_PATH=%~dp0run-ddns-with-env.ps1
set LOG_FILE=%USERPROFILE%\DDNS_Update_Log.txt

echo 任務名稱: %TASK_NAME%
echo 腳本路徑: %SCRIPT_PATH%
echo 日誌路徑: %LOG_FILE%
echo.

echo [2/4] 刪除舊任務（如果存在）...
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 舊任務已刪除
) else (
    echo ℹ️  沒有舊任務需要刪除
)
echo.

echo [3/4] 建立工作排程器任務...
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

echo [4/4] 設定重複執行（每 5 分鐘）...
schtasks /Change /TN "%TASK_NAME%" /RI 5 /DU 9999:59 >nul 2>&1

if %errorlevel% neq 0 (
    echo ❌ 重複執行設定失敗
    echo.
    echo 請手動在「工作排程器」中設定：
    echo   1. 開啟工作排程器
    echo   2. 找到任務 "%TASK_NAME%"
    echo   3. 右鍵 → 內容 → 觸發程序 → 編輯
    echo   4. 勾選「重複工作間隔」→ 5 分鐘
    echo   5. 持續時間: 無限期
) else (
    echo ✅ 重複執行已設定（每 5 分鐘）
)
echo.

echo ════════════════════════════════════════════════════
echo ✅ DDNS 自動更新設置完成！
echo.
echo 任務信息：
echo   名稱: %TASK_NAME%
echo   頻率: 每 5 分鐘
echo   腳本: %SCRIPT_PATH%
echo.
echo 💡 後續步驟：
echo   1. 測試任務：在「工作排程器」中右鍵該任務 → 執行
echo   2. 檢查日誌：%LOG_FILE%
echo   3. 啟動多代理服務：執行 start_multi_agent.bat
echo   4. 設定路由器埠轉發
echo   5. （可選）配置 Cloudflare SSL
echo.
echo 📋 詳細配置請查看: SETUP-AFTER-DDNS.md
echo ════════════════════════════════════════════════════
echo.

pause

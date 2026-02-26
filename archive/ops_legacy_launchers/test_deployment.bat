@echo off
chcp 65001 >nul
title 部署完整測試

echo.
echo ════════════════════════════════════════════════════
echo   完整部署測試
echo ════════════════════════════════════════════════════
echo.

cd /d "%~dp0"

echo [測試 1/4] DDNS 自動更新腳本...
echo 執行 PowerShell 腳本...
powershell.exe -ExecutionPolicy Bypass -File "run-ddns-with-env.ps1"
if %errorlevel% equ 0 (
    echo ✅ DDNS 腳本執行成功
) else (
    echo ❌ DDNS 腳本執行失敗
)
echo.

echo [測試 2/4] 檢查工作排程器...
schtasks /Query /TN "DuckDNS 每5分鐘更新" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 工作排程器任務已建立
    schtasks /Query /TN "DuckDNS 每5分鐘更新" /FO LIST | findstr "下次執行時間"
) else (
    echo ⚠️  工作排程器任務未建立
    echo    請執行: setup_ddns_schedule.bat
)
echo.

echo [測試 3/4] 本機服務...
echo 測試 http://localhost:8001 ...
curl -s -o nul -w "HTTP 狀態碼: %%{http_code}\n" http://localhost:8001 --max-time 5
if %errorlevel% equ 0 (
    echo ✅ 本機服務正常
) else (
    echo ⚠️  本機服務未運行或無法訪問
    echo    請執行: start_multi_agent.bat
)
echo.

echo [測試 4/4] 外部訪問...
echo 測試 http://zhuwei-tech.duckdns.org:8001 ...
curl -s -o nul -w "HTTP 狀態碼: %%{http_code}\n" http://zhuwei-tech.duckdns.org:8001 --max-time 10
if %errorlevel% equ 0 (
    echo ✅ 外部訪問正常
) else (
    echo ⚠️  外部訪問失敗
    echo    請檢查：
    echo    • 路由器埠轉發是否正確
    echo    • 防火牆是否允許端口 8001
    echo    • DDNS 是否已更新
)
echo.

echo ════════════════════════════════════════════════════
echo 📋 檢查日誌：
echo   DDNS 日誌: type %USERPROFILE%\DDNS_Update_Log.txt
echo   系統日誌: type system_health_report.json
echo.
echo 💡 快速修復：
echo   1. 設定 DDNS 排程:    setup_ddns_schedule.bat
echo   2. 啟動多代理服務:  start_multi_agent.bat
echo   3. 查看完整指南:    SETUP-AFTER-DDNS.md
echo ════════════════════════════════════════════════════
echo.

pause

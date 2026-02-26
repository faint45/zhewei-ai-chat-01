@echo off
title 築未科技：AI 大腦總指揮部
chcp 65001 > nul
cd /d "%~dp0"

echo [步驟 1/3] 執行安全診斷...
python startup_diagnostics.py
if %errorlevel% neq 0 (
    echo.
    echo ❌ 診斷失敗，請排除 Z 槽或檔案缺失問題！
    pause
    exit /b 1
)

echo.
echo [步驟 2/3] 啟動 WebSocket 伺服器 (Port 8000)...
start "Brain_Server" cmd /k "cd /d "%~dp0" && python brain_server.py"

echo.
echo [步驟 3/3] 啟動工地主動監控系統...
if exist "%~dp0brain_workspace\site_monitor.py" (
    start "Site_Monitor" cmd /k "cd /d "%~dp0brain_workspace" && python site_monitor.py"
) else if exist "D:\brain_workspace\site_monitor.py" (
    start "Site_Monitor" cmd /k "cd /d D:\brain_workspace && python site_monitor.py"
) else (
    echo ⚠️ 未找到 site_monitor.py，跳過工地監控
)

echo.
echo ✨ 築未大腦已完成佈署並上線。
echo 📱 請從 iPhone 使用 Tailscale 連線：100.116.133.23:8000
echo.
pause

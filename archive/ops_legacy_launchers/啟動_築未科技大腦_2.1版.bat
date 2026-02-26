@echo off
title 築未科技：AI 大腦總指揮部 2.1 (自癒模式)
chcp 65001 > nul
cd /d "%~dp0"

echo [步驟 1/4] 環境安全診斷...
python startup_diagnostics.py
if %errorlevel% neq 0 (
    echo.
    echo ❌ 診斷未通過，正在啟動 AI 自動修復補丁...
    python -c "from preflight_check import attempt_z_mount; attempt_z_mount()"
    timeout /t 5 /nobreak > nul
    python startup_diagnostics.py
    if %errorlevel% neq 0 (
        echo ⚠️ 仍未通過，請手動檢查 Z 槽或核心檔案。系統將繼續啟動守護與服務。
    )
)
echo.

echo [步驟 2/4] 啟動自我監控與守護進程...
start "Zhewei_Guardian" /min cmd /k "cd /d "%~dp0" && python guardian_master.py"

echo [步驟 3/4] 啟動 WebSocket 伺服器 (Port 8000)...
start "Brain_Server" cmd /k "cd /d "%~dp0" && python brain_server.py"

echo [步驟 4/4] 啟動邊緣運算監控...
if exist "%~dp0brain_workspace\site_monitor.py" (
    start "Site_Monitor" cmd /k "cd /d "%~dp0brain_workspace" && python site_monitor.py"
) else if exist "D:\brain_workspace\site_monitor.py" (
    start "Site_Monitor" cmd /k "cd /d D:\brain_workspace && python site_monitor.py"
) else (
    echo ⚠️ 未找到 site_monitor.py，跳過邊緣運算監控
)

echo.
echo ✨ 築未科技大腦 2.1 已進入「自我監控與修復」狀態。
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "ROOT=%CD%"
set "MODE=%~1"

REM 無參數或 docker = Docker 模式；local = 本機模式
if "%MODE%"=="" set "MODE=docker"
if /I "%MODE%"=="local" goto local_mode

REM === Docker 模式（對外運營） ===
echo 築未科技大腦 — Docker 啟動
echo.
where docker >nul 2>nul
if errorlevel 1 (
  echo [SKIP] Docker 未安裝，改為本機模式
  goto local_mode
)
docker start zhewei_brain zhe-wei-tech-tunnel-1 zhe-wei-ollama zhewei-qdrant 2>nul
if exist "%ROOT%\scripts\start_runtime_monitor.bat" (
  start "Monitor" /min cmd /c "call \"%ROOT%\scripts\start_runtime_monitor.bat\""
)
if exist "%ROOT%\Jarvis_Training\run_discord_bot_autostart.bat" (
  start "DiscordBot" /min cmd /c "call \"%ROOT%\Jarvis_Training\run_discord_bot_autostart.bat\""
)
echo [OK] Brain: http://127.0.0.1:8002
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8002
goto end

:local_mode
REM === 本機模式（無 Docker） ===
echo 築未科技大腦 — 本機啟動
echo.
python startup_diagnostics.py
if errorlevel 1 (
  echo [ERROR] 診斷未通過
  pause
  exit /b 1
)
start "Brain" cmd /k "python brain_server.py"
if exist "monitoring_dashboard.py" start "Monitor" cmd /k "python monitoring_dashboard.py"
echo [OK] Brain: http://127.0.0.1:8002
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8002

:end
pause

@echo off
REM 築未科技大腦 — 一鍵啟動（依賴+Docker+Monitor+Bot+Ollama）
REM 用法：雙擊執行，或 一鍵啟動.bat [hold=完成後暫停]
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "ROOT=%CD%"
set "KEEP_OPEN=%~1"
set "LOG=%ROOT%\reports\one_click.log"
set "PY=%ROOT%\Jarvis_Training\.venv312\Scripts\python.exe"
set "ENSURE=%ROOT%\scripts\ensure_env_ollama.py"

if not exist "%ROOT%\reports" mkdir "%ROOT%\reports"
echo [%date% %time%] 一鍵啟動開始>> "%LOG%"

echo.
echo ========================================
echo   築未科技大腦 — 一鍵啟動
echo ========================================
echo.

REM === 1. 依賴鎖定 ===
echo [1/6] 安裝鎖定依賴...
if exist "%PY%" (
  if exist "%ROOT%\requirements.lock" (
    "%PY%" -m pip install -r "%ROOT%\requirements.lock" --quiet 2>nul
  ) else if exist "%ROOT%\requirements-brain.lock" (
    "%PY%" -m pip install -r "%ROOT%\requirements-brain.lock" --quiet 2>nul
  )
  if exist "%ROOT%\requirements-voice.txt" (
    echo       (選用) 戰術語音+Graph RAG: whisper, edge-tts, PyMuPDF...
    "%PY%" -m pip install -r "%ROOT%\requirements-voice.txt" --quiet 2>nul
  )
  echo [OK] 依賴就緒
) else (
  echo [WARN] Python venv 未找到，跳過 pip
)

REM === 2. 環境變數 ===
echo [2/6] 檢查 .env...
if not exist "%ROOT%\.env" (
  if exist "%ROOT%\.env.example" (
    copy "%ROOT%\.env.example" "%ROOT%\.env" >nul
    echo [OK] 已從 .env.example 建立 .env
  ) else (
    echo [WARN] 無 .env.example，請手動建立 .env
  )
) else (
  echo [OK] .env 存在
)
if exist "%PY%" if exist "%ENSURE%" (
  "%PY%" "%ENSURE%" >> "%LOG%" 2>&1
)

REM === 3. Docker ===
echo [3/6] 啟動 Docker 容器...
where docker >nul 2>nul
if errorlevel 1 (
  echo [SKIP] Docker 未安裝，跳過容器
  goto skip_docker
)
set /a wait=0
:docker_wait
docker info >nul 2>nul
if not errorlevel 1 goto docker_start
set /a wait+=1
if !wait! GEQ 24 (
  echo [WARN] Docker 未就緒，跳過
  goto skip_docker
)
timeout /t 5 /nobreak >nul
goto docker_wait

:docker_start
docker start zhewei_brain zhe-wei-tech-tunnel-1 zhe-wei-ollama zhewei-qdrant 2>nul
echo [OK] 容器已啟動
goto after_docker

:skip_docker
echo [SKIP] Docker 未安裝或未就緒
:after_docker

REM === 4. Ollama 模型 ===
echo [4/6] 拉取 Ollama 模型...
docker ps --format "{{.Names}}" 2>nul | findstr /x "zhe-wei-ollama" >nul 2>nul
if not errorlevel 1 (
  docker exec zhe-wei-ollama ollama pull qwen2.5-coder:7b 2>nul
  docker exec zhe-wei-ollama ollama pull deepseek-r1:8b 2>nul
  echo [OK] 模型就緒
) else (
  echo [SKIP] Ollama 容器未運行
)

REM === 5. Monitor + Bot ===
echo [5/6] 啟動監控與 Discord Bot...
set "MONITOR_BAT=%ROOT%\scripts\start_runtime_monitor.bat"
set "BOT_BAT=%ROOT%\Jarvis_Training\run_discord_bot_autostart.bat"

if exist "%MONITOR_BAT%" (
  for /f %%I in ('powershell -NoProfile -Command "$h=''; foreach ($p in Get-CimInstance Win32_Process) { if ($p.Name -match 'python' -and $p.CommandLine -match 'monitor_runtime_and_notify') { $h=$p.ProcessId; break } }; $h"') do set "M=%%I"
  if not defined M (
    start "ZheweiMonitor" /min cmd /c "call \"%MONITOR_BAT%\""
    echo [OK] Monitor 已啟動
  ) else (
    echo [OK] Monitor 已在運行
  )
) else (
  echo [WARN] Monitor 腳本不存在
)

if exist "%BOT_BAT%" (
  for /f %%I in ('powershell -NoProfile -Command "$h=''; foreach ($p in Get-CimInstance Win32_Process) { if ($p.Name -match 'cmd' -and $p.CommandLine -match 'run_discord_bot_autostart') { $h=$p.ProcessId; break } }; $h"') do set "B=%%I"
  if not defined B (
    start "ZheweiDiscordBot" /min cmd /c "call \"%BOT_BAT%\""
    echo [OK] Discord Bot 已啟動
  ) else (
    echo [OK] Discord Bot 已在運行
  )
) else (
  echo [WARN] Discord Bot 腳本不存在
)

REM === 6. 完成 ===
echo [6/6] 啟動完成
echo.
echo ========================================
echo   築未科技大腦 已就緒
echo ========================================
echo   Brain: http://127.0.0.1:8002
echo   Agent Hub: http://127.0.0.1:8002/agent-hub
echo   Health: http://127.0.0.1:8002/health-dashboard
echo   Log: %LOG%
echo ========================================
echo.
echo 3 秒後開啟瀏覽器...
timeout /t 3 /nobreak >nul
start http://127.0.0.1:8002
echo.
if /I "%KEEP_OPEN%"=="hold" (
  echo 按任意鍵關閉...
  pause >nul
) else (
  pause
)

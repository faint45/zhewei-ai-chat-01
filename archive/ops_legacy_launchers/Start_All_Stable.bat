@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "KEEP_OPEN=%~1"

set "ROOT=%CD%"
set "LOG=%ROOT%\reports\start_all_stable.log"
set "MONITOR_BAT=%ROOT%\scripts\start_runtime_monitor.bat"
set "BOT_BAT=%ROOT%\Jarvis_Training\run_discord_bot_autostart.bat"
set "PY=%ROOT%\Jarvis_Training\.venv312\Scripts\python.exe"
set "GATE=%ROOT%\scripts\commercial_gate.py"
set "MAX_DOCKER_WAIT=180"

if not exist "%ROOT%\reports" mkdir "%ROOT%\reports"
echo [%date% %time%] [INFO] Start_All_Stable begin>> "%LOG%"

call :warmup_salad_wsl

where docker >nul 2>nul
if errorlevel 1 (
  echo [%date% %time%] [ERROR] docker command not found>> "%LOG%"
  echo [ERROR] docker command not found. Please install/start Docker Desktop.
  if /I "%KEEP_OPEN%"=="hold" (
    echo [INFO] Press any key to close...
    pause >nul
  )
  exit /b 1
)

call :wait_docker_ready
if errorlevel 1 (
  echo [%date% %time%] [ERROR] docker daemon not ready in %MAX_DOCKER_WAIT%s>> "%LOG%"
  echo [ERROR] Docker daemon not ready. Please wait Docker Desktop fully started.
  if /I "%KEEP_OPEN%"=="hold" (
    echo [INFO] Press any key to close...
    pause >nul
  )
  exit /b 1
)

echo [%date% %time%] [INFO] starting core containers>> "%LOG%"
docker start zhewei_brain zhe-wei-tech-tunnel-1 zhe-wei-ollama zhewei-qdrant >> "%LOG%" 2>&1

if not exist "%MONITOR_BAT%" (
  echo [%date% %time%] [ERROR] monitor bat missing: %MONITOR_BAT%>> "%LOG%"
  echo [ERROR] monitor bat not found: %MONITOR_BAT%
  exit /b 1
)
if not exist "%BOT_BAT%" (
  echo [%date% %time%] [ERROR] bot bat missing: %BOT_BAT%>> "%LOG%"
  echo [ERROR] bot bat not found: %BOT_BAT%
  exit /b 1
)

set "MONITOR_RUNNING="
for /f %%I in ('powershell -NoProfile -Command "$hit=''; foreach ($p in Get-CimInstance Win32_Process) { if ($p.Name -match 'python' -and $p.CommandLine -match 'monitor_runtime_and_notify\\.py') { $hit=$p.ProcessId; break } }; $hit"') do set "MONITOR_RUNNING=%%I"
if defined MONITOR_RUNNING (
  echo [%date% %time%] [INFO] monitor already running pid=!MONITOR_RUNNING!>> "%LOG%"
) else (
  echo [%date% %time%] [INFO] launching runtime monitor>> "%LOG%"
  start "ZheweiRuntimeMonitor" /min cmd /c "call \"%MONITOR_BAT%\""
)

set "BOT_WATCHDOG_PID="
for /f %%I in ('powershell -NoProfile -Command "$hit=''; foreach ($p in Get-CimInstance Win32_Process) { if ($p.Name -match 'cmd' -and $p.CommandLine -match 'run_discord_bot_autostart\\.bat') { $hit=$p.ProcessId; break } }; $hit"') do set "BOT_WATCHDOG_PID=%%I"
if defined BOT_WATCHDOG_PID (
  echo [%date% %time%] [INFO] bot watchdog already running pid=!BOT_WATCHDOG_PID!>> "%LOG%"
) else (
  echo [%date% %time%] [INFO] launching discord bot watchdog>> "%LOG%"
  start "ZheweiDiscordBotWatchdog" /min cmd /c "call \"%BOT_BAT%\""
)

echo [%date% %time%] [INFO] Start_All_Stable done>> "%LOG%"
call :wait_commercial_gate
if errorlevel 1 (
  echo [%date% %time%] [ERROR] commercial gate failed>> "%LOG%"
  echo [ERROR] Commercial gate failed. Check logs and health dashboard.
  echo [INFO] Log: %LOG%
  if /I "%KEEP_OPEN%"=="hold" (
    echo [INFO] Press any key to close...
    pause >nul
  )
  exit /b 2
)
echo [OK] Core + monitor + bot launched and passed commercial gate.
echo [INFO] Log: %LOG%
if /I "%KEEP_OPEN%"=="hold" (
  echo [INFO] Press any key to close...
  pause >nul
)
exit /b 0

:wait_docker_ready
set /a waited=0
:wait_loop
docker info >nul 2>nul
if not errorlevel 1 exit /b 0
if !waited! GEQ %MAX_DOCKER_WAIT% exit /b 1
timeout /t 5 /nobreak >nul
set /a waited+=5
goto wait_loop

:wait_commercial_gate
if not exist "%PY%" (
  echo [%date% %time%] [WARN] python missing, skip commercial gate>> "%LOG%"
  exit /b 0
)
if not exist "%GATE%" (
  echo [%date% %time%] [WARN] commercial gate script missing, skip>> "%LOG%"
  exit /b 0
)
set /a gate_try=0
:gate_loop
set /a gate_try+=1
"%PY%" "%GATE%" >> "%LOG%" 2>&1
if not errorlevel 1 (
  echo [%date% %time%] [INFO] commercial gate passed in try=!gate_try!>> "%LOG%"
  exit /b 0
)
if !gate_try! GEQ 12 exit /b 1
timeout /t 10 /nobreak >nul
goto gate_loop

:warmup_salad_wsl
where wsl.exe >nul 2>nul
if errorlevel 1 exit /b 0
set /a try=0
:wsl_try
set /a try+=1
wsl.exe -d salad-enterprise-linux -e sh -c "echo warmup-ok" >nul 2>nul
if errorlevel 1 (
  if !try! GEQ 3 (
    echo [%date% %time%] [WARN] salad-enterprise-linux warmup failed after retries>> "%LOG%"
    exit /b 0
  )
  timeout /t 2 /nobreak >nul
  goto wsl_try
)
wsl.exe -d salad-enterprise-linux -e sh -c "mkdir -p /root/.docker /root/C:Usersuser/.docker; [ -f /root/.docker/config.json ] || echo {} > /root/.docker/config.json; [ -f /root/C:Usersuser/.docker/config.json ] || echo {} > /root/C:Usersuser/.docker/config.json" >nul 2>nul
echo [%date% %time%] [INFO] salad-enterprise-linux warmup ok>> "%LOG%"
exit /b 0


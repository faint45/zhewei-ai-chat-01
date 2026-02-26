@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "ROOT=%CD%"
set "LOG=%ROOT%\reports\boot_health_check.log"
set "CORE_CONTAINERS=zhewei_brain zhe-wei-tech-tunnel-1 zhe-wei-ollama zhewei-qdrant"
set "MONITOR_BAT=%ROOT%\scripts\start_runtime_monitor.bat"
set "BOT_BAT=%ROOT%\Jarvis_Training\run_discord_bot_autostart.bat"
set "MAX_DOCKER_WAIT=180"

if not exist "%ROOT%\reports" mkdir "%ROOT%\reports"
echo [%date% %time%] [INFO] boot health check begin>> "%LOG%"

call :warmup_salad_wsl

call :wait_docker_ready
if errorlevel 1 (
  echo [%date% %time%] [WARN] docker not ready in %MAX_DOCKER_WAIT%s, skip container recovery>> "%LOG%"
) else (
  call :recover_core_containers
)

call :recover_runtime_monitor
call :recover_discord_bot_watchdog

echo [%date% %time%] [INFO] boot health check done>> "%LOG%"
echo [OK] boot health check completed
exit /b 0

:warmup_salad_wsl
where wsl.exe >nul 2>nul
if errorlevel 1 exit /b 0
set /a try=0
:warmup_try
set /a try+=1
wsl.exe -d salad-enterprise-linux -e sh -c "echo warmup-ok" >nul 2>nul
if errorlevel 1 (
  if !try! GEQ 3 (
    echo [%date% %time%] [WARN] WSL warmup failed for salad-enterprise-linux>> "%LOG%"
    exit /b 0
  )
  timeout /t 2 /nobreak >nul
  goto warmup_try
)
wsl.exe -d salad-enterprise-linux -e sh -c "mkdir -p /root/.docker /root/C:Usersuser/.docker; [ -f /root/.docker/config.json ] || echo {} > /root/.docker/config.json; [ -f /root/C:Usersuser/.docker/config.json ] || echo {} > /root/C:Usersuser/.docker/config.json" >nul 2>nul
echo [%date% %time%] [INFO] WSL warmup ok: salad-enterprise-linux>> "%LOG%"
exit /b 0

:wait_docker_ready
where docker >nul 2>nul
if errorlevel 1 exit /b 1
set /a waited=0
:wait_docker_loop
docker info >nul 2>nul
if not errorlevel 1 exit /b 0
if !waited! GEQ %MAX_DOCKER_WAIT% exit /b 1
timeout /t 5 /nobreak >nul
set /a waited+=5
goto wait_docker_loop

:recover_core_containers
for %%C in (%CORE_CONTAINERS%) do (
  docker inspect -f "{{.State.Running}}" %%C 2>nul | findstr /I "true" >nul
  if errorlevel 1 (
    echo [%date% %time%] [INFO] container not running, starting: %%C>> "%LOG%"
    docker start %%C >> "%LOG%" 2>&1
  ) else (
    echo [%date% %time%] [INFO] container healthy running: %%C>> "%LOG%"
  )
)
exit /b 0

:recover_runtime_monitor
if not exist "%MONITOR_BAT%" (
  echo [%date% %time%] [ERROR] monitor bat missing: %MONITOR_BAT%>> "%LOG%"
  exit /b 0
)
set "MONITOR_PID="
for /f %%I in ('powershell -NoProfile -Command "$hit=''; foreach ($p in Get-CimInstance Win32_Process) { if ($p.Name -match 'python' -and $p.CommandLine -match 'monitor_runtime_and_notify\\.py') { $hit=$p.ProcessId; break } }; $hit"') do set "MONITOR_PID=%%I"
if defined MONITOR_PID (
  echo [%date% %time%] [INFO] runtime monitor already running pid=!MONITOR_PID!>> "%LOG%"
) else (
  echo [%date% %time%] [INFO] runtime monitor missing, launching>> "%LOG%"
  start "ZheweiRuntimeMonitor" /min cmd /c "call \"%MONITOR_BAT%\""
)
exit /b 0

:recover_discord_bot_watchdog
if not exist "%BOT_BAT%" (
  echo [%date% %time%] [ERROR] bot bat missing: %BOT_BAT%>> "%LOG%"
  exit /b 0
)
set "BOT_WATCHDOG_PID="
for /f %%I in ('powershell -NoProfile -Command "$hit=''; foreach ($p in Get-CimInstance Win32_Process) { if ($p.Name -match 'cmd' -and $p.CommandLine -match 'run_discord_bot_autostart\\.bat') { $hit=$p.ProcessId; break } }; $hit"') do set "BOT_WATCHDOG_PID=%%I"
if defined BOT_WATCHDOG_PID (
  echo [%date% %time%] [INFO] bot watchdog already running pid=!BOT_WATCHDOG_PID!>> "%LOG%"
) else (
  echo [%date% %time%] [INFO] bot watchdog missing, launching>> "%LOG%"
  start "ZheweiDiscordBotWatchdog" /min cmd /c "call \"%BOT_BAT%\""
)
exit /b 0


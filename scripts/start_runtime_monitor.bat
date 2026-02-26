@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "PY=Jarvis_Training\.venv312\Scripts\python.exe"
set "SCRIPT=scripts\monitor_runtime_and_notify.py"
set "LOG=reports\runtime_monitor.log"
set "INTERVAL=60"

if not exist "%PY%" (
  echo [%date% %time%] [FATAL] python not found: %PY%>> "%LOG%"
  exit /b 1
)
if not exist "%SCRIPT%" (
  echo [%date% %time%] [FATAL] script not found: %SCRIPT%>> "%LOG%"
  exit /b 1
)

echo [%date% %time%] [INFO] runtime monitor started>> "%LOG%"

:loop
"%PY%" "%SCRIPT%" >> "%LOG%" 2>&1
timeout /t %INTERVAL% /nobreak >nul
goto loop

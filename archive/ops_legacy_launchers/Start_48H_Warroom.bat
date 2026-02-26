@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "ROOT=%CD%"
set "PY=%ROOT%\Jarvis_Training\.venv312\Scripts\python.exe"
set "WARROOM=%ROOT%\scripts\warroom_48h_runner.py"
set "LOG=%ROOT%\reports\warroom_48h\runner.log"
set "HOURS=48"
set "INTERVAL=300"

if not exist "%ROOT%\reports\warroom_48h" mkdir "%ROOT%\reports\warroom_48h"
if not exist "%PY%" (
  echo [ERROR] python not found: %PY%
  exit /b 1
)
if not exist "%WARROOM%" (
  echo [ERROR] script not found: %WARROOM%
  exit /b 1
)

call "%ROOT%\Start_All_Stable.bat"
if errorlevel 1 (
  echo [ERROR] Start_All_Stable failed, stop warroom.
  exit /b 2
)

echo [INFO] 48H warroom starting...
echo [INFO] logs: %LOG%
"%PY%" "%WARROOM%" --hours %HOURS% --interval-seconds %INTERVAL% >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
echo [INFO] warroom finished rc=%RC%
exit /b %RC%


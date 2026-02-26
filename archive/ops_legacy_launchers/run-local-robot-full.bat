@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "local_robot.py" (
    echo Error: Please run from project root.
    pause
    exit /b 1
)

set PYCMD=python
where python >nul 2>&1 || set PYCMD=py

echo.
echo  ========================================
echo   ZheWei Brain - Full Startup
echo  ========================================
echo.

REM 1. Wake Ollama
echo [1/4] Waking Ollama...
"%PYCMD%" scripts\wake_all_devices.py 2>nul
echo.

REM 2. Start Brain Bridge API
echo [2/4] Starting Brain Bridge API (port 5100)...
start "" cmd /k "cd /d %~dp0 && %PYCMD% -m pip install fastapi uvicorn -q 2>nul && %PYCMD% -m uvicorn brain_bridge_fastapi:app --host 0.0.0.0 --port 5100"
timeout /t 4 /nobreak >nul
echo   [OK] Brain Bridge started
echo.

REM 3. Start OpenClaw Gateway
echo [3/4] Starting OpenClaw Gateway...
where openclaw >nul 2>&1
if %errorlevel% equ 0 (
    start "" /MIN cmd /c "openclaw gateway"
    timeout /t 2 /nobreak >nul
    echo   [OK] OpenClaw Gateway started
) else (
    echo   [Skip] OpenClaw not installed
)
echo.

REM 4. Start Local Robot
echo [4/4] Starting Local Robot...
echo   Login page: http://127.0.0.1:5100/login
timeout /t 2 /nobreak >nul
echo.
set ZHEWEI_LOCAL_ROBOT=1
"%PYCMD%" local_robot.py %*

echo.
echo Done. Press any key to close...
pause >nul

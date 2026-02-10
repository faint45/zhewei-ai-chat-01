@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo    Zhewei Brain - Startup Script
echo ========================================
echo.

REM Set script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Step 1: Run diagnostics
echo [Step 1/3] Running system diagnostics...
echo.
python startup_diagnostics.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Diagnostics failed! Please fix the issues above.
    echo.
    pause
    exit /b 1
)

echo.
echo [Step 2/3] Starting services...
timeout /t 2 /nobreak >nul

REM Step 2: Check and start Brain Server
if exist "brain_server.py" (
    echo Starting Brain Server (Port 8000)...
    start "Zhewei Brain - Chat Service" cmd /k "python brain_server.py"
    echo [OK] Brain Server started
    timeout /t 2 /nobreak >nul
) else (
    echo [ERROR] brain_server.py not found
)

REM Step 3: Check and start Monitoring Dashboard
if exist "monitoring_dashboard.py" (
    echo Starting Monitoring Dashboard (Port 8001)...
    start "Zhewei Brain - Monitoring Panel" cmd /k "python monitoring_dashboard.py"
    echo [OK] Monitoring Dashboard started
) else (
    echo [WARNING] monitoring_dashboard.py not found
)

echo.
echo ========================================
echo    Startup Complete!
echo ========================================
echo.
echo Services running:
echo   - Chat Service:   http://localhost:8000
echo   - Monitoring:      http://localhost:8001
echo.
echo Remote access (via Tailscale VPN):
echo   - Chat Service:   http://100.116.133.23:8000
echo   - Monitoring:      http://100.116.133.23:8001
echo.
echo Opening browser in 3 seconds...
timeout /t 3 /nobreak >nul
start http://localhost:8000

echo.
echo Press any key to exit...
pause >nul

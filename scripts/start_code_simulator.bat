@echo off
chcp 65001 >nul
echo ========================================
echo   築未科技 代碼模擬器 v1.0
echo   http://127.0.0.1:8001/simulator
echo ========================================
echo.

cd /d "%~dp0\..\simulator"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)

:: Check dependencies
python -c "import fastapi, uvicorn, httpx" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing dependencies...
    pip install fastapi uvicorn httpx python-dotenv
)

echo [INFO] Starting Code Simulator on port 8001...
echo [INFO] Open http://127.0.0.1:8001/simulator
echo.
python code_simulator.py
pause

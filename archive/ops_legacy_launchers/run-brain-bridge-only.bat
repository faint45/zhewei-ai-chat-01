@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PYCMD=python
where python >nul 2>&1 || set PYCMD=py

echo.
echo ZheWei Brain - Brain Bridge API (port 5100)
echo After startup, open: http://127.0.0.1:5100/login
echo.

"%PYCMD%" -m pip install fastapi uvicorn -q 2>nul
"%PYCMD%" scripts\run_brain_bridge.py

echo.
echo Stopped. Press any key to close...
pause >nul

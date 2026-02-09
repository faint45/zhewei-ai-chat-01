@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PYCMD=python
where python >nul 2>&1 || set PYCMD=py

echo Run smoke test (ensure Brain Bridge is running: run-brain-bridge-only.bat)
"%PYCMD%" scripts\smoke-test-brain-api.py
echo.
pause

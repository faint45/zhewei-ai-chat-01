@echo off
REM 築未科技大腦 — 外網連線診斷
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "scripts\check_external_access.ps1"
pause

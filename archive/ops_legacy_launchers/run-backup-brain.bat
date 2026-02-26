@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PYCMD=python
where python >nul 2>&1 || set PYCMD=py

echo Running brain data backup (knowledge, cost, logs, Chroma, sessions)...
"%PYCMD%" scripts\backup-brain-data.py
echo.
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PYCMD=python
where python >nul 2>&1 || set PYCMD=py

"%PYCMD%" scripts\test-remote-access.py
echo.
pause

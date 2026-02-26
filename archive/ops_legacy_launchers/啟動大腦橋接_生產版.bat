@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYCMD=python
where python >nul 2>&1 || set PYCMD=py
echo 築未科技大腦橋接 - FastAPI + gunicorn 生產版
echo.
"%PYCMD%" -m pip install fastapi uvicorn gunicorn -q 2>nul
"%PYCMD%" -m gunicorn -c gunicorn.conf.py brain_bridge_fastapi:app
pause

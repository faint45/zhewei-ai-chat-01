@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 築未科技 — 完整跑啟動
echo.
python scripts\run_full_system.py
pause

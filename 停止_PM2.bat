@echo off
cd /d "%~dp0"
pm2 stop all
echo [OK] 已停止
pause

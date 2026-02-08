@echo off
chcp 65001 >nul
title 築未科技 - 遠程控制服務器 [端口 8005]

echo ════════════════════════════════════════════════════
echo  築未科技 - 遠程控制服務器 [端口 8005]
echo ════════════════════════════════════════════════════
echo.
echo ⚙️ 訪問地址：
echo    - 遠程控制：  http://localhost:8005
echo.
echo ════════════════════════════════════════════════════
echo.
echo 正在啟動服務器...
echo.

python remote_control_server.py

pause

@echo off
chcp 65001 >nul
title 築未科技 - 網站服務器 [端口 8000]

echo ════════════════════════════════════════════════════
echo  築未科技 - 網站服務器 [端口 8000]
echo ════════════════════════════════════════════════════
echo.
echo 🌐 訪問地址：
echo    - 網站首頁：  http://localhost:8000
echo    - AI大腦：    http://localhost:8000/chat
echo    - 管理後台：  http://localhost:8000/admin
echo    - 聯繫我們：  http://localhost:8000/contact
echo.
echo ════════════════════════════════════════════════════
echo.
echo 正在啟動服務器...
echo.

python website_server.py

pause

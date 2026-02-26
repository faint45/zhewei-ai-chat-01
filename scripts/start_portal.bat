@echo off
chcp 65001 >nul
title Portal - 築未科技服務入口

echo 🌐 啟動 Portal 服務入口網站...
echo ========================================

:: 檢查 Python
call python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，請先安裝 Python 3.8+
    pause
    exit /b 1
)

:: 設定環境變數
set PORTAL_PORT=8888

echo.
echo 🚀 啟動 Portal (Port 8888)...
echo 📍 本地訪問: http://localhost:8888
echo 📍 外網訪問: https://zhe-wei.net (需配置 Tunnel)
echo ========================================
echo.

:: 啟動服務
call python portal_server.py

pause

@echo off
chcp 65001 >nul
title Smart Bridge - 築未科技

echo 🌉 啟動 Smart Bridge 服務...
echo ========================================

:: 檢查 Python
call python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，請先安裝 Python 3.8+
    pause
    exit /b 1
)

:: 設定環境變數
set SMART_BRIDGE_PORT=8003
set SMART_BRIDGE_HOST=0.0.0.0

:: 檢查 Ollama
set OLLAMA_BASE_URL=http://localhost:11434
curl -s %OLLAMA_BASE_URL%/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Ollama 檢測正常
) else (
    echo ⚠️ Ollama 未響應，將使用雲端模型作為備援
)

echo.
echo 🚀 啟動 Smart Bridge (Port 8003)...
echo 📍 本地訪問: http://localhost:8003
echo 📍 外網訪問: https://bridge.zhe-wei.net (需配置 Tunnel)
echo ========================================
echo.

:: 啟動服務
call python smart_bridge.py

pause

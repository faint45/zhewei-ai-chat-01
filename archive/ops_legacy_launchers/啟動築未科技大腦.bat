@echo off
chcp 65001 >nul
cls
echo ================================================================
echo        築未科技大腦 - 遠端對話系統
echo ================================================================
echo.

cd /d "%~dp0"

echo [1/3] 檢查 Python 環境...
python --version
if %errorlevel% neq 0 (
    echo ✗ Python 未安裝或未添加到 PATH
    echo 請先安裝 Python 3.8 或更高版本
    pause
    exit /b 1
)
echo ✓ Python 環境檢查完成
echo.

echo [2/3] 安裝依賴套件...
echo 正在安裝 FastAPI、Uvicorn...
pip install fastapi uvicorn websockets pydantic --quiet
if %errorlevel% neq 0 (
    echo ✗ 依賴套件安裝失敗
    pause
    exit /b 1
)
echo ✓ 依賴套件安裝完成
echo.

echo [3/3] 啟動築未科技大腦服務器...
echo.
echo ================================================================
echo 🌐 服務器資訊
echo ================================================================
echo • 本地訪問: http://localhost:8000
echo • WebSocket: ws://localhost:8000/ws/chat
echo • REST API: http://localhost:8000/api
echo • 對話界面: file:///%~dp0remote_brain.html
echo.
echo ℹ️  按下 Ctrl+C 停止服務器
echo ================================================================
echo.

python brain_server.py

pause

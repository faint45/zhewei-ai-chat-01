@echo off
chcp 65001 >nul
echo ========================================
echo 易經科學預測系統啟動
echo I Ching Scientific Prediction System
echo ========================================
echo.

cd /d D:\zhe-wei-tech

echo [1/3] 檢查 Python 環境...
if not exist "Jarvis_Training\.venv312\Scripts\python.exe" (
    echo ❌ Python 虛擬環境不存在
    pause
    exit /b 1
)

echo [2/3] 安裝依賴套件...
Jarvis_Training\.venv312\Scripts\python.exe -m pip install fastapi uvicorn websockets pydantic requests -q

echo [3/3] 啟動預測服務 (Port 8025)...
echo.
echo 🔮 系統啟動中...
echo 📊 儀表板: http://localhost:8025/static/prediction_dashboard.html
echo 📖 API 文檔: http://localhost:8025/docs
echo.

Jarvis_Training\.venv312\Scripts\python.exe prediction_modules\prediction_service.py

pause

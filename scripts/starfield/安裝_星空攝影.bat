@echo off
chcp 65001 >nul
echo ============================================
echo   Tapo C230 星空攝影 — 安裝環境
echo ============================================
echo.

cd /d "%~dp0"

:: 檢查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 找不到 Python，請先安裝 Python 3.10+
    pause
    exit /b 1
)

:: 建立虛擬環境
if not exist "venv" (
    echo 📦 建立虛擬環境...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 建立虛擬環境失敗
        pause
        exit /b 1
    )
)

:: 啟動虛擬環境並安裝依賴
echo 📦 安裝依賴套件...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ❌ 安裝依賴失敗
    pause
    exit /b 1
)

:: 檢查 .env
if not exist ".env" (
    echo.
    echo ⚠️  尚未設定 RTSP URL
    echo    請執行「設定RTSP.bat」來設定攝影機連線
    echo.
)

echo.
echo ✅ 安裝完成！
echo.
pause

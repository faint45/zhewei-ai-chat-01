@echo off
chcp 65001 >nul
echo ============================================
echo   Tapo C230 星空攝影 — 一鍵啟動
echo ============================================
echo.

cd /d "%~dp0"

:: Step 1: 檢查/安裝環境
if not exist "venv\Scripts\python.exe" (
    echo 📦 首次使用，安裝環境中...
    call 安裝_星空攝影.bat
    if errorlevel 1 exit /b 1
)

:: Step 2: 檢查 .env
if not exist ".env" (
    echo ⚠️  尚未設定 RTSP URL
    call 設定RTSP.bat
    if errorlevel 1 exit /b 1
)

:: Step 3: 測試 RTSP 連線
echo 🔍 測試 RTSP 連線...
call venv\Scripts\activate.bat
python test_rtsp.py
if errorlevel 1 (
    echo.
    echo ❌ RTSP 連線失敗，請檢查：
    echo    1. 攝影機是否開機
    echo    2. IP 位址是否正確
    echo    3. 帳號密碼是否正確
    echo.
    pause
    exit /b 1
)

:: Step 4: 啟動相機模式
echo.
echo ✅ 連線成功！啟動相機模式...
echo    按 Q 退出
echo.
python virtual_cam_params.py -i --no-vcam
echo.
pause

@echo off
chcp 65001 >nul
echo ============================================
echo   Tapo C230 星空攝影 — 設定 RTSP URL
echo ============================================
echo.

cd /d "%~dp0"

echo 格式：rtsp://帳號:密碼@IP:554/stream1
echo 範例：rtsp://allen34556:12345678@192.168.0.21:554/stream1
echo.

if exist ".env" (
    echo 目前設定：
    type .env
    echo.
    echo ---
)

set /p RTSP_URL="請輸入 RTSP URL："

if "%RTSP_URL%"=="" (
    echo ❌ 未輸入任何內容
    pause
    exit /b 1
)

echo TAPO_RTSP_URL=%RTSP_URL%> .env
echo.
echo ✅ 已儲存至 .env
echo    TAPO_RTSP_URL=%RTSP_URL%
echo.
pause

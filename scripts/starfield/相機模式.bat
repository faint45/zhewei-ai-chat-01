@echo off
chcp 65001 >nul
echo ============================================
echo   Tapo C230 星空攝影 — 相機模式（互動滑桿）
echo ============================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo ❌ 尚未安裝，請先執行「安裝_星空攝影.bat」
    pause
    exit /b 1
)

if not exist ".env" (
    echo ❌ 尚未設定 RTSP URL，請先執行「設定RTSP.bat」
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python virtual_cam_params.py -i --no-vcam
echo.
pause

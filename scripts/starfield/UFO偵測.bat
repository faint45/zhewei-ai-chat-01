@echo off
chcp 65001 >nul
echo ============================================
echo   🛸 Tapo C230 UFO 偵測 — 本地 GUI 模式
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

set /p SENS="偵測靈敏度 0.0~1.0（預設 0.5）："
if "%SENS%"=="" set SENS=0.5

echo.
echo 🛸 啟動 UFO 偵測...
echo    靈敏度: %SENS%
echo    按 Q 退出，S 截圖
echo.

call venv\Scripts\activate.bat
python ufo_detector.py -s %SENS%
echo.
pause

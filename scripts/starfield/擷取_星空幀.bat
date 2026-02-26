@echo off
chcp 65001 >nul
echo ============================================
echo   Tapo C230 星空攝影 — 擷取星空幀
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

set /p COUNT="擷取幀數（預設 100）："
if "%COUNT%"=="" set COUNT=100

set /p INTERVAL="擷取間隔秒數（預設 2）："
if "%INTERVAL%"=="" set INTERVAL=2

echo.
echo 📸 開始擷取 %COUNT% 幀（間隔 %INTERVAL% 秒）...
echo    按 Ctrl+C 可中斷
echo.

call venv\Scripts\activate.bat
python capture_with_params.py -n %COUNT% -i %INTERVAL% --star-mode --clahe --denoise
echo.
pause

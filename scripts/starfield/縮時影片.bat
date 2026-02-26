@echo off
chcp 65001 >nul
echo ============================================
echo   Tapo C230 星空攝影 — 縮時影片 / 星軌影片
echo ============================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo ❌ 尚未安裝，請先執行「安裝_星空攝影.bat」
    pause
    exit /b 1
)

:: 列出可用的幀目錄
echo 可用的幀目錄：
echo ---
if exist "starfield_frames" (
    dir /b /ad starfield_frames 2>nul
) else (
    echo （尚無擷取資料）
    pause
    exit /b 1
)
echo ---
echo.

set /p FRAME_DIR="請輸入幀目錄名稱："
if "%FRAME_DIR%"=="" (
    echo ❌ 未輸入目錄名稱
    pause
    exit /b 1
)

set FULL_PATH=starfield_frames\%FRAME_DIR%
if not exist "%FULL_PATH%" (
    echo ❌ 目錄不存在：%FULL_PATH%
    pause
    exit /b 1
)

echo.
echo 模式：
echo   1. timelapse（縮時攝影）
echo   2. startrail（星軌生成過程影片）
set /p MODE_CHOICE="選擇（1/2，預設 1）："
if "%MODE_CHOICE%"=="2" (set MODE=startrail) else (set MODE=timelapse)

set /p FPS="FPS（預設 24）："
if "%FPS%"=="" set FPS=24

echo.
echo 🎬 開始合成（%MODE%，%FPS% fps）...
call venv\Scripts\activate.bat
python timelapse.py %MODE% "%FULL_PATH%" --fps %FPS%
echo.
pause

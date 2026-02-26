@echo off
chcp 65001 >nul
echo ============================================
echo   Tapo C230 星空攝影 — 疊圖
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
    echo （尚無擷取資料，請先執行「擷取_星空幀.bat」）
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
echo 疊圖方法：
echo   1. median（中位數，預設，去除雜訊效果好）
echo   2. mean（平均值，保留更多細節）
set /p METHOD_CHOICE="選擇（1/2，預設 1）："
if "%METHOD_CHOICE%"=="2" (set METHOD=mean) else (set METHOD=median)

echo.
echo 🔄 開始疊圖（%METHOD%）...
call venv\Scripts\activate.bat
python stack_frames.py "%FULL_PATH%" -m %METHOD%
echo.
pause

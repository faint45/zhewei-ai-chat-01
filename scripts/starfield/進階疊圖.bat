@echo off
chcp 65001 >nul
echo ============================================
echo   Tapo C230 星空攝影 — 進階疊圖
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
echo   1. sigma_clip（Sigma Clipping，去除異常值，推薦）
echo   2. median（中位數）
echo   3. mean（平均值）
echo   4. star_trails（星軌 Max）
echo   5. star_trails_fade（漸變星軌）
set /p METHOD_CHOICE="選擇（1-5，預設 1）："
if "%METHOD_CHOICE%"=="2" (set METHOD=median) else if "%METHOD_CHOICE%"=="3" (set METHOD=mean) else if "%METHOD_CHOICE%"=="4" (set METHOD=star_trails) else if "%METHOD_CHOICE%"=="5" (set METHOD=star_trails_fade) else (set METHOD=sigma_clip)

set /p DO_ALIGN="啟用星點對齊？（y/N）："
if /i "%DO_ALIGN%"=="y" (set ALIGN=--align) else (set ALIGN=)

echo.
echo 🔄 開始進階疊圖（%METHOD%）...
call venv\Scripts\activate.bat
python advanced_stack.py "%FULL_PATH%" -m %METHOD% %ALIGN%
echo.
pause

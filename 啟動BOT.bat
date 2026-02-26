@echo off
chcp 65001 >nul
cd /d "%~dp0"
cd Jarvis_Training

echo.
echo ========================================
echo   賈維斯 Discord BOT 啟動
echo ========================================
echo.

REM 檢查 .env
if not exist ".env" (
    echo [錯誤] .env 不存在
    echo 請複製 .env.example 為 .env，並填入 DISCORD_BOT_TOKEN
    pause
    exit /b 1
)

REM 檢查 Token
findstr /C:"DISCORD_BOT_TOKEN=" .env | findstr /V "your_ example xxx" >nul 2>nul
if errorlevel 1 (
    echo [錯誤] DISCORD_BOT_TOKEN 未設定或仍為範例值
    echo 請在 .env 填入正確的 Bot Token
    pause
    exit /b 1
)

REM 檢查 Python
set "PY=.venv312\Scripts\python.exe"
if not exist "%PY%" (
    set "PY=python"
    where python >nul 2>nul
    if errorlevel 1 (
        echo [錯誤] 找不到 Python
        echo 請安裝 Python 或建立 .venv312
        pause
        exit /b 1
    )
    echo [提示] 使用系統 Python
) else (
    echo [OK] 使用 .venv312
)

echo.
echo 正在啟動 BOT...
echo 若成功，Discord 會顯示為「上線」
echo 按 Ctrl+C 可停止
echo ========================================
echo.

"%PY%" jarvis_discord_bot.py

echo.
echo [結束] BOT 已停止
pause

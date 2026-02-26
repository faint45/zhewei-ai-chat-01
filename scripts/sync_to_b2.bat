@echo off
chcp 65001 >nul
setlocal EnableExtensions
title 築未科技 - 同步至 Backblaze B2（冷備份）

cd /d "%~dp0\.."
set "PROJ=%CD%"

where rclone >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 找不到 rclone
    pause
    exit /b 1
)

rclone listremotes | findstr /C:"b2:" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 未找到 b2 遠端
    echo 請先執行：scripts\setup_b2_rclone.bat
    pause
    exit /b 1
)

set "B2_BUCKET=zhewei-brain-backup"
echo 建立 Bucket（若不存在）...
rclone mkdir "b2:%B2_BUCKET%" 2>nul
echo.

echo ============================================================
echo 築未科技 - 冷備份同步至 Backblaze B2
echo ============================================================
echo.

:: 從 gdrive 同步到 b2（若 gdrive 已有完整資料）
rclone listremotes | findstr /C:"gdrive:" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [1/2] 從 gdrive 同步至 b2...
    rclone sync "gdrive:Zhewei_Brain" "b2:%B2_BUCKET%" ^
        --exclude "*.pyc" --exclude "**/__pycache__/" ^
        --transfers 4 --checkers 8 --progress
) else (
    echo [1/2] 無 gdrive，直接從本地同步...
    if exist "D:\brain_workspace" (
        rclone sync "D:\brain_workspace" "b2:%B2_BUCKET%/workspace" ^
            --exclude "venv*/" --exclude "**/__pycache__/" ^
            --transfers 4 --checkers 8 --progress
    )
    rclone sync "%PROJ%" "b2:%B2_BUCKET%/tech_repo" ^
        --exclude ".venv312/" --exclude "node_modules/" --exclude ".git/objects/" ^
        --exclude "*.pt" --exclude "raw_footage/**" ^
        --transfers 4 --checkers 8 --progress
)

echo.
echo [2/2] 完成。B2 Bucket: %B2_BUCKET%
echo ============================================================
if /i not "%1"=="quiet" pause

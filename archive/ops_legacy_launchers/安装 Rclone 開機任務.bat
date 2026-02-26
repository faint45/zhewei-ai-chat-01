@echo off
chcp 65001 >nul
title 築未科技 - 開機自動掛載 Z 槽（工作排程）

:: 需管理員權限
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 請以「以系統管理員身分執行」此腳本。
    pause
    exit /b 1
)

set "RCLONE_EXE=C:\tools\rclone\rclone.exe"
set "TASK_NAME=RcloneMountGDrive"
set "MOUNT_ARGS=mount gdrive: Z: --vfs-cache-mode full --no-modtime --dir-cache-time 1h --vfs-cache-max-size 10G --no-checksum --links"

if not exist "%RCLONE_EXE%" (
    echo [錯誤] 找不到 rclone：%RCLONE_EXE%
    pause
    exit /b 1
)

rclone listremotes | findstr /C:"gdrive:" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 未找到遠端 gdrive，請先執行 rclone config。
    pause
    exit /b 1
)

:: 若已存在則先刪除
schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo 正在移除舊任務...
    schtasks /Delete /TN "%TASK_NAME%" /F
)

echo 正在建立開機登入時執行的任務...
schtasks /Create /TN "%TASK_NAME%" /TR "\"%RCLONE_EXE%\" %MOUNT_ARGS%" /SC ONLOGON /RL HIGHEST /F
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 建立任務失敗。
    pause
    exit /b 1
)

echo.
echo 已建立任務「%TASK_NAME%」：下次登入時會自動掛載 Z 槽。
echo.
echo 若要立即掛載，請執行：schtasks /Run /TN "%TASK_NAME%"
echo 若要取消開機掛載，請執行「卸載 Rclone 開機任務.bat」
echo.
pause

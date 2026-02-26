@echo off
setlocal EnableExtensions
title 築未科技 - 設定 B2 冷備份排程

cd /d "%~dp0\.."

set "B2_BAT=%~dp0sync_to_b2.bat"
set "TASK_NAME=ZheweiB2ColdBackup"
set "TASK_DESC=築未科技 - 每日同步至 Backblaze B2"

schtasks /Create /TN "%TASK_NAME%" /TR "\"%B2_BAT%\" quiet" /SC DAILY /ST 03:00 /F >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [警告] 排程建立失敗，請以管理員執行。
) else (
    echo [OK] 排程已建立：每日 03:00 同步至 B2
)

schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo 請先執行 setup_b2_rclone.bat 完成 B2 設定。
) else (
    echo [錯誤] 排程建立失敗。
)
pause

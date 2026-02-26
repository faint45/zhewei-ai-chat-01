@echo off
setlocal EnableExtensions
title 築未科技 - 設定雲端同步排程

cd /d "%~dp0\.."

set "SYNC_BAT=%~dp0sync_to_cloud.bat"
set "TASK_NAME=ZheweiCloudSync"
set "TASK_DESC=築未科技 - 每小時同步資料至 Google Drive"

:: 建立每小時執行一次的排程（quiet 模式不 pause）
schtasks /Create /TN "%TASK_NAME%" /TR "\"%SYNC_BAT%\" quiet" /SC HOURLY /ST 00:00 /F >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [警告] 排程建立失敗，請以管理員執行。改為每 2 小時...
    schtasks /Create /TN "%TASK_NAME%" /TR "\"%SYNC_BAT%\"" /SC HOURLY /MO 2 /ST 00:00 /F >nul 2>&1
)

schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] 排程已建立：%TASK_NAME%
    echo 執行：每小時自動同步 D:\brain_workspace 與專案至雲端
) else (
    echo [錯誤] 排程建立失敗，請以系統管理員身分執行。
)
pause

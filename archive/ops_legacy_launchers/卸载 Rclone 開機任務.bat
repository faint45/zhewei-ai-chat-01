@echo off
chcp 65001 >nul
title 築未科技 - 取消開機自動掛載

set "TASK_NAME=RcloneMountGDrive"

schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 任務「%TASK_NAME%」不存在，無需卸載。
    pause
    exit /b 0
)

schtasks /Delete /TN "%TASK_NAME%" /F
echo 已移除開機掛載任務。
pause

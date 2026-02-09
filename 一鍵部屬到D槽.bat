@echo off
chcp 65001 >nul
title 築未科技 — 一鍵部屬到 D 槽（資料都放 D）

cd /d "%~dp0"
echo.
echo 築未科技 — D 槽部署（資料都放在 D 槽）
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0scripts\deploy_to_d_drive.ps1"
if %errorlevel% neq 0 (
    echo.
    echo [X] 部署失敗
    pause
    exit /b 1
)

echo.
pause

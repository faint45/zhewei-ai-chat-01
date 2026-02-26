@echo off
chcp 65001 >nul
title 築未科技 - 卸載 Rclone 掛載服務

:: 需管理員權限
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 請以「以系統管理員身分執行」此腳本。
    pause
    exit /b 1
)

set "NSSM=C:\tools\nssm\nssm.exe"

sc query RcloneMount >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 服務 RcloneMount 不存在，無需卸載。
    pause
    exit /b 0
)

echo 正在停止服務 RcloneMount...
if exist "%NSSM%" (
    "%NSSM%" stop RcloneMount
) else (
    net stop RcloneMount
)
timeout /t 2 /nobreak >nul

echo 正在移除服務...
if exist "%NSSM%" (
    "%NSSM%" remove RcloneMount confirm
) else (
    sc delete RcloneMount
)

echo.
echo 服務已卸載。
pause

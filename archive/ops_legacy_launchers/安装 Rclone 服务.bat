@echo off
chcp 65001 >nul
title 築未科技 - 安裝 Rclone 掛載服務（開機自動掛載）

:: 需管理員權限
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 請以「以系統管理員身分執行」此腳本。
    pause
    exit /b 1
)

set "NSSM=C:\tools\nssm\nssm.exe"
set "PROJ=%~dp0"
set "PROJ=%PROJ:~0,-1%"

if not exist "%NSSM%" (
    echo [錯誤] 找不到 NSSM：%NSSM%
    echo 請從 https://nssm.cc/download 下載並解壓到 C:\tools\nssm
    echo 將 nssm.exe 放在 C:\tools\nssm\
    pause
    exit /b 1
)

where rclone >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 找不到 rclone，請先安裝並加入 PATH。
    pause
    exit /b 1
)

rclone listremotes | findstr /C:"gdrive:" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 未找到遠端 gdrive，請先執行 rclone config。
    pause
    exit /b 1
)

sc query RcloneMount >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo 服務 RcloneMount 已存在，請先執行「卸載 Rclone 服務.bat」再安裝。
    pause
    exit /b 1
)

echo 正在建立服務 RcloneMount...
"%NSSM%" install RcloneMount rclone "mount gdrive: Z: --vfs-cache-mode full --no-modtime --dir-cache-time 1h --vfs-cache-max-size 10G --no-checksum --links"
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 安裝服務失敗。
    pause
    exit /b 1
)

"%NSSM%" set RcloneMount AppDirectory "%PROJ%"
"%NSSM%" set RcloneMount DisplayName "築未科技 - Google Drive 掛載"
"%NSSM%" set RcloneMount Description "將 Google Drive 掛載為 Z 盤"
"%NSSM%" set RcloneMount Start SERVICE_AUTO_START

echo 正在啟動服務...
"%NSSM%" start RcloneMount
echo.
echo 服務已安裝並設為開機自動啟動。
echo 若 Z 槽未出現，請確認 WinFsp 已安裝並重新開機後再試。
pause

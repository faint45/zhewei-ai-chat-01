@echo off
chcp 65001 >nul
title 築未科技 - 卸載 Google Drive

echo ============================================================
echo 築未科技 - 卸載 Google Drive（Z 槽）
echo ============================================================
echo.

:: 檢查 Z 槽是否存在
if not exist Z:\ (
    echo Z 槽未掛載或無法存取，無需卸載。
    goto :done
)

echo 正在卸載 Z: 盤...
echo.

:: 方法 1：嘗試 net use 卸載（部分環境有效）
net use Z: /delete /y >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo 已透過 net use 卸載 Z:。
    goto :done
)

:: 方法 2：結束正在掛載 Z 的 rclone 行程（WinFsp 掛載需結束行程）
tasklist /FI "IMAGENAME eq rclone.exe" 2>nul | find /I "rclone.exe" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo 正在結束 rclone 掛載行程...
    taskkill /IM rclone.exe /F >nul 2>&1
    timeout /t 2 /nobreak >nul
    if exist Z:\ (
        echo 若 Z: 仍存在，請手動關閉「掛載 Google Drive 為 Z 槽.bat」的視窗。
    ) else (
        echo 已卸載 Z:。
    )
) else (
    echo 未發現執行中的 rclone。若 Z: 仍顯示，請關閉掛載腳本視窗或重新開機。
)

:done
echo.
pause

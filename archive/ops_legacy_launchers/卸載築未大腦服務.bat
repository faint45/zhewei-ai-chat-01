@echo off
title 築未科技：卸載 ZheweiBrain 服務
chcp 65001 > nul

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ 請以「系統管理員身分」執行此檔案！
    pause
    exit /b
)

set NSSM="C:\tools\nssm\nssm.exe"
set SERVICE_NAME="ZheweiBrain"

echo 🛑 正在停止並移除 %SERVICE_NAME%...
%NSSM% stop %SERVICE_NAME%
%NSSM% remove %SERVICE_NAME% confirm

echo ✅ 服務已成功移除。
pause

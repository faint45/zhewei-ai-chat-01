@echo off
chcp 65001 >nul
title NVIDIA 穩定性修復與優化
:: 請以「以系統管理員身分執行」執行此檔
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 請在檔案上按右鍵，選擇「以系統管理員身分執行」。
    pause
    exit /b 1
)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\repair_nvidia_stability.ps1"
pause

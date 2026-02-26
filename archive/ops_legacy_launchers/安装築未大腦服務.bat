@echo off
title 築未科技：安裝 ZheweiBrain 服務
chcp 65001 > nul

:: 權限檢查
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ 請以「系統管理員身分」執行此檔案！
    pause
    exit /b 1
)

:: 配置變數 (請確認路徑正確)
set NSSM=C:\tools\nssm\nssm.exe
set PROJ_DIR=%~dp0
set PROJ_DIR=%PROJ_DIR:~0,-1%
set SERVICE_NAME=ZheweiBrain
set PYTHON_EXE=python

:: 若有特定 Python 路徑需求請取消下行註解
:: set PYTHON_EXE=C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe

echo 🛠️ 正在安裝 %SERVICE_NAME% 服務...
"%NSSM%" install %SERVICE_NAME% %PYTHON_EXE% brain_server.py
"%NSSM%" set %SERVICE_NAME% AppDirectory "%PROJ_DIR%"
"%NSSM%" set %SERVICE_NAME% Start SERVICE_AUTO_START
"%NSSM%" set %SERVICE_NAME% Description "築未科技 AI 工地管理大腦服務"

echo 🚀 啟動服務...
"%NSSM%" start %SERVICE_NAME%

echo ✨ 安裝完成，系統妥善率：$100%%$.
pause

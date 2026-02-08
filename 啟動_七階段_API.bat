@echo off
chcp 65001 >nul
title 七階段系統 HTTP API

echo.
echo ========================================
echo   七階段指揮作戰系統 HTTP API
echo   Seven-Stage System HTTP API
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 檢查環境變量...
if not exist ".env.seven_stage" (
    echo 錯誤: 找不到 .env.seven_stage 配置文件
    pause
    exit /b 1
)
echo OK: 環境變量已配置

echo.
echo [2/3] 加載環境變量...
for /f "tokens=*" %%a in ('type .env.seven_stage ^| findstr /v "^#" ^| findstr "="') do set %%a
echo OK: 環境變量已加載

echo.
echo [3/3] 啟動 HTTP API 服務器...
echo.
echo 服務器信息:
echo   本地訪問: http://localhost:8006
echo   API 文檔: http://localhost:8006/docs
echo   健康檢查: http://localhost:8006/health
echo.
echo ========================================
echo.

python seven_stage_api.py

pause

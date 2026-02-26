@echo off
title 築未科技 PM2
cd /d "%~dp0"
chcp 65001 >nul
set "MODE=%~1"

echo 築未科技大腦 — PM2 啟動
echo.

where pm2 >nul 2>nul
if errorlevel 1 (
  echo [ERROR] PM2 未安裝。請執行：npm install -g pm2
  goto :end
)

if not exist "ecosystem.docker.config.cjs" (
  echo [ERROR] 找不到 ecosystem.docker.config.cjs，請確認在專案根目錄執行
  goto :end
)

if not exist "reports" mkdir reports

if /I "%MODE%"=="docker" (
  echo 模式：Docker
  pm2 start ecosystem.docker.config.cjs
) else (
  echo 模式：本機全服務
  if exist "ecosystem.config.cjs" (
    pm2 start ecosystem.config.cjs
  ) else (
    pm2 start ecosystem.docker.config.cjs
  )
)

echo.
pm2 status
echo.

:end
echo 按任意鍵關閉...
pause >nul

@echo off
chcp 65001 >nul
title 築未科技 - 啟動 OpenHands (AI 軟體工程師)

cd /d "%~dp0"

echo ============================================================
echo 築未科技 - OpenHands (原 OpenDevin)
echo AI 自動寫程式、測試、修 Bug 的沙盒環境
echo ============================================================
echo.

docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] Docker 未啟動，請先開啟 Docker Desktop
    pause
    exit /b 1
)

echo [1/2] 啟動 OpenHands...
docker compose -f docker-compose.openhands.yml up -d
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 啟動失敗
    pause
    exit /b 1
)

echo.
echo [2/2] 等待服務就緒...
timeout /t 10 /nobreak >nul

echo.
echo ============================================================
echo OpenHands 已啟動！
echo.
echo   介面網址：http://localhost:3001
echo.
echo   設定 LLM：
echo     - 選 Ollama → Base URL: http://host.docker.internal:11434
echo     - 或選 Gemini → 填入 GEMINI_API_KEY
echo.
echo   使用方式：
echo     1. 打開瀏覽器 http://localhost:3000
echo     2. 在左側對話框輸入任務
echo     3. AI 會自動寫程式、跑指令、看報錯、自動修
echo.
echo   停止：docker compose -f docker-compose.openhands.yml down
echo ============================================================
echo.
start http://localhost:3001
pause

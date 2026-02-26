@echo off
chcp 65001 >nul
echo ========================================
echo   Railway 部署 - 七階段系統
echo ========================================
echo.

cd /d "%~dp0"

echo [步驟 1/6] 檢查登錄狀態...
railway whoami
if %errorlevel% neq 0 (
    echo 需要登錄...
    echo.
    echo 請在瀏覽器中完成授權
    railway login
    echo.
)

echo.
echo [步驟 2/6] 初始化項目...
railway init --name seven-stage-system

echo.
echo [步驟 3/6] 設置啟動命令...
railway variables set RAILWAY_COMMAND="uvicorn seven_stage_api:app --host 0.0.0.0 --port $PORT"

echo.
echo [步驟 4/6] 配置環境變量...
echo 配置 Gemini API...
railway variables set GEMINI_API_KEY=AIzaSyDthmqwPFbVvSECltanWKOo1O8p-KP_Rt0

echo 配置 Claude API...
railway variables set ANTHROPIC_API_KEY=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

echo 配置 Cursor API...
railway variables set CURSOR_API_KEY=key_9c4a95d3000562a24a35048849eac00524b44ea547657d2b9dc2a19c4854f994

echo 配置通義千問 API...
railway variables set QIANWEN_API_KEY=sk-ab8f191deb8744618119023a57bde3dd

echo 配置 API 端口...
railway variables set API_PORT=8006

echo.
echo [步驟 5/6] 部署到 Railway...
railway up

echo.
echo [步驟 6/6] 獲取部署 URL...
echo.
echo 您的應用 URL:
railway domain

echo.
echo ========================================
echo 部署完成！
echo ========================================
echo.
echo 下一步:
echo 1. 測試健康檢查: curl https://your-app.railway.app/health
echo 2. 訪問 API 文檔: https://your-app.railway.app/docs
echo 3. 執行任務測試
echo.
pause

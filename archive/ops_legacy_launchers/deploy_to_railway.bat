@echo off
chcp 65001 >nul
echo ========================================
echo   部署七階段系統到 Railway
echo ========================================
echo.

cd /d "%~dp0"

echo [1/5] 檢查 Railway CLI...
where railway >nul 2>&1
if %errorlevel% neq 0 (
    echo 錯誤: 未找到 Railway CLI
    echo.
    echo 請先安裝 Railway CLI:
    echo   npm install -g @railway/cli
    echo.
    pause
    exit /b 1
)
echo OK: Railway CLI 已安裝

echo.
echo [2/5] 檢查登錄狀態...
railway whoami >nul 2>&1
if %errorlevel% neq 0 (
    echo 需要登錄 Railway...
    railway login
)

echo.
echo [3/5] 創建新項目...
set project_name=seven-stage-system
railway init --name %project_name%

echo.
echo [4/5] 配置環境變量...
echo 請配置以下環境變量:
echo.
echo GEMINI_API_KEY = AIzaSyDthmqwPFbVvSECltanWKOo1O8p-KP_Rt0
echo ANTHROPIC_API_KEY = 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
echo CURSOR_API_KEY = key_9c4a95d3000562a24a35048849eac00524b44ea547657d2b9dc2a19c4854f994
echo QIANWEN_API_KEY = sk-ab8f191deb8744618119023a57bde3dd
echo.
echo (請在 Railway Dashboard 中配置，或手動執行)
echo railway variables set GEMINI_API_KEY=AIzaSyDthmqwPFbVvSECltanWKOo1O8p-KP_Rt0
echo railway variables set ANTHROPIC_API_KEY=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
echo railway variables set CURSOR_API_KEY=key_9c4a95d3000562a24a35048849eac00524b44ea547657d2b9dc2a19c4854f994
echo railway variables set QIANWEN_API_KEY=sk-ab8f191deb8744618119023a57bde3dd
echo.

echo.
echo [5/5] 部署到 Railway...
railway up

echo.
echo ========================================
echo 部署完成！
echo ========================================
echo.
echo 獲取部署 URL:
railway domain

echo.
echo 訪問 Health 端點測試:
echo   curl https://your-domain.railway.app/health
echo.
pause

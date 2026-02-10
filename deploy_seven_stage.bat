@echo off
chcp 65001 >nul
echo ========================================
echo   七階段系統網路部署
echo   Seven-Stage System Deployment
echo ========================================
echo.

cd /d "%~dp0"

echo [選擇部署平台]
echo.
echo 1. Railway (推薦 - 簡單快速)
echo 2. Vercel (適合前端 + API)
echo 3. 腾讯云 CloudBase (適合微信小程序)
echo 4. Cloudflare Pages (免費)
echo 5. 查看部署說明
echo.

set /p choice="請選擇部署方式 (1-5): "

if "%choice%"=="1" goto railway
if "%choice%"=="2" goto vercel
if "%choice%"=="3" goto cloudbase
if "%choice%"=="4" goto cloudflare
if "%choice%"=="5" goto help
goto end

:railway
echo.
echo ========================================
echo [Railway 部署]
echo ========================================
echo.
echo 1. 訪問 https://railway.app/
echo 2. 登錄或創建帳號
echo 3. 點擊 "New Project"
echo 4. 選擇 "Deploy from GitHub repo"
echo 5. 或直接上傳文件
echo.
echo 環境變量配置:
echo   GEMINI_API_KEY
echo   ANTHROPIC_API_KEY
echo   CURSOR_API_KEY
echo   QIANWEN_API_KEY
echo.
echo 部署後會獲得一個 .railway.app 域名
pause
goto end

:vercel
echo.
echo ========================================
echo [Vercel 部署]
echo ========================================
echo.
echo 需要先安裝 Vercel CLI:
echo   npm i -g vercel
echo.
echo 然後執行:
echo   vercel
echo.
pause
goto end

:cloudbase
echo.
echo ========================================
echo [腾讯云 CloudBase 部署]
echo ========================================
echo.
echo 需要先安裝 CloudBase CLI:
echo   npm install -g @cloudbase/cli
echo.
echo 然後執行:
echo   tcb login
echo   tcb deploy
echo.
pause
goto end

:cloudflare
echo.
echo ========================================
echo [Cloudflare Pages 部署]
echo ========================================
echo.
echo 1. 訪問 https://pages.cloudflare.com/
echo 2. 登錄 Cloudflare 帳號
echo 3. 創建新項目
echo 4. 上傳文件或連接 GitHub
echo.
pause
goto end

:help
echo.
echo ========================================
echo [部署說明]
echo ========================================
echo.
echo 推薦方案: Railway
echo   - 免費開始，按用量付費
echo   - 支持長時間運行
echo   - 自動 HTTPS
echo   - 易於配置環境變量
echo.
echo 注意事項:
echo   1. 七階段系統需要長時間運行，推薦 Railway
echo   2. Ollama 服務無法部署到云端（本地運行）
echo   3. API 密鑰需要在部署平台配置環境變量
echo   4. 部署後可通過 API URL 遠程調用
echo.
pause
goto end

:end
echo.
echo ========================================
pause

@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技官方網站 - Vercel雲部署工具
echo ================================================
echo.

echo 🚀 準備部署到Vercel雲服務...
echo.

echo 📋 部署前檢查：
if exist website_server.py (
    echo ✅ 主服務器文件存在
) else (
    echo ❌ 缺少website_server.py
)

if exist requirements_vercel.txt (
    echo ✅ 依賴配置存在
) else (
    echo ❌ 缺少requirements_vercel.txt
)

if exist vercel.json (
    echo ✅ 部署配置存在
) else (
    echo ❌ 缺少vercel.json
)

echo.
echo 🔧 創建部署包...

REM 創建臨時部署目錄
if not exist deploy_temp mkdir deploy_temp

REM 複製必要文件
copy website_server.py deploy_temp\
copy requirements_vercel.txt deploy_temp\requirements.txt
copy vercel.json deploy_temp\

REM 複製靜態文件
xcopy static deploy_temp\static /E /I /Y
xcopy templates deploy_temp\templates /E /I /Y

REM 複製其他必要文件
if exist ai_service.py copy ai_service.py deploy_temp\
if exist config_ai.py copy config_ai.py deploy_temp\

echo.
echo 📊 部署包大小：
for /f %%i in ('dir deploy_temp /s ^| find "個檔案"') do echo     總文件數: %%i
dir deploy_temp /s | find "位元組"

echo.
echo 🌐 部署步驟：
echo.
echo 1. 訪問 https://vercel.com/
echo 2. 使用GitHub帳號登錄
echo 3. 點擊 "New Project"
echo 4. 導入GitHub倉庫（或拖拽deploy_temp文件夾）
echo 5. 配置部署設置：
echo     • Framework Preset: Other
echo     • Root Directory: .
echo     • Build Command: 留空
echo     • Output Directory: .
echo 6. 點擊 "Deploy"
echo.

echo 💡 部署完成後，您將獲得：
echo     • 永久訪問地址（如：https://zhuwei-tech.vercel.app）
echo     • 自動SSL證書
echo     • 全球CDN加速
echo     • 自動部署（每次代碼更新）
echo.

echo 🔗 測試訪問地址示例：
echo     • 企業官網: https://您的域名.vercel.app
echo     • 管理後台: https://您的域名.vercel.app/admin
echo     • AI對話: https://您的域名.vercel.app/chat
echo.

echo ⚠️  注意事項：
echo     • 雲服務器可能不支持SQLite數據庫寫入操作
echo     • 建議使用雲數據庫（如MongoDB Atlas）替代
echo     • AI服務需要配置相應的API密鑰
echo.

echo 📱 立即開始部署？
echo     1. 打開Vercel網站並開始部署
echo     2. 查看詳細部署文檔
echo     3. 返回主菜單

choice /c 123 /n /m "請選擇："
if errorlevel 3 goto menu
if errorlevel 2 goto docs
if errorlevel 1 goto deploy

:deploy
start https://vercel.com/new
echo.
echo 🌐 已打開Vercel部署頁面
echo 💡 請按照上述步驟進行部署
goto end

:docs
echo.
echo 📚 詳細部署文檔：
echo     • Vercel文檔: https://vercel.com/docs
echo     • Python部署指南: https://vercel.com/docs/deployments/deploy-a-python-app
echo.
goto end

:menu
echo.
echo 🔙 返回主菜單
goto end

:end
echo.
echo ✅ 部署工具準備完成
echo 💡 建議先測試本地運行，確保所有功能正常
echo.
pause
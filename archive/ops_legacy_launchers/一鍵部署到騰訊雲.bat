@echo off
chcp 65001 >nul
echo ====================================
echo 築未科技 - 一鍵部署到騰訊雲
echo ====================================
echo.

echo [1/5] 檢查部署準備...
echo.

if not exist "cloudrun_deploy\main.py" (
    echo ❌ 錯誤：找不到部署文件
    echo 請確保 cloudrun_deploy 目錄存在
    pause
    exit /b 1
)

echo ✅ 部署文件檢查完成
echo.

echo [2/5] 檢查Git環境...
git --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  未檢測到Git，請選擇其他部署方式
    echo.
    echo 可選部署方式：
    echo   1. 手動上傳到騰訊雲控制台
    echo   2. 使用Git倉庫部署（需要安裝Git）
    echo.
    set /p choice="請選擇 (1/2): "
    if "%choice%"=="1" goto MANUAL_DEPLOY
    if "%choice%"=="2" goto MANUAL_DEPLOY
    exit /b 0
)

echo ✅ Git環境檢查完成
echo.

echo [3/5] 準備Git倉庫...
cd cloudrun_deploy
if not exist ".git" (
    git init
    git add .
    git commit -m "Initial commit for CloudRun deployment"
    echo ✅ Git倉庫初始化完成
) else (
    echo ✅ Git倉庫已存在
)
cd ..
echo.

echo [4/5] 開啟騰訊雲控制台...
echo.
echo 🌐 即將打開騰訊雲CloudRun控制台
echo.
echo 按照以下步驟操作：
echo.
echo 1. 點擊「新建服務」
echo 2. 選擇「容器型服務」
echo 3. 代碼來源選擇「Git倉庫」
echo 4. 配置服務參數（CPU 0.5核，內存 1GB）
echo 5. 設置環境變量
echo 6. 點擊「部署」
echo.
echo 按任意鍵打開控制台...
pause >nul

start https://tcb.cloud.tencent.com/dev?envId=allen34556-0g1pkqyh2fce7669#/cloudrun

echo.
echo [5/5] 部署說明...
echo.
echo 📝 部署配置參數：
echo   - 服務名稱: zhewei-api
echo   - CPU: 0.5核
echo   - 內存: 1GB
echo   - 最小實例數: 1
echo   - 最大實例數: 3
echo   - 端口: 8080
echo.
echo 📝 環境變量：
echo   PYTHONPATH=/app
echo   PORT=8080
echo   CLOUD_DEPLOYMENT=true
echo.
echo 💡 提示：
echo   - 部署時間約3-5分鐘
echo   - 部署成功後會獲得訪問地址
echo   - 詳細指南請查看 cloudrun_deploy\DEPLOY_GUIDE.md
echo.
echo ====================================
echo 部署準備完成！
echo ====================================
echo.
goto END

:MANUAL_DEPLOY
echo.
echo 📋 手動部署指南：
echo.
echo 1. 打開騰訊雲控制台
echo 2. 上傳 cloudrun_deploy 目錄
echo 3. 配置服務參數
echo 4. 點擊部署
echo.
echo 按任意鍵打開控制台...
pause >nul
start https://tcb.cloud.tencent.com/dev?envId=allen34556-0g1pkqyh2fce7669#/cloudrun

:END
pause

@echo off
chcp 65001 >nul
echo.
echo ================================================
echo           啟動築未科技官方網站
echo ================================================
echo.

REM 檢查Python環境
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 錯誤：未找到Python，請先安裝Python 3.7+
    pause
    exit /b 1
)

REM 檢查虛擬環境
if not exist "venv" (
    echo 📦 創建虛擬環境...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 創建虛擬環境失敗
        pause
        exit /b 1
    )
)

REM 激活虛擬環境
call venv\Scripts\activate.bat

REM 安裝依賴
echo 📦 安裝依賴包...
pip install -r requirements_brain.txt --upgrade
if errorlevel 1 (
    echo ❌ 依賴安裝失敗
    pause
    exit /b 1
)

REM 創建必要的目錄結構
if not exist "templates" mkdir templates
if not exist "templates\admin" mkdir templates\admin
if not exist "static" mkdir static
if not exist "static\css" mkdir static\css
if not exist "static\js" mkdir static\js

REM 啟動網站服務器
echo.
echo 🚀 啟動築未科技官方網站...
echo.
echo 📱 網站地址: http://localhost:8000
echo 💻 管理後台: http://localhost:8000/admin
echo 🤖 AI對話: http://localhost:8000/chat
echo 📊 健康檢查: http://localhost:8000/health
echo.
echo ⚠️  注意：請確保防火牆允許端口8000的訪問
echo.

python website_server.py

REM 如果服務器停止，顯示提示
echo.
echo ⏹️  網站服務已停止
echo.
pause
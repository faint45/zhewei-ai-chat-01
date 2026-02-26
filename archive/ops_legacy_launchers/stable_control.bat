@echo off
chcp 65001 >nul
echo.
echo ================================================
echo     築未科技穩定遠程控制系統
echo ================================================
echo.

:: 設置環境變量
set "SERVER_FILE=stable_server.py"
set "MAX_RETRIES=3"
set "RETRY_DELAY=5"

:: 檢查Python環境
echo 🔍 檢查Python環境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python未安裝或未在PATH中
    pause
    exit /b 1
)

echo ✅ Python環境正常

:: 檢查依賴包
echo 🔍 檢查FastAPI依賴...
pip list | findstr fastapi >nul
if %errorlevel% neq 0 (
    echo ❌ FastAPI未安裝，正在安裝...
    pip install fastapi uvicorn
)

echo ✅ 依賴包檢查完成

:: 檢查端口狀態
echo 🔍 檢查端口狀態 (8000-8010)...
for /L %%i in (8000,1,8010) do (
    netstat -an | findstr ":%%i" >nul
    if %errorlevel% equ 0 (
        echo ❌ 端口%%i被占用
    ) else (
        echo ✅ 端口%%i可用
    )
)

:: 啟動穩定服務器
echo.
echo 🚀 啟動穩定遠程控制服務器...
echo.

set "retry_count=0"
:start_server

if %retry_count% geq %MAX_RETRIES% (
    echo ❌ 服務器啟動失敗，已達最大重試次數
    pause
    exit /b 1
)

if %retry_count% gtr 0 (
    echo ⏳ 第%retry_count%次重試，等待%RETRY_DELAY%秒...
    timeout /t %RETRY_DELAY% /nobreak >nul
)

:: 啟動服務器
start "築未科技穩定服務器" python %SERVER_FILE%

:: 等待服務器啟動
echo ⏳ 等待服務器啟動 (10秒)...
timeout /t 10 /nobreak >nul

:: 檢測服務器是否正常運行
echo 🔗 檢測服務器狀態...
for /L %%i in (8000,1,8010) do (
    curl -s -m 5 http://localhost:%%i/health >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✅ 服務器運行在端口%%i
        echo 🌐 控制面板: http://localhost:%%i
        echo 📊 健康檢查: http://localhost:%%i/health
        goto :server_running
    )
)

:: 服務器啟動失敗
set /a retry_count+=1
echo ❌ 服務器啟動失敗，正在重試...
goto :start_server

:server_running
echo.
echo ✅ 穩定遠程控制系統已啟動

:: 監控服務器狀態
echo.
echo 📊 開始監控服務器狀態...
:monitor_loop
for /L %%i in (8000,1,8010) do (
    curl -s -m 3 http://localhost:%%i/health >nul 2>&1
    if %errorlevel% equ 0 (
        echo %time% - 服務器運行正常 (端口%%i)
    ) else (
        echo %time% - 服務器連接失敗 (端口%%i)
    )
)

timeout /t 30 /nobreak >nul
goto :monitor_loop
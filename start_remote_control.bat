@echo off
chcp 65001 >nul
echo.
echo ================================================
echo     啟動築未科技遠程控制服務器
echo ================================================
echo.

:: 檢查端口8003是否被占用
echo 🔍 檢查端口8003狀態...
netstat -an | findstr ":8003" >nul
if %errorlevel% equ 0 (
    echo ❌ 端口8003已被占用，停止現有進程...
    for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":8003"') do (
        echo 停止進程PID: %%i
        taskkill /PID %%i /F
    )
    timeout /t 2 /nobreak >nul
)

:: 啟動遠程控制服務器
echo 🚀 啟動遠程控制服務器...
start "築未科技遠程控制" python remote_control_server.py

echo.
echo ✅ 服務器啟動中...
echo.

:: 等待服務器啟動
echo ⏳ 等待服務器啟動（5秒）...
timeout /t 5 /nobreak >nul

:: 測試連接
echo 🔗 測試服務器連接...
curl -s -m 10 http://localhost:8003/ >nul
if %errorlevel% equ 0 (
    echo ✅ 服務器連接成功！
    echo 🌐 控制面板: http://localhost:8003
    echo 📊 API文檔: http://localhost:8003/docs
) else (
    echo ❌ 服務器連接失敗，請檢查錯誤信息
)

echo.
echo 💡 使用測試工具: test_remote_control.bat
pause
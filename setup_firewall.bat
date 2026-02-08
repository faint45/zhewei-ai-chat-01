@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技官方網站 - 防火牆配置
echo ================================================
echo.

echo 🔒 配置Windows防火牆允許端口8000...
echo.

REM 檢查是否為管理員權限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️  請以管理員身份運行此腳本！
    echo.
    echo 📋 操作方法：
    echo     1. 右鍵點擊此文件
    echo     2. 選擇"以管理員身份運行"
    echo.
    pause
    exit /b 1
)

echo ✅ 檢測到管理員權限
echo.

echo 🔧 添加防火牆規則...

REM 添加入站規則
netsh advfirewall firewall add rule name="築未科技網站 (TCP入站)" ^
    dir=in action=allow protocol=TCP localport=8000 ^
    description="築未科技官方網站端口8000"

REM 添加出站規則（可選）
netsh advfirewall firewall add rule name="築未科技網站 (TCP出站)" ^
    dir=out action=allow protocol=TCP localport=8000 ^
    description="築未科技官方網站端口8000"

echo.
echo ✅ 防火牆規則配置完成！
echo.

echo 📊 檢查防火牆規則：
netsh advfirewall firewall show rule name="築未科技網站"

echo.
echo 💡 防火牆狀態：
netsh advfirewall show allprofiles state

echo.
echo 🌐 測試端口監聽：
netstat -an | findstr ":8000"

echo.
echo ================================================
pause
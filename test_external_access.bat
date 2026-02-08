@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技官方網站 - 外部訪問測試
echo ================================================
echo.

echo 🔍 檢查網站服務器狀態...
tasklist | findstr "python.exe" >nul
if %errorlevel% equ 0 (
    echo ✅ 網站服務器正在運行
) else (
    echo ❌ 網站服務器未運行
    echo    請先運行: start_website.bat
    goto :end
)

echo.
echo 🌐 檢查本地訪問...
curl -s -o nul -w "本地訪問: %%{http_code}" http://localhost:8000/
if %errorlevel% equ 0 (
    echo ✅ 本地訪問正常
) else (
    echo ❌ 本地訪問失敗
)

echo.
echo 🔧 檢查端口監聽...
netstat -an | findstr ":8000" >nul
if %errorlevel% equ 0 (
    echo ✅ 端口8000正在監聽
) else (
    echo ❌ 端口8000未監聽
)

echo.
echo 🌍 檢查公網IP...
echo     當前公網IP: 
curl -s ifconfig.me

echo.
echo 🔗 檢查DuckDNS解析...
set DUCKDNS_DOMAIN=zhuwei-tech
curl -s -o nul -w "域名解析: %%{http_code}" http://%DUCKDNS_DOMAIN%.duckdns.org:8000/
if %errorlevel% equ 0 (
    echo ✅ DuckDNS域名可訪問
    echo.
    echo 🏢 網站訪問地址：
    echo     🌐 企業官網: http://%DUCKDNS_DOMAIN%.duckdns.org:8000
    echo     🔧 管理後台: http://%DUCKDNS_DOMAIN%.duckdns.org:8000/admin
    echo     🤖 AI大腦: http://%DUCKDNS_DOMAIN%.duckdns.org:8000/chat
    echo.
    echo 🔑 管理員登錄：
    echo     帳號: admin
    echo     密碼: admin123
) else (
    echo ❌ DuckDNS域名無法訪問
    echo.
    echo 🔧 需要配置：
    echo     1. 路由器端口轉發 (運行 setup_port_forward.bat)
    echo     2. 防火牆規則 (運行 setup_firewall.bat)
    echo     3. DuckDNS Token配置 (編輯 duckdns_update.bat)
)

echo.
echo 📱 測試建議：
echo     • 使用手機4G網絡訪問域名
    echo     • 使用不同設備測試
    echo     • 測試所有功能頁面

echo.
:end
echo ================================================
pause
@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技官方網站 - DuckDNS 自動更新腳本
echo ================================================
echo.

REM 設置您的 DuckDNS 配置
set DUCKDNS_TOKEN=553407dd-D7C9-40E9-BE8A-bbdaa71C24B0
set DUCKDNS_DOMAIN=zhuwei-tech

if "%DUCKDNS_TOKEN%"=="553407dd-D7C9-40E9-BE8A-bbdaa71C24B0" (
    echo ⚠️  請先配置 DuckDNS Token
echo.
    echo 📋 配置方法：
    echo 1. 訪問 https://www.duckdns.org/
    echo 2. 使用 Google/GitHub 帳號登錄
    echo 3. 創建子域名：zhuwei-tech
    echo 4. 複製 Token 到下方配置
    echo 5. 編輯此文件，替換 YOUR_TOKEN_HERE
echo.
    echo 💡 示例子域名：
    echo    • zhuwei-tech.duckdns.org
echo.
    goto :end
)

echo 🔄 更新 DuckDNS IP 地址...
echo 域名: %DUCKDNS_DOMAIN%.duckdns.org

echo.
echo 📊 檢測當前公網IP...
curl -s ifconfig.me

echo.
echo 🔗 發送更新請求...
curl -s "https://www.duckdns.org/update?domains=%DUCKDNS_DOMAIN%&token=%DUCKDNS_TOKEN%&ip="

if %errorlevel% equ 0 (
    echo.
    echo ✅ IP 更新成功！
    echo.
    echo 🏢 築未科技官方網站訪問地址：
    echo     🌐 企業官網: http://%DUCKDNS_DOMAIN%.duckdns.org:8000
    echo     🔧 管理後台: http://%DUCKDNS_DOMAIN%.duckdns.org:8000/admin
    echo     🤖 AI大腦: http://%DUCKDNS_DOMAIN%.duckdns.org:8000/chat
    echo     📊 健康檢查: http://%DUCKDNS_DOMAIN%.duckdns.org:8000/health
    echo.
    echo 🔑 管理員登錄信息：
    echo     帳號: admin
    echo     密碼: admin123
    echo.
    echo 💡 外部訪問配置：
    echo 1. 路由器端口轉發: 8000 → 本機IP:8000
    echo 2. 防火牆允許端口8000
    echo 3. 建議設置每10分鐘自動更新
) else (
    echo.
    echo ❌ IP 更新失敗，請檢查：
    echo    • 網絡連接
    echo    • Token配置
    echo    • 域名註冊
)

echo.
echo ================================================
:end
pause
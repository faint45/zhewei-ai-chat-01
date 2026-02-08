@echo off
chcp 65001 >nul
title DuckDNS 動態 DNS 更新

echo.
echo ════════════════════════════════════════════════════
echo  DuckDNS 動態 DNS 更新工具
echo ════════════════════════════════════════════════════
echo.

:: 設置您的 DuckDNS 配置
:: 請修改以下參數為您的實際值

set DOMAIN=zhuwei-tech      :: 您的子域名（不要輸入 .duckdns.org）
set TOKEN=553407dd-d7c9-40e9-be8a-bbdaa71c24b0      :: 您的 DuckDNS Token
set VERBOSE=true          :: 是否顯示詳細信息

:: 檢查是否已配置
if "%DOMAIN%"=="myproject" (
    echo ⚠️  警告：尚未配置 DuckDNS 參數
    echo.
    echo 請按以下步驟配置：
    echo.
    echo 1. 訪問 https://www.duckdns.org/
    echo 2. 註冊並創建子域名（如：myproject）
    echo 3. 獲取您的 Token
    echo 4. 編輯本腳本，修改 DOMAIN 和 TOKEN 變量
    echo.
    pause
    exit /b 1
)

echo DuckDNS 配置：
echo   子域名: %DOMAIN%.duckdns.org
echo   Token: %TOKEN% (已隱藏部分)
echo.

:: 檢查 curl 是否可用
curl --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 錯誤：未檢測到 curl 命令
    echo.
    echo 請確保您的系統已安裝 curl
    echo （Windows 10/11 通常已內置）
    echo.
    pause
    exit /b 1
)

echo [1/3] 獲取當前公網 IP...
for /f "tokens=*" %%i in ('curl -s ifconfig.me 2^>nul') do (
    set CURRENT_IP=%%i
)

if "%CURRENT_IP%"=="" (
    for /f "tokens=*" %%i in ('powershell -Command "Invoke-RestMethod -Uri http://ipinfo.io/ip" 2^>nul') do (
        set CURRENT_IP=%%i
    )
)

if "%CURRENT_IP%"=="" (
    echo ❌ 無法獲取公網 IP 地址
    pause
    exit /b 1
)

echo 公網 IP: %CURRENT_IP%
echo.

echo [2/3] 更新 DuckDNS...
set DUCKDNS_URL=https://www.duckdns.org/update?domains=%DOMAIN%^&token=%TOKEN%^&ip=%CURRENT_IP%

if "%VERBOSE%"=="true" (
    echo 請求 URL: %DUCKDNS_URL%
    echo.
)

for /f "tokens=*" %%i in ('curl -s "%DUCKDNS_URL%"') do (
    set RESPONSE=%%i
)

echo DuckDNS 響應: %RESPONSE%
echo.

echo [3/3] 檢查更新結果...
if "%RESPONSE%"=="OK" (
    echo ✅ DDNS 更新成功！
    echo.
    echo 您的網站現在可以通過以下地址訪問：
    echo   網站首頁:  http://%DOMAIN%.duckdns.org:8000
    echo   AI 對話:    http://%DOMAIN%.duckdns.org:8000/chat
    echo   管理後台:  http://%DOMAIN%.duckdns.org:8000/admin
    echo   聯繫我們:  http://%DOMAIN%.duckdns.org:8000/contact
    echo   遠程控制:  http://%DOMAIN%.duckdns.org:8005
    echo.
) else if "%RESPONSE%"=="KO" (
    echo ❌ DDNS 更新失敗
    echo 可能的原因：
    echo   - Token 錯誤
    echo   - 子域名不存在
    echo   - 網絡連接問題
    echo.
) else (
    echo ⚠️  未知響應: %RESPONSE%
    echo.
)

set /p create_task="是否創建定時任務（每小時自動更新）？(Y/N): "
if /i "%create_task%"=="Y" (
    echo.
    echo 正在創建定時任務...
    echo.

    set TASK_NAME=築未科技DDNS更新
    set SCRIPT_PATH=%~f0
    set TASK_TRIGGER=HOURLY

    :: 刪除舊任務（如果存在）
    schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

    :: 創建新任務
    schtasks /Create /TN "%TASK_NAME%" /TR "\"%SCRIPT_PATH%\"" /SC %TASK_TRIGGER% /F >nul 2>&1

    if %errorlevel% equ 0 (
        echo ✅ 定時任務創建成功
        echo    任務名稱: %TASK_NAME%
        echo    執行頻率: 每小時
        echo.
        echo 💡 提示：您可以在「任務計劃程序」中查看和管理此任務
        echo.
    ) else (
        echo ❌ 定時任務創建失敗
        echo    請以管理員權限運行此腳本
        echo.
    )
)

echo ════════════════════════════════════════════════════
echo.
echo 完成後的完整部署步驟：
echo.
echo 1. 運行此腳本更新 DDNS
echo 2. 配置路由器端口轉發（運行 get_network_info.bat）
echo 3. 訪問 http://%DOMAIN%.duckdns.org:8000 測試
echo.
pause

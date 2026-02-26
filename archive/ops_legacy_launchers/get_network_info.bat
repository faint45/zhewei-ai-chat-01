@echo off
chcp 65001 >nul
title 獲取網絡配置信息

echo.
echo ════════════════════════════════════════════════════
echo  網絡配置信息 - 用於路由器端口轉發設置
echo ════════════════════════════════════════════════════
echo.

echo [1/5] 獲取本機 IP 地址...
ipconfig | findstr "IPv4"
echo.

echo [2/5] 獲取默認網關（路由器地址）...
ipconfig | findstr "Default Gateway"
echo.

echo [3/5] 檢查本地服務端口...
netstat -ano | findstr ":8000" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 端口 8000（網站服務器）正在運行
) else (
    echo ❌ 端口 8000（網站服務器）未運行
)

netstat -ano | findstr ":8005" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 端口 8005（遠程控制）正在運行
) else (
    echo ❌ 端口 8005（遠程控制）未運行
)
echo.

echo [4/5] 獲取公網 IP 地址...
echo 正在查詢...
for /f "tokens=2 delims=: " %%a in ('curl -s ifconfig.me 2^>nul') do (
    set PUBLIC_IP=%%a
    goto :found_ip
)

:curl_fail
for /f "tokens=1" %%a in ('powershell -Command "Invoke-RestMethod -Uri http://ipinfo.io/ip" 2^>nul') do (
    set PUBLIC_IP=%%a
    goto :found_ip
)

echo ❌ 無法獲取公網 IP
goto :skip_ip

:found_ip
echo 公網 IP: %PUBLIC_IP%
:skip_ip
echo.

echo [5/5] 生成端口轉發配置...
echo.
echo ════════════════════════════════════════════════════
echo  路由器端口轉發配置表
echo ════════════════════════════════════════════════════
echo.
echo ┌─────────────┬──────────┬────────────────────┬───────┐
echo │ 外部端口    │ 內部端口 │ 內部 IP 地址       │ 協議  │
echo ├─────────────┼──────────┼────────────────────┼───────┤
echo │ 8000        │ 8000     │ [本機 IPv4 地址]   │ TCP   │
echo │ 8005        │ 8005     │ [本機 IPv4 地址]   │ TCP   │
echo └─────────────┴──────────┴────────────────────┴───────┘
echo.
echo 💡 設置步驟：
echo 1. 訪問路由器管理頁面（通常是 192.168.1.1）
echo 2. 登錄管理員賬號
echo 3. 找到「端口轉發」或「虛擬服務器」設置
echo 4. 添加上述配置表的規則
echo 5. 保存並重啟路由器（如需要）
echo.
echo ⚠️  注意事項：
echo - 請將 [本機 IPv4 地址] 替換為上方的實際 IP
echo - 某些運營商可能封鎖 8000/8005 端口
echo - 如無法訪問，可嘗試使用 80/443 端口
echo.

echo ════════════════════════════════════════════════════
echo  部署完成後的訪問地址
echo ════════════════════════════════════════════════════
echo.
if defined PUBLIC_IP (
    echo 網站首頁：  http://%PUBLIC_IP%:8000
    echo AI 對話：    http://%PUBLIC_IP%:8000/chat
    echo 管理後台：  http://%PUBLIC_IP%:8000/admin
    echo 聯繫我們：  http://%PUBLIC_IP%:8000/contact
    echo 遠程控制：  http://%PUBLIC_IP%:8005
) else (
    echo 網站首頁：  http://[您的公網IP]:8000
    echo AI 對話：    http://[您的公網IP]:8000/chat
    echo 管理後台：  http://[您的公網IP]:8000/admin
    echo 聯繫我們：  http://[您的公網IP]:8000/contact
    echo 遠程控制：  http://[您的公網IP]:8005
)
echo.

set /p test="是否測試端口連接性？(Y/N): "
if /i "%test%"=="Y" (
    echo.
    echo 正在測試端口連接性...
    powershell -Command "Test-NetConnection -ComputerName google.com -Port 80" >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✅ 網絡連接正常
    ) else (
        echo ❌ 網絡連接異常
    )
)

echo.
echo 按任意鍵打開路由器登錄頁面...
pause >nul

:: 嘗試打開常見的路由器地址
start http://192.168.1.1
timeout /t 1 >nul
start http://192.168.0.1

echo.
echo ✅ 已嘗試打開路由器管理頁面
echo    如果無法訪問，請檢查您的路由器地址
echo.
pause

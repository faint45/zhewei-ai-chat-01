@echo off
chcp 65001 >nul
title DuckDNS 自動配置向導

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║          DuckDNS 自動配置向導 - 築未科技系統            ║
╚════════════════════════════════════════════════════════════╝
echo.

:: 檢查本地服務是否運行
echo [檢查] 正在檢查本地服務...
netstat -ano | findstr ":8000" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  警告：端口 8000 似乎未運行
    echo    建議先運行：start_all_services.bat
    echo.
)

netstat -ano | findstr ":8005" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  警告：端口 8005 似乎未運行
    echo    建議先運行：start_all_services.bat
    echo.
)

:: 獲取本機 IP
echo [步驟 1/6] 獲取本機 IP 地址...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr "IPv4"') do (
    for /f "tokens=2" %%b in ("%%a") do set LOCAL_IP=%%b
)
if defined LOCAL_IP (
    echo ✅ 本機 IP: %LOCAL_IP%
) else (
    echo ❌ 無法獲取本機 IP
)
echo.

:: 獲取公網 IP
echo [步驟 2/6] 獲取公網 IP 地址...
for /f "tokens=*" %%i in ('curl -s ifconfig.me 2^>nul') do (
    set PUBLIC_IP=%%i
)
if defined PUBLIC_IP (
    echo ✅ 公網 IP: %PUBLIC_IP%
) else (
    echo ⚠️  無法獲取公網 IP
)
echo.

:: 輸入 DuckDNS 配置
echo [步驟 3/6] 配置 DuckDNS
echo.
echo 📌 請按照以下步驟操作：
echo.
echo 1. 訪問 https://www.duckdns.org/
echo 2. 登錄或註冊帳號
echo 3. 創建一個子域名（例如：zhuwei-tech）
echo 4. 在頁面頂部複製您的 Token
echo.
echo ════════════════════════════════════════════════════
echo.

:: 輸入子域名
:input_domain
set /p DOMAIN="請輸入您的 DuckDNS 子域名（不含 .duckdns.org）: "
if "%DOMAIN%"=="" (
    echo ❌ 子域名不能為空
    goto input_domain
)
echo ✅ 子域名: %DOMAIN%.duckdns.org
echo.

:: 輸入 Token
:input_token
set /p TOKEN="請輸入您的 DuckDNS Token: "
if "%TOKEN%"=="" (
    echo ❌ Token 不能為空
    goto input_token
)
echo ✅ Token: 已設置（已隱藏部分）
echo.

:: 測試 DDNS 連接
echo [步驟 4/6] 測試 DDNS 連接...
set DUCKDNS_URL=https://www.duckdns.org/update?domains=%DOMAIN%^&token=%TOKEN%^&ip=%PUBLIC_IP%
for /f "tokens=*" %%i in ('curl -s "%DUCKDNS_URL%"') do (
    set RESPONSE=%%i
)

if "%RESPONSE%"=="OK" (
    echo ✅ DDNS 測試成功！
    echo    DuckDNS 響應: OK
) else if "%RESPONSE%"=="KO" (
    echo ❌ DDNS 測試失敗！
    echo    DuckDNS 響應: KO
    echo.
    echo 可能的原因：
    echo   - Token 錯誤
    echo   - 子域名不存在
    echo   - 網絡連接問題
    echo.
    set /p retry="是否重新輸入？(Y/N): "
    if /i "%retry%"=="Y" (
        goto input_domain
    )
    goto end
) else (
    echo ⚠️  未知響應: %RESPONSE%
)
echo.

:: 更新 ddns_update.bat
echo [步驟 5/6] 更新配置文件...
echo 正在備份原文件...
copy ddns_update.bat ddns_update.bat.backup >nul 2>&1

echo 正在更新配置...
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo title DuckDNS 動態 DNS 更新
    echo.
    echo :: DuckDNS 配置
    echo set DOMAIN=%DOMAIN%
    echo set TOKEN=%TOKEN%
    echo set VERBOSE=true
    echo.
    echo :: 其餘代碼保持不變...
) > ddns_update_new.bat

:: 追加原文件的其餘部分
more +8 ddns_update.bat >> ddns_update_new.bat

:: 替換原文件
move /Y ddns_update_new.bat ddns_update.bat >nul 2>&1
echo ✅ 配置文件已更新
echo.

:: 創建定時任務
echo [步驟 6/6] 設置定時更新任務...
echo.
echo DDNS 需要定期更新以保持域名指向正確的 IP。
echo 建議設置為每小時自動更新。
echo.

set /p create_task="是否創建定時任務（每小時自動更新）？(Y/N): "
if /i "%create_task%"=="Y" (
    set TASK_NAME=築未科技DDNS更新
    set SCRIPT_PATH=%~f0
    set TASK_TRIGGER=HOURLY

    echo 正在創建定時任務...
    :: 刪除舊任務
    schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

    :: 創建新任務
    schtasks /Create /TN "%TASK_NAME%" /TR "cd /d \"%~dp0\" && ddns_update.bat" /SC %TASK_TRIGGER% /F >nul 2>&1

    if %errorlevel% equ 0 (
        echo ✅ 定時任務創建成功
        echo    任務名稱: %TASK_NAME%
        echo    執行頻率: 每小時
        echo.
        echo 💡 提示：您可以在「任務計劃程序」中查看和管理此任務
    ) else (
        echo ❌ 定時任務創建失敗
        echo    請以管理員權限運行此腳本
        echo.
        echo 您可以手動創建任務：
        echo   schtasks /Create /TN "築未科技DDNS更新" /TR "ddns_update.bat" /SC HOURLY /F
    )
)
echo.

:: 顯示配置摘要
echo ════════════════════════════════════════════════════
echo  配置完成！
echo ════════════════════════════════════════════════════
echo.
echo 📋 配置摘要：
echo.
echo   DuckDNS 子域名: %DOMAIN%.duckdns.org
echo   本機 IP:         %LOCAL_IP%
echo   公網 IP:         %PUBLIC_IP%
echo.
echo 🌐 訪問地址：
echo.
echo   網站首頁:      http://%DOMAIN%.duckdns.org:8000
echo   AI 對話:        http://%DOMAIN%.duckdns.org:8000/chat
echo   管理後台:      http://%DOMAIN%.duckdns.org:8000/admin
echo   聯繫我們:      http://%DOMAIN%.duckdns.org:8000/contact
echo   遠程控制:      http://%DOMAIN%.duckdns.org:8005
echo.

:: 提示配置端口轉發
echo ⚠️  重要提示：
echo.
echo 您還需要配置路由器端口轉發才能從外網訪問！
echo.
echo 請運行以下腳本獲取端口轉發配置：
echo   get_network_info.bat
echo.
echo 或按照以下步驟手動配置：
echo   1. 訪問路由器管理頁面（通常是 192.168.1.1）
echo   2. 找到「端口轉發」設置
echo   3. 添加以下規則：
echo      外部端口 8000 → 內部端口 8000 → 本機 IP (%LOCAL_IP%)
echo      外部端口 8005 → 內部端口 8005 → 本機 IP (%LOCAL_IP%)
echo.

set /p open_guide="是否打開詳細的 DuckDNS 配置指南？(Y/N): "
if /i "%open_guide%"=="Y" (
    if exist "duckdns_setup_guide.md" (
        start duckdns_setup_guide.md
    ) else (
        echo ❌ 未找到配置指南文檔
    )
)

set /p test_now="是否立即測試 DDNS 連接？(Y/N): "
if /i "%test_now%"=="Y" (
    echo.
    echo 正在測試連接...
    start http://%DOMAIN%.duckdns.org:8000
    echo.
    echo 如果無法訪問，請檢查：
    echo   1. 路由器端口轉發是否已配置
    echo   2. 防火牆是否允許端口訪問
    echo   3. 本地服務是否正在運行
)

:end
echo.
echo ════════════════════════════════════════════════════
echo.
echo ✅ DuckDNS 配置完成！
echo.
echo 📌 後續步驟：
echo   1. 配置路由器端口轉發（運行 get_network_info.bat）
echo   2. 從外網測試訪問
echo   3. 配置防火牆規則以增強安全性
echo.
pause

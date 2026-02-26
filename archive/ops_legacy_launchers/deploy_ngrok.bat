@echo off
chcp 65001 >nul
title 使用 Ngrok 部署到網絡

echo.
echo ════════════════════════════════════════════════════
echo  使用 Ngrok 內網穿透部署到網絡
echo ════════════════════════════════════════════════════
echo.

:: 檢查 Ngrok 是否已安裝
where ngrok >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 錯誤：未檢測到 Ngrok
    echo.
    echo 請按照以下步驟安裝 Ngrok：
    echo 1. 訪問 https://ngrok.com/
    echo 2. 註冊賬號並下載 Ngrok
    echo 3. 解壓縮到系統 PATH 中的目錄
    echo 4. 運行：ngrok config add-authtoken YOUR_TOKEN
    echo.
    pause
    exit /b 1
)

echo ✅ 檢測到 Ngrok 已安裝
echo.

:: 檢查本地服務是否運行
echo [1/4] 檢查本地服務...
powershell -Command "Test-NetConnection -ComputerName localhost -Port 8000" | findstr "TcpTestSucceeded" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  警告：端口 8000 似乎未運行
    echo    請先運行：start_all_services.bat
    echo.
    set /p continue="是否繼續啟動 Ngrok？(Y/N): "
    if /i not "%continue%"=="Y" exit /b 0
)

powershell -Command "Test-NetConnection -ComputerName localhost -Port 8005" | findstr "TcpTestSucceeded" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  警告：端口 8005 似乎未運行
    echo    請先運行：start_all_services.bat
    echo.
)

echo ✅ 本地服務檢查完成
echo.

:: 啟動 Ngrok 穿透
echo [2/4] 啟動 Ngrok 穿透服務...
echo.

echo 正在啟動 Ngrok 穿透端口 8000...
start "Ngrok - 網站服務器 [8000]" ngrok http 8000 --log=stdout

timeout /t 3 >nul

echo 正在啟動 Ngrok 穿透端口 8005...
start "Ngrok - 遠程控制 [8005]" ngrok http 8005 --log=stdout

timeout /t 2 >nul

echo.
echo [3/4] 等待 Ngrok 啟動...
timeout /t 5 >nul

echo.
echo [4/4] 獲取公網地址...
echo.

:: 嘗試獲取 Ngrok URL
echo 正在查詢 Ngrok URL...
echo.
echo 💡 提示：請查看 Ngrok 窗口中的 "Forwarding" 信息
echo    格式：https://xxxx-xx-xx-xx-xx.ngrok-free.app
echo.

echo ════════════════════════════════════════════════════
echo  Ngrok 已啟動！
echo ════════════════════════════════════════════════════
echo.
echo 📌 使用方式：
echo.
echo 1. 查看 "Ngrok - 網站服務器" 窗口
echo    找到 "Forwarding" 行的 URL
echo.
echo 2. 查看 "Ngrok - 遠程控制" 窗口
echo    找到 "Forwarding" 行的 URL
echo.
echo 3. 使用 Ngrok 提供的 URL 訪問您的服務
echo.
echo ⚠️  重要提示：
echo    - Ngrok URL 在每次啟動時會變化
echo    - 需要保持 Ngrok 窗口運行
echo    - 免費版有速率限制
echo.
echo 按任意鍵打開 Ngrok 控制台...
pause >nul

start https://dashboard.ngrok.com/tunnels

echo.
echo ✅ 部署完成！
echo.
pause

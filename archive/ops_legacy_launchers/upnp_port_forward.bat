@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技 - UPnP自動端口轉發工具
echo ================================================
echo.

echo 🔧 嘗試使用UPnP自動配置端口轉發...
echo.

echo 📡 檢測UPnP設備...
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr "IPv4"') do set LOCAL_IP=%%i
set LOCAL_IP=%LOCAL_IP: =%
echo     本機IP: %LOCAL_IP%
echo.

echo 🌐 嘗試自動端口映射...
echo     • 外部端口: 8000
echo     • 內部IP: %LOCAL_IP%
echo     • 內部端口: 8000
echo.

echo 💡 如果路由器支持UPnP，將自動配置端口轉發
echo.

echo ⚠️  注意：此功能需要路由器啟用UPnP
echo     如果失敗，請手動配置路由器或使用其他方案
echo.

REM 使用PowerShell嘗試UPnP配置
powershell -Command "
Try {
    # 嘗試使用UPnP進行端口映射
    $externalPort = 8000
    $internalPort = 8000
    $internalIP = '%LOCAL_IP%'
    $protocol = 'TCP'
    
    # 使用netsh進行端口映射嘗試
    $result = netsh interface portproxy add v4tov4 listenport=$externalPort listenaddress=0.0.0.0 connectport=$internalPort connectaddress=$internalIP
    if ($LASTEXITCODE -eq 0) {
        Write-Host '✅ UPnP端口轉發配置成功！' -ForegroundColor Green
    } else {
        Write-Host '❌ UPnP自動配置失敗，需要手動路由器配置' -ForegroundColor Red
    }
} Catch {
    Write-Host '❌ UPnP功能不可用' -ForegroundColor Red
}
"

echo.
echo 📋 替代方案：
echo     1. 聯繫網絡管理員配置路由器
echo     2. 使用雲服務器部署（推薦）
echo     3. 使用Ngrok等內網穿透工具
echo.

pause
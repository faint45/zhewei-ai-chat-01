@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技官方網站 - 端口轉發配置指南
echo ================================================
echo.

echo 📋 路由器端口轉發配置步驟：
echo.

echo 1. 🔍 查找本機IP地址：
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr "IPv4"') do echo    本機IP: %%i
echo.

echo 2. 🌐 登錄路由器管理界面：
echo     地址: http://192.168.1.1 (或查看路由器標籤)
echo     帳號/密碼: 路由器背面標籤
echo.

echo 3. ⚙️  配置端口轉發：
echo     • 服務名稱: 築未科技網站
echo     • 協議: TCP
echo     • 外部端口: 8000
echo     • 內部IP: 上面顯示的本機IP
echo     • 內部端口: 8000
echo.

echo 4. 🔒 配置防火牆：
echo     netsh advfirewall firewall add rule name="築未科技網站" ^
echo         dir=in action=allow protocol=TCP localport=8000
echo.

echo 5. ✅ 測試外部訪問：
echo     http://您的域名.duckdns.org:8000
echo.

echo 📱 路由器品牌配置位置：
echo     • TP-Link: 轉發規則 → 虛擬服務器
echo     • ASUS: 高級設置 → 外部網絡 → 端口轉發
echo     • Netgear: 高級 → 端口轉發/端口觸發
echo     • D-Link: 高級 → 端口轉發
echo.

echo 💡 重要提示：
echo     • 確保網站服務器正在運行 (start_website.bat)
echo     • 完成DuckDNS配置後再測試
echo     • 建議使用手機4G網絡測試外部訪問
echo.

pause
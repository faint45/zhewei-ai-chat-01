@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技 - 路由器信息查找工具
echo ================================================
echo.

echo 📡 正在檢測網絡信息...
echo.

echo 🌐 默認網關（通常是路由器IP）：
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr "默認網關"') do echo     %%i
echo.

echo 🔍 建議嘗試的登錄地址：
echo     http://192.168.1.1
echo     http://192.168.0.1
echo     http://192.168.31.1
echo     http://10.0.0.1
echo.

echo 🔑 常見默認賬號密碼：
echo     • TP-Link: admin / admin
echo     • ASUS: admin / admin  
echo     • Netgear: admin / password
echo     • D-Link: admin / (空白)
echo     • 小米: (空白) / (空白)
echo.

echo 💡 如果忘記密碼：
echo     1. 查看路由器背面標籤
echo     2. 嘗試重置路由器（按住Reset按鈕10秒）
echo     3. 重置後使用默認密碼登錄
echo.

echo ⚠️  重置路由器會清除所有設置，請謹慎操作！
echo.

pause
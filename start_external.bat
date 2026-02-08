@echo off
echo ========================================
echo    築未科技大腦 - 外網訪問啟動腳本
echo ========================================

REM 設置環境變量
set AI_MODEL_TYPE=ollama
set OLLAMA_MODEL=gemma3:4b

echo.
echo 📊 網絡配置信息：
echo 本地IP地址: 192.168.1.102
echo 服務端口: 8000
echo.

echo 🌐 訪問方式：
echo 1. 局域網內訪問： http://192.168.1.102:8000
echo 2. 路由器端口轉發：配置外部端口8000到192.168.1.102:8000
echo 3. 使用ngrok等內網穿透工具
echo.

echo 🔧 檢查防火牆規則...
netsh advfirewall firewall show rule name="築未科技大腦" 2>nul
if %errorlevel% neq 0 (
    echo ⚠️  防火牆規則不存在，需要管理員權限創建
    echo 💡 請以管理員身份運行此腳本或手動創建防火牆規則
)

echo.
echo 🚀 啟動築未科技大腦服務...
python brain_server.py

pause
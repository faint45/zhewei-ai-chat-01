@echo off
chcp 65001 >nul
echo.
echo ================================================
echo     築未科技AI远程控制测试工具
echo ================================================
echo.

:: 检查远程控制服务是否运行
echo 🔍 检查远程控制服务状态...
netstat -an | findstr ":8003" >nul
if %errorlevel% equ 0 (
    echo ✅ 远程控制服务正在运行 (端口8003)
) else (
    echo ❌ 远程控制服务未运行
    echo 🔧 请先启动服务：python remote_control_server.py
    pause
    exit /b 1
)

:: 测试指令发送
echo.
echo 🚀 开始测试远程指令...
echo.

:: 测试系统指令
echo 📋 测试系统指令：ping google.com
curl -X POST http://localhost:8003/api/command ^
  -H "Content-Type: application/json" ^
  -d "{\"type\": \"sys\", \"command\": \"ping google.com\"}"
echo.

:: 测试AI指令
echo 📋 测试AI指令：解释什么是机器学习
curl -X POST http://localhost:8003/api/command ^
  -H "Content-Type: application/json" ^
  -d "{\"type\": \"ai\", \"command\": \"解释什么是机器学习\"}"
echo.

:: 测试Python版本
echo 📋 测试系统指令：python --version
curl -X POST http://localhost:8003/api/command ^
  -H "Content-Type: application/json" ^
  -d "{\"type\": \"sys\", \"command\": \"python --version\"}"
echo.

:: 测试代码分析
echo 📋 测试AI指令：分析Python代码
curl -X POST http://localhost:8003/api/command ^
  -H "Content-Type: application/json" ^
  -d "{\"type\": \"ai\", \"command\": \"请帮我分析这个Python代码\"}"
echo.

echo.
echo ✅ 测试指令已发送到远程控制服务
echo.
echo 🌐 查看结果：
echo     • 本地访问：http://localhost:8003
echo     • 实时查看指令执行状态
echo     • 查看AI模型回应
echo.
echo 💡 更多指令请查看：test_instructions.txt
pause
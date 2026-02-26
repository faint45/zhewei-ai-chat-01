@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技 - 云端地址配置更新
echo ================================================
echo.

echo 请输入您的腾讯云CloudBase访问地址
echo.

set /p CLOUD_URL="访问地址（例如：https://zhewei-api-xxx.service.tcloudbase.com）："

if "%CLOUD_URL%"=="" (
    echo ❌ 访问地址不能为空
    pause
    exit /b 1
)

echo.
echo 正在更新配置文件...
echo.

REM 更新Telegram机器人配置
if exist telegram_bot.py (
    echo ✅ 更新 telegram_bot.py
    powershell -Command "(Get-Content telegram_bot.py) -replace 'self\.server_url = .*', 'self.server_url = \"%CLOUD_URL%\"' | Set-Content telegram_bot.py"
)

REM 更新Discord机器人配置
if exist discord_bot.py (
    echo ✅ 更新 discord_bot.py
    powershell -Command "(Get-Content discord_bot.py) -replace 'self\.server_url = .*', 'self.server_url = \"%CLOUD_URL%\"' | Set-Content discord_bot.py"
)

REM 更新remote_control.html
if exist remote_control.html (
    echo ✅ 更新 remote_control.html
    powershell -Command "(Get-Content remote_control.html) -replace 'const API_BASE_URL = .*', 'const API_BASE_URL = ''%CLOUD_URL%''' | Set-Content remote_control.html"
)

REM 更新remote_brain.html
if exist remote_brain.html (
    echo ✅ 更新 remote_brain.html
    powershell -Command "(Get-Content remote_brain.html) -replace 'const API_BASE_URL = .*', 'const API_BASE_URL = ''%CLOUD_URL%''' | Set-Content remote_brain.html"
)

REM 更新zhewei-ai-chat-live.html
if exist zhewei-ai-chat-live.html (
    echo ✅ 更新 zhewei-ai-chat-live.html
    powershell -Command "(Get-Content zhewei-ai-chat-live.html) -replace 'const API_BASE_URL = .*', 'const API_BASE_URL = ''%CLOUD_URL%''' | Set-Content zhewei-ai-chat-live.html"
)

echo.
echo ================================================
echo ✅ 配置更新完成！
echo ================================================
echo.
echo 已将以下地址更新为：%CLOUD_URL%
echo.
echo 更新的文件：
echo   - telegram_bot.py
echo   - discord_bot.py
echo   - remote_control.html
echo   - remote_brain.html
echo   - zhewei-ai-chat-live.html
echo.
echo 💡 提示：
echo   1. 重启机器人以使用新配置
echo   2. 刷新浏览器以加载新前端
echo   3. 测试API连接是否正常
echo.
pause
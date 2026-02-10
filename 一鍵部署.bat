@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技 - 一键部署系统
echo ================================================
echo.

echo 请选择部署平台：
echo.
echo [1] 腾讯云CloudBase  (推荐国内)
echo [2] Vercel           (推荐国际)
echo [3] Railway          (开发者友好)
echo [4] 本地启动         (快速测试)
echo.
echo [5] 查看部署状态
echo [6] 部署帮助
echo.

choice /c 123456 /n /m "请选择（1-6）："

if errorlevel 6 goto help
if errorlevel 5 goto status
if errorlevel 4 goto local
if errorlevel 3 goto railway
if errorlevel 2 goto vercel
if errorlevel 1 goto tencent

:tencent
cls
echo ================================================
echo     部署到腾讯云CloudBase
echo ================================================
echo.
echo 正在打开腾讯云控制台...
echo.
start "" "https://console.cloud.tencent.com/tcb/cloudrun"
echo.
echo 已打开腾讯云控制台，请按照指引操作：
echo.
echo 1. 创建CloudBase环境：zhewei-ai-system
echo 2. 创建CloudRun服务：zhewei-api
echo 3. 上传项目代码（确保包含Dockerfile）
echo 4. 配置环境变量（参考 ENV_VARS_GUIDE.md）
echo 5. 部署并测试
echo.
echo 详细指南：CLOUDBASE_DEPLOYMENT_GUIDE.md
echo.
pause
goto end

:vercel
cls
echo ================================================
echo     部署到Vercel
echo ================================================
echo.
echo 正在打开Vercel...
echo.
start "" "https://vercel.com/new"
echo.
echo 已打开Vercel，请按照指引操作：
echo.
echo 1. 登录Vercel账号（推荐使用GitHub登录）
echo 2. 导入项目或选择Git仓库
echo 3. 配置构建设置
echo 4. 部署项目
echo.
pause
goto end

:railway
cls
echo ================================================
echo     部署到Railway
echo ================================================
echo.
echo 正在打开Railway...
echo.
start "" "https://railway.app/new"
echo.
echo 已打开Railway，请按照指引操作：
echo.
echo 1. 登录Railway账号
echo 2. 连接GitHub仓库
echo 3. 选择项目并配置
echo 4. 自动部署
echo.
pause
goto end

:local
cls
echo ================================================
echo     本地启动
echo ================================================
echo.
echo 正在检查本地环境...
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装，请先安装Python 3.8+
    pause
    goto end
)
echo ✅ Python已安装

REM 检查Ollama
ollama --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Ollama未运行，建议启动
    echo    运行：start_ollama.bat
) else (
    echo ✅ Ollama已安装
)

echo.
echo 选择启动方式：
echo [1] 启动远程控制服务器
echo [2] 启动Telegram机器人
echo [3] 启动Discord机器人
echo [4] 启动所有服务
echo [5] 返回主菜单
echo.

choice /c 12345 /n /m "请选择（1-5）："

if errorlevel 5 goto main_menu
if errorlevel 4 goto start_all
if errorlevel 3 goto start_discord
if errorlevel 2 goto start_telegram
if errorlevel 1 goto start_server

:start_server
echo.
echo 正在启动远程控制服务器...
start cmd /k "python remote_control_server.py"
echo ✅ 服务器已启动
goto end

:start_telegram
echo.
echo 正在启动Telegram机器人...
start cmd /k "python telegram_bot.py"
echo ✅ Telegram机器人已启动
goto end

:start_discord
echo.
echo 正在启动Discord机器人...
start cmd /k "python discord_bot.py"
echo ✅ Discord机器人已启动
goto end

:start_all
echo.
echo 正在启动所有服务...
echo.
echo [1/3] 启动远程控制服务器...
start cmd /k "python remote_control_server.py"
timeout /t 2 /nobreak >nul
echo [2/3] 启动Telegram机器人...
start cmd /k "python telegram_bot.py"
timeout /t 2 /nobreak >nul
echo [3/3] 启动Discord机器人...
start cmd /k "python discord_bot.py"
echo.
echo ✅ 所有服务已启动
goto end

:status
cls
echo ================================================
echo     部署状态
echo ================================================
echo.
echo 正在读取部署状态...
if exist DEPLOYMENT_STATUS.md (
    type DEPLOYMENT_STATUS.md
) else (
    echo ❌ 未找到部署状态文件
)
echo.
pause
goto end

:help
cls
echo ================================================
echo     部署帮助
echo ================================================
echo.
echo 📚 可用的部署文档：
echo.
echo   1. 快速开始指南
echo      文件：QUICK_START.md
echo.
echo   2. 腾讯云详细部署指南
echo      文件：CLOUDBASE_DEPLOYMENT_GUIDE.md
echo.
echo   3. 完整部署说明
echo      文件：DEPLOY_INSTRUCTIONS.md
echo.
echo   4. 环境变量配置指南
echo      文件：ENV_VARS_GUIDE.md
echo.
echo   5. 部署状态记录
echo      文件：DEPLOYMENT_STATUS.md
echo.
echo 🌐 云平台链接：
echo.
echo   - 腾讯云CloudBase
echo     https://console.cloud.tencent.com/tcb
echo.
echo   - Vercel
echo     https://vercel.com/dashboard
echo.
echo   - Railway
echo     https://dashboard.railway.app
echo.
choice /c YN /n /m "是否打开快速开始指南？(Y/N)"
if errorlevel 2 goto end
if errorlevel 1 goto open_guide

:open_guide
start "" "QUICK_START.md"
goto end

:main_menu
cls
goto :eof

:end
echo.
echo ================================================
echo 💡 提示
echo ================================================
echo.
echo 部署完成后：
echo 1. 测试API：python test_cloud_api.py https://your-domain.com
echo 2. 更新配置：update_cloud_config.bat
echo 3. 重启服务：重启所有机器人
echo.
echo 访问文档获取更多帮助
echo.
pause
@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技 - 腾讯云CloudBase部署助手
echo ================================================
echo.

echo 🚀 开始部署到腾讯云CloudBase
echo.
echo 本助手将引导您完成以下步骤：
echo.
echo 1️⃣  准备部署文件
echo 2️⃣  登录腾讯云控制台
echo 3️⃣  创建CloudBase环境
echo 4️⃣  部署CloudRun服务
echo 5️⃣  配置环境变量
echo 6️⃣  测试部署结果
echo.

pause
cls

echo ================================================
echo 第一步：检查部署文件
echo ================================================
echo.

echo 检查必要文件...

set READY=true

if not exist Dockerfile (
    echo ❌ 缺少 Dockerfile
    set READY=false
) else (
    echo ✅ Dockerfile 已准备
)

if not exist requirements_ai.txt (
    echo ❌ 缺少 requirements_ai.txt
    set READY=false
) else (
    echo ✅ requirements_ai.txt 已准备
)

if not exist remote_control_server.py (
    echo ❌ 缺少 remote_control_server.py
    set READY=false
) else (
    echo ✅ remote_control_server.py 已准备
)

if not exist CLOUDBASE_DEPLOYMENT_GUIDE.md (
    echo ❌ 缺少 CLOUDBASE_DEPLOYMENT_GUIDE.md
    set READY=false
) else (
    echo ✅ CLOUDBASE_DEPLOYMENT_GUIDE.md 已准备
)

echo.
if "%READY%"=="false" (
    echo ❌ 部署文件不完整，请检查
    pause
    exit /b 1
)

echo ✅ 所有部署文件已准备就绪
echo.

pause
cls

echo ================================================
echo 第二步：打开腾讯云控制台
echo ================================================
echo.

echo 您需要在腾讯云控制台完成部署
echo.
echo 📝 控制台地址：
echo   https://console.cloud.tencent.com/tcb/cloudrun
echo.
echo 💡 如果没有腾讯云账号，请先注册：
echo   https://cloud.tencent.com/
echo.

choice /c YN /n /m "是否打开腾讯云控制台？(Y/N)"
if errorlevel 2 goto deploy_guide
if errorlevel 1 goto open_console

:open_console
start "" "https://console.cloud.tencent.com/tcb/cloudrun"

:deploy_guide
cls
echo ================================================
echo 第三步：部署指导
echo ================================================
echo.

echo 请按照以下步骤在控制台操作：
echo.
echo 1️⃣  创建CloudBase环境
echo    - 点击"新建环境"
echo    - 环境名称：zhewei-ai-system
echo    - 套餐：按量付费（有免费额度）
echo    - 地域：选择广州或上海
echo.

echo 2️⃣  创建CloudRun服务
echo    - 进入CloudRun控制台
echo    - 点击"新建服务"
echo    - 服务名称：zhewei-api
echo    - 服务类型：容器型服务
echo.

echo 3️⃣  上传代码
echo    - 代码来源：选择"本地上传"
echo    - 上传项目根目录
echo    - 确保包含Dockerfile
echo.

echo 4️⃣  配置服务参数
echo    - CPU：0.5核
echo    - 内存：1GB
echo    - 最小实例数：1
echo    - 最大实例数：3
echo    - 端口：8080
echo.

echo 5️⃣  设置环境变量
echo    PYTHONPATH=/app
echo    PORT=8080
echo    CLOUD_DEPLOYMENT=true
echo.

echo 6️⃣  点击"部署"并等待完成
echo.

pause
cls

echo ================================================
echo 第四步：测试部署
echo ================================================
echo.

echo 部署完成后，您将获得访问地址
echo.
echo 示例格式：
echo   https://zhewei-api-xxx.service.tcloudbase.com
echo.

echo 您可以：
echo   1. 使用 test_cloud_api.py 测试API连接
echo   2. 使用 update_cloud_config.bat 更新客户端配置
echo.

choice /c YN /n /m "是否需要查看详细部署指南？(Y/N)"
if errorlevel 2 goto next_steps
if errorlevel 1 goto open_guide

:open_guide
start "" "CLOUDBASE_DEPLOYMENT_GUIDE.md"

:next_steps
cls
echo ================================================
echo 下一步操作
echo ================================================
echo.

echo ✅ 部署完成后，请执行以下操作：
echo.
echo 1️⃣  测试API连接
echo    python test_cloud_api.py https://your-domain.com
echo.

echo 2️⃣  更新客户端配置
echo    update_cloud_config.bat
echo    （输入您的云端地址）
echo.

echo 3️⃣  重启所有机器人
echo    python telegram_bot.py
echo    python discord_bot.py
echo.

echo 4️⃣  刷新浏览器
echo    访问新地址的前端界面
echo.

echo ================================================
echo 💡 重要提示
echo ================================================
echo.
echo 1. 记录您的访问地址和环境ID
echo 2. 确保最小实例数设置为1
echo 3. 检查安全规则配置
echo 4. 定期查看服务日志和监控
echo.

echo 📚 相关文档：
echo   - CLOUDBASE_DEPLOYMENT_GUIDE.md（详细指南）
echo   - DEPLOYMENT_STATUS.md（状态记录）
echo   - README.md（项目文档）
echo.

pause
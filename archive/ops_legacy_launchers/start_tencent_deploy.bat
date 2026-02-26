@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技 - 腾讯云CloudBase部署向导
echo ================================================
echo.

echo 📋 部署步骤说明
echo.
echo 由于腾讯云CloudBase需要在控制台手动部署，请按照以下步骤操作：
echo.

echo 第一步：登录腾讯云控制台
echo   访问：https://console.cloud.tencent.com/tcb
echo   或直接访问：https://console.cloud.tencent.com/tcb/cloudrun
echo.

echo 第二步：创建CloudBase环境
echo   1. 点击"新建环境"
echo   2. 环境名称：zhewei-ai-system
echo   3. 选择"按量付费"套餐（有免费额度）
echo   4. 地域：选择广州或上海（离您近的）
echo   5. 点击"新建"并等待创建完成
echo.

echo 第三步：部署CloudRun服务
echo   1. 进入CloudRun控制台
echo   2. 点击"新建服务"
echo   3. 服务名称：zhewei-api
echo   4. 服务类型：容器型服务
echo   5. 代码来源：选择"Git仓库"或"本地上传"
echo.

echo 第四步：配置服务参数
echo   - CPU：0.5核
echo   - 内存：1GB
echo   - 最小实例数：1
echo   - 最大实例数：3
echo   - 端口：8080
echo   - Dockerfile：已在项目根目录准备
echo.

echo 第五步：设置环境变量
echo   PYTHONPATH=/app
echo   PORT=8080
echo   CLOUD_DEPLOYMENT=true
echo   OLAMA_BASE_URL=http://localhost:11434
echo   DEFAULT_AI_MODEL=gemma3:4b
echo.

echo 第六步：部署并等待完成
echo   点击"部署"按钮，等待几分钟
echo   部署成功后会显示访问地址
echo.

echo ================================================
echo 💡 提示和帮助
echo ================================================
echo.
echo 查看详细部署指南：
echo   打开文件：CLOUDBASE_DEPLOYMENT_GUIDE.md
echo.
echo 查看部署状态：
echo   打开文件：DEPLOYMENT_STATUS.md
echo.
echo 腾讯云文档：
echo   https://cloud.tencent.com/document/product/1243
echo.

choice /c YN /n /m "是否打开腾讯云控制台？(Y/N)"
if errorlevel 2 goto end
if errorlevel 1 goto open_console

:open_console
start "" "https://console.cloud.tencent.com/tcb/cloudrun"
goto end

:end
echo.
echo ================================================
echo ✅ 准备就绪，开始部署吧！
echo ================================================
echo.
echo 📝 部署完成后，请记录以下信息：
echo   1. API访问地址
echo   2. 环境ID
echo   3. 服务名称
echo.
echo 然后我可以帮您更新客户端配置。
echo.
pause
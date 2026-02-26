@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技 - 腾讯云CloudBase一键部署
echo ================================================
echo.

echo 📋 部署前检查...
echo.

REM 检查Docker是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker未安装，请先安装Docker
    echo    下载地址：https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo ✅ Docker已安装
echo.

REM 检查Docker是否运行
docker ps >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker未运行，请启动Docker Desktop
    pause
    exit /b 1
)

echo ✅ Docker正在运行
echo.

echo 🏗️ 开始构建Docker镜像...
echo.

docker build -t zhewei-ai-api:latest .

if errorlevel 1 (
    echo ❌ Docker镜像构建失败
    pause
    exit /b 1
)

echo ✅ Docker镜像构建成功
echo.

echo 📝 部署说明：
echo.
echo 由于腾讯云CloudBase需要通过控制台部署，请按照以下步骤操作：
echo.
echo 1. 登录腾讯云控制台
echo    https://console.cloud.tencent.com/tcb/cloudrun
echo.
echo 2. 创建新的CloudRun服务
echo    - 服务名称：zhewei-api
echo    - 服务类型：容器型服务
echo    - 运行环境：自定义镜像
echo.
echo 3. 导入本地镜像
echo    - 如果使用本地镜像，需要先将镜像推送到腾讯云镜像仓库
echo    - 或使用Git仓库部署（推荐）
echo.
echo 4. 配置服务参数
echo    - CPU：0.5核
echo    - 内存：1GB
echo    - 最小实例数：1
echo    - 最大实例数：3
echo    - 端口：8080
echo.
echo 5. 设置环境变量
echo    PYTHONPATH=/app
echo    PORT=8080
echo    CLOUD_DEPLOYMENT=true
echo.
echo 6. 部署并获取访问地址
echo.
echo 💡 更详细的部署指南请查看：CLOUDBASE_DEPLOYMENT_GUIDE.md
echo.

choice /c YN /n /m "是否打开详细部署指南？(Y/N)"
if errorlevel 2 goto end
if errorlevel 1 goto open_guide

:open_guide
start "" "CLOUDBASE_DEPLOYMENT_GUIDE.md"
goto end

:end
echo.
echo ================================================
echo 🚀 构建完成，准备部署到腾讯云
echo ================================================
echo.
echo 💡 提示：您现在可以：
echo    1. 查看详细部署指南（CLOUDBASE_DEPLOYMENT_GUIDE.md）
echo    2. 访问腾讯云控制台开始部署
echo    3. 或使用其他云平台（如Vercel、Railway）
echo.
pause
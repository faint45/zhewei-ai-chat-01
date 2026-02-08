@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技 - 部署准备检查
echo ================================================
echo.

echo 检查部署文件完整性...
echo.

set ALL_READY=true

echo [1/6] 检查 Dockerfile
if exist Dockerfile (
    echo ✅ Dockerfile
) else (
    echo ❌ Dockerfile - 缺失
    set ALL_READY=false
)

echo [2/6] 检查 requirements_ai.txt
if exist requirements_ai.txt (
    echo ✅ requirements_ai.txt
) else (
    echo ❌ requirements_ai.txt - 缺失
    set ALL_READY=false
)

echo [3/6] 检查 remote_control_server.py
if exist remote_control_server.py (
    echo ✅ remote_control_server.py
) else (
    echo ❌ remote_control_server.py - 缺失
    set ALL_READY=false
)

echo [4/6] 检查 CLOUDBASE_DEPLOYMENT_GUIDE.md
if exist CLOUDBASE_DEPLOYMENT_GUIDE.md (
    echo ✅ CLOUDBASE_DEPLOYMENT_GUIDE.md
) else (
    echo ❌ CLOUDBASE_DEPLOYMENT_GUIDE.md - 缺失
    set ALL_READY=false
)

echo [5/6] 检查 開始騰訊雲部署.bat
if exist 開始騰訊雲部署.bat (
    echo ✅ 開始騰訊雲部署.bat
) else (
    echo ❌ 開始騰訊雲部署.bat - 缺失
    set ALL_READY=false
)

echo [6/6] 检查 update_cloud_config.bat
if exist update_cloud_config.bat (
    echo ✅ update_cloud_config.bat
) else (
    echo ❌ update_cloud_config.bat - 缺失
    set ALL_READY=false
)

echo.
echo ================================================

if "%ALL_READY%"=="true" (
    echo ✅ 所有部署文件已准备就绪
    echo ================================================
    echo.
    echo 🚀 您现在可以开始部署到腾讯云
    echo.
    echo 步骤1：打开腾讯云控制台
    echo         https://console.cloud.tencent.com/tcb/cloudrun
    echo.
    echo 步骤2：创建CloudBase环境
    echo         环境名称：zhewei-ai-system
    echo.
    echo 步骤3：创建CloudRun服务
    echo         服务名称：zhewei-api
    echo         服务类型：容器型服务
    echo.
    echo 步骤4：上传代码并配置
    echo         CPU：0.5核
    echo         内存：1GB
    echo         最小实例数：1
    echo         最大实例数：3
    echo         端口：8080
    echo.
    echo 步骤5：部署并测试
    echo.
    echo 💡 需要帮助？查看详细文档
    echo         CLOUDBASE_DEPLOYMENT_GUIDE.md
    echo.

    choice /c YN /n /m "是否打开腾讯云控制台？(Y/N)"
    if errorlevel 2 goto end
    if errorlevel 1 goto open_console

    :open_console
    start "" "https://console.cloud.tencent.com/tcb/cloudrun"
) else (
    echo ❌ 部署文件不完整
    echo ================================================
    echo.
    echo 请确保以下文件存在：
    echo   - Dockerfile
    echo   - requirements_ai.txt
    echo   - remote_control_server.py
    echo   - CLOUDBASE_DEPLOYMENT_GUIDE.md
    echo   - 開始騰訊雲部署.bat
    echo   - update_cloud_config.bat
    echo.
)

:end
echo.
pause
@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技 - 云端环境变量配置
echo ================================================
echo.

echo 已准备的环境变量：
echo.
echo PYTHONPATH=/app
echo PORT=8080
echo CLOUD_DEPLOYMENT=true
echo OLAMA_BASE_URL=http://localhost:11434
echo DEFAULT_AI_MODEL=gemma3:4b
echo.

echo ================================================
echo 配置说明
echo ================================================
echo.
echo 这些环境变量需要在腾讯云CloudRun服务中手动配置。
echo.
echo 配置步骤：
echo.
echo 1. 登录腾讯云CloudBase控制台
echo    https://console.cloud.tencent.com/tcb/cloudrun
echo.
echo 2. 找到您的服务 zhewei-api
echo.
echo 3. 点击"服务配置"或"环境变量"
echo.
echo 4. 添加以下环境变量：
echo.
echo    键名                值
echo    -------------------  --------------------------------
echo    PYTHONPATH          /app
echo    PORT                8080
echo    CLOUD_DEPLOYMENT    true
echo    OLAMA_BASE_URL      http://localhost:11434
echo    DEFAULT_AI_MODEL    gemma3:4b
echo.
echo 5. 点击"保存"或"更新配置"
echo.
echo 6. 如果服务正在运行，需要重新部署以应用新变量
echo.

echo ================================================
echo 重要提示
echo ================================================
echo.
echo 1. OLAMA_BASE_URL 配置说明：
echo    - 如果您在云端不使用Ollama，可以注释掉此变量
echo    - 如果使用云端AI服务，需要配置实际的API地址
echo    - 本地Ollama在云端无法访问，建议使用云端AI服务
echo.
echo 2. DEFAULT_AI_MODEL 配置说明：
echo    - gemma3:4b 是轻量级模型，适合大多数场景
echo    - 如需其他模型，可以修改为：llava:latest, llama2:7b 等
echo.
echo 3. CORS_ORIGINS 配置说明：
echo    - 生产环境建议限制具体域名
echo    - 例如：https://yourdomain.com
echo    - 开发环境可以使用 * 允许所有来源
echo.

choice /c YN /n /m "是否打开腾讯云控制台配置环境变量？(Y/N)"
if errorlevel 2 goto end
if errorlevel 1 goto open_console

:open_console
start "" "https://console.cloud.tencent.com/tcb/cloudrun"

:end
echo.
echo ================================================
echo 💡 其他配置选项
echo ================================================
echo.
echo 环境变量已保存到文件：
echo   .env.cloud
echo.
echo 您可以：
echo   1. 在腾讯云控制台手动添加这些变量
echo   2. 将此文件的内容复制粘贴到配置界面
echo   3. 根据需要修改变量值
echo.
echo 部署完成后，记得测试服务是否正常运行：
echo   python test_cloud_api.py https://your-domain.com
echo.
pause
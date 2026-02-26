@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技大腦 - 本地AI模型配置
echo ================================================
echo.

echo 🤖 配置本地Ollama模型...
echo.

REM 設置環境變量
set AI_MODEL_TYPE=ollama
set OLLAMA_MODEL=llama3.1
set OLLAMA_API_BASE=http://localhost:11434/v1

echo ✅ 環境變量設置完成：
echo     AI_MODEL_TYPE=%AI_MODEL_TYPE%
echo     OLLAMA_MODEL=%OLLAMA_MODEL%
echo     OLLAMA_API_BASE=%OLLAMA_API_BASE%

echo.
echo 🔧 驗證配置...
python -c "
import os
print('當前環境變量：')
print(f\"  AI_MODEL_TYPE: {os.getenv('AI_MODEL_TYPE', '未設置')}\")
print(f\"  OLLAMA_MODEL: {os.getenv('OLLAMA_MODEL', '未設置')}\")
print(f\"  OLLAMA_API_BASE: {os.getenv('OLLAMA_API_BASE', '未設置')}\")

from config_ai import ai_config
print()
print('AI配置狀態：')
print(f\"  模型類型: {ai_config.MODEL_TYPE.value}\")
print(f\"  模型名稱: {ai_config.get_model_name()}\")
print(f\"  API地址: {ai_config.get_api_base()}\")
"

echo.
echo 📋 重要提示：
echo     1. 確保Ollama服務正在運行
echo     2. 已下載llama3.1模型
echo     3. 重啟網站服務器使配置生效
echo.

echo 🔍 檢查Ollama服務狀態...
python -c "
import requests
try:
    response = requests.get('http://localhost:11434/api/tags', timeout=5)
    if response.status_code == 200:
        print('✅ Ollama服務正常運行')
        models = response.json().get('models', [])
        if models:
            print('📊 可用的本地模型：')
            for model in models:
                print(f'   - {model[\"name\"]}')
        else:
            print('⚠️  未找到本地模型，請先下載模型')
    else:
        print('❌ Ollama服務未運行')
except Exception as e:
    print(f'❌ 無法連接到Ollama服務: {e}')
    print('💡 請先安裝並啟動Ollama：https://ollama.ai/')
"

echo.
echo 🚀 啟動網站服務器（使用本地AI模型）...
echo.
echo 📝 下次啟動網站時將使用本地Ollama模型
echo 💡 運行 start_website.bat 啟動服務
echo.

REM 啟動網站服務器（可選）
choice /c YN /n /m "是否立即啟動網站服務器？(Y/N):"
if errorlevel 2 goto end
if errorlevel 1 goto start_server

:start_server
echo.
echo 🔄 啟動網站服務器...
start_website.bat
goto end

:end
echo.
echo ✅ 本地AI模型配置完成！
echo 💡 現在可以測試 http://localhost:8000/chat 使用本地模型對話
echo.
pause
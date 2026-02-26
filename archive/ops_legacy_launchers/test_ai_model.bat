@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技大腦 - AI模型測試工具
echo ================================================
echo.

echo 🤖 檢測當前AI模型配置...
echo.

REM 檢查配置文件
echo 📋 檢查 config_ai.py 配置...
python -c "
from config_ai import ai_config, AIModelType
print('當前AI模型配置：')
print(f'  模型類型: {ai_config.MODEL_TYPE.value}')
print(f'  模型名稱: {ai_config.get_model_name()}')
print(f'  API地址: {ai_config.get_api_base()}')

if ai_config.MODEL_TYPE == AIModelType.DEMO:
    print('🔸 當前模式: 演示模式')
    print('   - 使用基礎回應，無需AI模型')
elif ai_config.MODEL_TYPE == AIModelType.OLLAMA:
    print('🔸 當前模式: 本地模型（Ollama）')
    print('   - 使用本地安裝的AI模型')
elif ai_config.MODEL_TYPE == AIModelType.OPENAI:
    print('🔸 當前模式: OpenAI API')
    print('   - 使用雲端OpenAI服務')
"

echo.
echo 🔍 測試模型連接...
python -c "
import requests
from config_ai import ai_config

try:
    if ai_config.MODEL_TYPE.value == 'ollama':
        # 測試Ollama服務是否運行
        response = requests.get(f'{ai_config.OLLAMA_API_BASE.replace(\"/v1\", \"\")}/api/tags', timeout=5)
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
    elif ai_config.MODEL_TYPE.value == 'openai':
        # 測試OpenAI API連接
        import os
        if os.getenv('OPENAI_API_KEY'):
            print('✅ OpenAI API密鑰已設置')
        else:
            print('⚠️  未設置OPENAI_API_KEY環境變量')
    else:
        print('✅ 演示模式正常')
        
except Exception as e:
    print(f'❌ 連接測試失敗: {e}')
"

echo.
echo 💬 測試AI回應...
python -c "
import asyncio
from ai_service import AIService
from config_ai import ai_config

async def test_ai():
    try:
        ai_service = AIService(ai_config)
        test_message = '你好，請告訴我築未科技是做什麼的？'
        
        print(f'測試問題: {test_message}')
        
        response = await ai_service.generate_response(test_message, 'test_session')
        
        print('✅ AI回應測試成功！')
        print('回應內容:')
        print(response[:200] + ('...' if len(response) > 200 else ''))
        
        # 判斷回應來源
        if ai_config.MODEL_TYPE.value == 'demo':
            print('🔸 來源: 演示模式（預設回應）')
        elif 'Ollama' in response or 'ollama' in response:
            print('🔸 來源: 本地Ollama模型')
        elif '築未科技' in response:
            print('🔸 來源: AI模型生成（內容相關）')
        else:
            print('🔸 來源: AI模型生成')
            
    except Exception as e:
        print(f'❌ AI測試失敗: {e}')

asyncio.run(test_ai())
"

echo.
echo 🔧 切換模型配置方法：
echo.
echo 1. 切換到本地模型（Ollama）：
echo     set AI_MODEL_TYPE=ollama
echo     set OLLAMA_MODEL=llama3.1
echo.
echo 2. 切換到OpenAI API：
echo     set AI_MODEL_TYPE=openai
echo     set OPENAI_API_KEY=您的API密鑰
echo.
echo 3. 使用演示模式（默認）：
echo     set AI_MODEL_TYPE=demo
echo.
echo 📱 立即測試：
echo     1. 啟動網站服務器（start_website.bat）
echo     2. 訪問 http://localhost:8000/chat
echo     3. 與AI大腦對話測試
echo.

pause
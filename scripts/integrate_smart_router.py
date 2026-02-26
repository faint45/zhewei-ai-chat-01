#!/usr/bin/env python3
"""
築未科技 — 智慧路由整合腳本
將 SmartOllamaRouter 整合到現有的 AI 服務中
"""

import os
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def integrate_to_ai_service():
    """整合智慧路由到 ai_service.py"""
    
    ai_service_path = ROOT / "ai_service.py"
    
    if not ai_service_path.exists():
        print(f"❌ 找不到 {ai_service_path}")
        return False
    
    print(f"📝 讀取 {ai_service_path}")
    content = ai_service_path.read_text(encoding="utf-8")
    
    # 檢查是否已整合
    if "smart_ollama_router" in content:
        print("✅ 智慧路由已整合到 ai_service.py")
        return True
    
    # 在 OllamaService 的 __init__ 方法中整合智慧路由
    integration_code = '''
    def __init__(self, model_name: str | None = None):
        # 使用智慧路由選擇最佳 Ollama URL
        try:
            from ai_modules.smart_ollama_router import get_ollama_url
            base = get_ollama_url(prefer_gpu=True)
        except ImportError:
            # Fallback 到環境變數
            base = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        
        self.base_url = f"{base}/api/chat"
        self.model_name = model_name or OLLAMA_MODEL
        self.timeout = OLLAMA_TIMEOUT
'''
    
    # 替換原有的 __init__ 方法
    old_init = '''    def __init__(self, model_name: str | None = None):
        base = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        self.base_url = f"{base}/api/chat"
        self.model_name = model_name or OLLAMA_MODEL
        self.timeout = OLLAMA_TIMEOUT'''
    
    if old_init in content:
        content = content.replace(old_init, integration_code)
        ai_service_path.write_text(content, encoding="utf-8")
        print("✅ 已整合智慧路由到 ai_service.py")
        return True
    else:
        print("⚠️ 無法找到 OllamaService.__init__ 方法，請手動整合")
        return False

def add_router_api_to_brain_server():
    """在 brain_server.py 中添加路由器狀態 API"""
    
    brain_server_path = ROOT / "brain_server.py"
    
    if not brain_server_path.exists():
        print(f"❌ 找不到 {brain_server_path}")
        return False
    
    print(f"📝 讀取 {brain_server_path}")
    content = brain_server_path.read_text(encoding="utf-8")
    
    # 檢查是否已添加
    if "/api/ollama/router/status" in content:
        print("✅ 路由器 API 已添加到 brain_server.py")
        return True
    
    # 添加路由器狀態 API
    router_api = '''
# ============================================
# Ollama 智慧路由 API
# ============================================

@app.get("/api/ollama/router/status")
async def get_ollama_router_status():
    """取得 Ollama 智慧路由器狀態"""
    try:
        from ai_modules.smart_ollama_router import get_router_status
        status = get_router_status()
        return {"success": True, "data": status}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/ollama/router/refresh")
async def refresh_ollama_router():
    """強制刷新路由器快取"""
    try:
        from ai_modules.smart_ollama_router import get_router
        router = get_router()
        router.force_refresh()
        status = router.get_status()
        return {"success": True, "message": "路由器已刷新", "data": status}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/ollama/models/recommended")
async def get_recommended_ollama_model(task_type: str = "general"):
    """取得推薦的 Ollama 模型"""
    try:
        from ai_modules.smart_ollama_router import get_recommended_model
        model = get_recommended_model(task_type)
        return {"success": True, "model": model, "task_type": task_type}
    except Exception as e:
        return {"success": False, "error": str(e)}
'''
    
    # 在檔案末尾添加（在 if __name__ == "__main__" 之前）
    if 'if __name__ == "__main__":' in content:
        parts = content.split('if __name__ == "__main__":')
        content = parts[0] + router_api + '\n\nif __name__ == "__main__":' + parts[1]
        brain_server_path.write_text(content, encoding="utf-8")
        print("✅ 已添加路由器 API 到 brain_server.py")
        return True
    else:
        print("⚠️ 無法找到合適的插入點，請手動添加 API")
        return False

def create_test_script():
    """建立測試腳本"""
    
    test_script = ROOT / "scripts" / "test_smart_router.py"
    
    test_code = '''#!/usr/bin/env python3
"""測試智慧 Ollama 路由器"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai_modules.smart_ollama_router import get_router

def main():
    print("=== 測試智慧 Ollama 路由器 ===\\n")
    
    router = get_router()
    
    # 取得狀態
    status = router.get_status()
    
    print(f"🎯 當前模式: {status['current_mode']}")
    print(f"\\n📡 GPU Ollama:")
    print(f"   URL: {status['gpu']['url']}")
    print(f"   可用: {'✅' if status['gpu']['available'] else '❌'}")
    if status['gpu']['models']:
        print(f"   模型: {', '.join(status['gpu']['models'][:5])}")
    print(f"   請求次數: {status['gpu']['requests']}")
    
    print(f"\\n☁️  CPU Ollama:")
    print(f"   URL: {status['cpu']['url']}")
    if status['cpu']['models']:
        print(f"   模型: {', '.join(status['cpu']['models'][:5])}")
    print(f"   請求次數: {status['cpu']['requests']}")
    
    # 推薦模型
    print(f"\\n💡 推薦模型:")
    print(f"   通用任務: {router.get_recommended_model('general')}")
    print(f"   代碼任務: {router.get_recommended_model('code')}")
    print(f"   輕量任務: {router.get_recommended_model('lightweight')}")
    
    # 最佳 URL
    best_url = router.get_best_ollama_url()
    print(f"\\n🚀 最佳 Ollama URL: {best_url}")
    
    print("\\n✅ 測試完成！")

if __name__ == "__main__":
    main()
'''
    
    test_script.write_text(test_code, encoding="utf-8")
    print(f"✅ 已建立測試腳本: {test_script}")

def main():
    print("=" * 60)
    print("🔧 築未科技 — 智慧路由整合")
    print("=" * 60)
    print()
    
    # 1. 整合到 ai_service.py
    print("步驟 1: 整合到 ai_service.py")
    integrate_to_ai_service()
    print()
    
    # 2. 添加 API 到 brain_server.py
    print("步驟 2: 添加 API 到 brain_server.py")
    add_router_api_to_brain_server()
    print()
    
    # 3. 建立測試腳本
    print("步驟 3: 建立測試腳本")
    create_test_script()
    print()
    
    print("=" * 60)
    print("✅ 整合完成！")
    print("=" * 60)
    print()
    print("後續步驟:")
    print("1. 複製 env.hybrid.example 為 .env")
    print("2. 填入 CLOUDFLARE_TOKEN 和 API Keys")
    print("3. 執行測試: python scripts/test_smart_router.py")
    print("4. 重啟 Brain Server")
    print()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試築未科技統一API功能
驗證三大模塊：Unified API、Auth Manager、Context Bridge
"""

import requests
import json
import time

def test_unified_api():
    """測試Unified API功能"""
    print("🧪 測試Unified API功能...")
    
    # 測試AI指令
    payload = {
        "source": "test",
        "user_id": "test_user_001",
        "command": "ai:解釋什麼是機器學習"
    }
    
    try:
        response = requests.post(
            "http://localhost:8003/v1/execute",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ AI指令測試成功")
            print(f"   狀態: {result['status']}")
            print(f"   執行時間: {result.get('execution_time', 0):.2f}秒")
            print(f"   上下文ID: {result.get('context_id', '新會話')}")
            return True
        else:
            print(f"❌ AI指令測試失敗: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ AI指令測試異常: {e}")
        return False

def test_system_command():
    """測試系統指令"""
    print("\n🧪 測試系統指令功能...")
    
    payload = {
        "source": "test",
        "user_id": "test_user_001",
        "command": "sys:python --version"
    }
    
    try:
        response = requests.post(
            "http://localhost:8003/v1/execute",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 系統指令測試成功")
            print(f"   狀態: {result['status']}")
            print(f"   結果: {result.get('result', '無輸出')[:100]}...")
            return True
        else:
            print(f"❌ 系統指令測試失敗: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 系統指令測試異常: {e}")
        return False

def test_context_bridge():
    """測試上下文橋接功能"""
    print("\n🧪 測試上下文橋接功能...")
    
    # 第一次對話
    payload1 = {
        "source": "test",
        "user_id": "test_user_002",
        "command": "ai:什麼是深度學習"
    }
    
    try:
        # 第一次對話
        response1 = requests.post(
            "http://localhost:8003/v1/execute",
            json=payload1,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response1.status_code == 200:
            result1 = response1.json()
            context_id = result1.get('context_id')
            
            # 第二次對話（使用相同的上下文）
            payload2 = {
                "source": "test",
                "user_id": "test_user_002",
                "command": "ai:那它和機器學習有什麼區別",
                "context_id": context_id
            }
            
            response2 = requests.post(
                "http://localhost:8003/v1/execute",
                json=payload2,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response2.status_code == 200:
                result2 = response2.json()
                print(f"✅ 上下文橋接測試成功")
                print(f"   第一次上下文ID: {context_id}")
                print(f"   第二次上下文ID: {result2.get('context_id')}")
                print(f"   上下文連續性: {'✅' if context_id == result2.get('context_id') else '❌'}")
                return True
            else:
                print(f"❌ 第二次對話失敗: {response2.status_code}")
                return False
        else:
            print(f"❌ 第一次對話失敗: {response1.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 上下文橋接測試異常: {e}")
        return False

def test_auth_manager():
    """測試認證管理功能"""
    print("\n🧪 測試認證管理功能...")
    
    # 測試不同用戶
    users = ["user_a", "user_b", "user_c"]
    success_count = 0
    
    for user_id in users:
        payload = {
            "source": "test",
            "user_id": user_id,
            "command": "ai:測試認證功能"
        }
        
        try:
            response = requests.post(
                "http://localhost:8003/v1/execute",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result['status'] == 'success':
                    success_count += 1
                    print(f"   ✅ 用戶 {user_id} 認證成功")
                else:
                    print(f"   ❌ 用戶 {user_id} 認證失敗: {result.get('error')}")
            else:
                print(f"   ❌ 用戶 {user_id} 請求失敗: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ 用戶 {user_id} 測試異常: {e}")
    
    print(f"   認證成功率: {success_count}/{len(users)} ({success_count/len(users)*100:.1f}%)")
    return success_count == len(users)

def test_legacy_api_compatibility():
    """測試舊API兼容性"""
    print("\n🧪 測試舊API兼容性...")
    
    # 測試舊的API端點
    try:
        response = requests.get("http://localhost:8003/api/status", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 舊API兼容性測試成功")
            print(f"   服務狀態: {result.get('service', '未知')}")
            print(f"   Ollama狀態: {'✅' if result.get('ollama_status') else '❌'}")
            return True
        else:
            print(f"❌ 舊API兼容性測試失敗: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 舊API兼容性測試異常: {e}")
        return False

def main():
    """主測試函數"""
    print("🚀 開始測試築未科技統一API系統")
    print("=" * 50)
    
    # 檢查服務器是否運行
    try:
        response = requests.get("http://localhost:8003/api/status", timeout=5)
        if response.status_code != 200:
            print("❌ 遠程控制服務器未運行，請先啟動: python remote_control_server.py")
            return
    except:
        print("❌ 無法連接到遠程控制服務器，請先啟動: python remote_control_server.py")
        return
    
    # 執行測試
    tests = [
        ("Unified API", test_unified_api),
        ("系統指令", test_system_command),
        ("上下文橋接", test_context_bridge),
        ("認證管理", test_auth_manager),
        ("舊API兼容性", test_legacy_api_compatibility)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 測試異常: {e}")
            results.append((test_name, False))
    
    # 總結測試結果
    print("\n" + "=" * 50)
    print("📊 測試結果總結:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"   {test_name}: {status}")
    
    print(f"\n總測試數: {total}")
    print(f"通過數: {passed}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 所有測試通過！統一API系統運行正常")
    else:
        print("⚠️ 部分測試失敗，請檢查服務器狀態")

if __name__ == "__main__":
    main()
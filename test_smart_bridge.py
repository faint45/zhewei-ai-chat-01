# -*- coding: utf-8 -*-
"""
Smart Bridge 整合測試腳本
"""

import asyncio
import json
import httpx

BASE_URL = "http://localhost:8003"

async def test_health():
    """測試健康檢查"""
    print("🔍 測試 Health Check...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"✅ Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200

async def test_cost_stats():
    """測試成本統計"""
    print("\n💰 測試成本統計 API...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/cost-stats")
        print(f"✅ Status: {response.status_code}")
        data = response.json()
        print(f"   總成本: ${data.get('total_cost', 0):.4f}")
        print(f"   節省: ${data.get('saved_cost', 0):.4f}")
        print(f"   效率: {data.get('efficiency', 'N/A')}")
        return response.status_code == 200

async def test_generate_api():
    """測試兩階段生成 API"""
    print("\n🚀 測試兩階段生成 API...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "prompt": "寫一個 Python 函數計算費氏數列",
            "task_type": "code"
        }
        print(f"   請求: {payload['prompt']}")
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/generate",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 生成成功!")
                print(f"   Phase 1: {data.get('phase1', {}).get('provider', 'N/A')}")
                print(f"   Phase 2: {data.get('phase2', {}).get('provider', 'N/A')}")
                print(f"   成本: ${data.get('cost_usd', 0):.4f}")
                print(f"   節省: ${data.get('saved_usd', 0):.4f}")
                print(f"   內容長度: {len(data.get('content', ''))} 字元")
                return True
            else:
                print(f"❌ 失敗: {response.status_code}")
                print(f"   {response.text}")
                return False
        except Exception as e:
            print(f"❌ 錯誤: {e}")
            return False

async def test_frontend():
    """測試前端頁面"""
    print("\n🌐 測試前端頁面...")
    async with httpx.AsyncClient() as client:
        response = await client.get(BASE_URL)
        print(f"✅ Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        print(f"   頁面大小: {len(response.text)} 字元")
        return response.status_code == 200 and "Smart Bridge" in response.text

async def main():
    """執行所有測試"""
    print("=" * 60)
    print("🌉 Smart Bridge 整合測試")
    print("=" * 60)
    
    results = []
    
    # 測試 1: Health Check
    results.append(("Health Check", await test_health()))
    
    # 測試 2: 成本統計
    results.append(("成本統計 API", await test_cost_stats()))
    
    # 測試 3: 前端頁面
    results.append(("前端頁面", await test_frontend()))
    
    # 測試 4: 兩階段生成 (可能需要較長時間)
    results.append(("兩階段生成 API", await test_generate_api()))
    
    # 總結
    print("\n" + "=" * 60)
    print("📊 測試總結")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\n總計: {passed}/{total} 測試通過")
    
    if passed == total:
        print("\n🎉 所有測試通過！Smart Bridge 整合成功！")
    else:
        print(f"\n⚠️ {total - passed} 個測試失敗，請檢查錯誤訊息")

if __name__ == "__main__":
    asyncio.run(main())

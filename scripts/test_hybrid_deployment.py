#!/usr/bin/env python3
"""
築未科技 — 混合部署測試腳本
測試雲端服務與本地 GPU 服務的連接狀態
"""

import requests
import time
from datetime import datetime
from typing import List, Dict, Tuple

class HybridDeploymentTester:
    def __init__(self):
        self.results = []
        
    def test_service(self, name: str, url: str, timeout: int = 5, category: str = "cloud") -> Dict:
        """測試單一服務"""
        try:
            start = time.time()
            resp = requests.get(url, timeout=timeout)
            elapsed = time.time() - start
            
            success = resp.status_code == 200
            return {
                "name": name,
                "url": url,
                "status": resp.status_code,
                "success": success,
                "response_time": f"{elapsed:.2f}s",
                "category": category,
                "error": None
            }
        except requests.exceptions.Timeout:
            return {
                "name": name,
                "url": url,
                "status": "TIMEOUT",
                "success": False,
                "response_time": f">{timeout}s",
                "category": category,
                "error": "超時（可能本地關機或網路問題）"
            }
        except requests.exceptions.ConnectionError:
            return {
                "name": name,
                "url": url,
                "status": "CONNECTION_ERROR",
                "success": False,
                "response_time": "N/A",
                "category": category,
                "error": "連接失敗"
            }
        except Exception as e:
            return {
                "name": name,
                "url": url,
                "status": "ERROR",
                "success": False,
                "response_time": "N/A",
                "category": category,
                "error": str(e)[:100]
            }
    
    def run_tests(self):
        """執行所有測試"""
        print("=" * 60)
        print("🧪 築未科技混合部署測試")
        print(f"⏰ 測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 雲端服務測試
        cloud_services = [
            ("Brain Server", "https://jarvis.zhe-wei.net/health"),
            ("Portal", "https://zhe-wei.net"),
            ("CMS", "https://cms.zhe-wei.net/health"),
            ("CodeSim", "https://codesim.zhe-wei.net"),
            ("Prediction", "https://predict.zhe-wei.net/health"),
        ]
        
        # 本地 GPU 服務測試（透過 Tunnel）
        local_services = [
            ("Ollama GPU", "https://ollama-gpu.zhe-wei.net/api/tags"),
            ("Vision AI", "https://vision-gpu.zhe-wei.net/healthz"),
            ("ComfyUI", "https://comfyui.zhe-wei.net"),
            ("Dify Local", "https://dify-local.zhe-wei.net"),
        ]
        
        # 測試雲端服務
        print("\n📡 雲端服務（必須可用）")
        print("-" * 60)
        for name, url in cloud_services:
            result = self.test_service(name, url, timeout=10, category="cloud")
            self.results.append(result)
            self._print_result(result)
        
        # 測試本地服務
        print("\n🖥️  本地 GPU 服務（可選，本地開機時可用）")
        print("-" * 60)
        for name, url in local_services:
            result = self.test_service(name, url, timeout=5, category="local")
            self.results.append(result)
            self._print_result(result)
        
        # 統計結果
        self._print_summary()
    
    def _print_result(self, result: Dict):
        """輸出單一測試結果"""
        if result["success"]:
            status = f"✅ {result['name']}"
            detail = f"({result['response_time']})"
        else:
            status = f"❌ {result['name']}"
            detail = f"({result['status']})"
            if result['error']:
                detail += f" - {result['error']}"
        
        print(f"{status:40} {detail}")
    
    def _print_summary(self):
        """輸出測試摘要"""
        print("\n" + "=" * 60)
        print("📊 測試摘要")
        print("=" * 60)
        
        cloud_results = [r for r in self.results if r["category"] == "cloud"]
        local_results = [r for r in self.results if r["category"] == "local"]
        
        cloud_success = sum(1 for r in cloud_results if r["success"])
        local_success = sum(1 for r in local_results if r["success"])
        
        print(f"\n雲端服務: {cloud_success}/{len(cloud_results)} 可用")
        print(f"本地服務: {local_success}/{len(local_results)} 可用")
        
        # 判斷部署狀態
        print("\n🎯 部署狀態:")
        if cloud_success == len(cloud_results):
            print("  ✅ 雲端服務完全正常")
        else:
            print(f"  ⚠️ 雲端服務部分異常 ({len(cloud_results) - cloud_success} 個服務不可用)")
        
        if local_success == len(local_results):
            print("  ✅ 本地 GPU 服務完全可用（最佳性能模式）")
        elif local_success > 0:
            print(f"  ⚠️ 本地 GPU 服務部分可用 ({local_success}/{len(local_results)})")
        else:
            print("  ℹ️ 本地 GPU 服務不可用（降級為雲端 CPU 模式）")
        
        # 建議
        print("\n💡 建議:")
        if cloud_success < len(cloud_results):
            print("  - 檢查雲端 VPS 服務狀態")
            print("  - 執行: docker compose -f docker-compose.cloud.yml ps")
        
        if local_success == 0 and len(local_results) > 0:
            print("  - 本地主機可能關機或 Tunnel 未啟動")
            print("  - 檢查: Get-Service cloudflared")
            print("  - 系統將使用雲端 CPU 模式運行（功能受限）")
        
        print("\n" + "=" * 60)

def main():
    tester = HybridDeploymentTester()
    tester.run_tests()

if __name__ == "__main__":
    main()

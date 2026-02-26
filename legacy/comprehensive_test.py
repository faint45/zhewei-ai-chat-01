#!/usr/bin/env python3
"""
築未科技 AI 系統完整功能測試
涵蓋所有主要模組和 API 端點
"""
import requests
import json
import base64
from datetime import datetime
from pathlib import Path

class ComprehensiveSystemTester:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "categories": {}
        }
        self.current_category = None
        
    def category(self, name):
        """開始新的測試類別"""
        self.current_category = name
        self.results["categories"][name] = {"tests": [], "passed": 0, "failed": 0}
        print(f"\n{'='*60}")
        print(f"📋 {name}")
        print('='*60)
        
    def test(self, name, url, method="GET", data=None, headers=None, expected_status=200, timeout=10):
        """執行單一測試"""
        try:
            if method == "GET":
                resp = requests.get(url, timeout=timeout)
            elif method == "POST":
                resp = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == "DELETE":
                resp = requests.delete(url, timeout=timeout)
            
            success = resp.status_code == expected_status
            
            # 嘗試解析 JSON
            try:
                response_data = resp.json()
                response_preview = json.dumps(response_data, ensure_ascii=False)[:150]
            except:
                response_preview = resp.text[:150]
            
            result = {
                "name": name,
                "url": url,
                "method": method,
                "status": resp.status_code,
                "success": success,
                "response": response_preview
            }
        except requests.exceptions.Timeout:
            result = {
                "name": name,
                "url": url,
                "method": method,
                "status": "TIMEOUT",
                "success": False,
                "response": f"請求超時 ({timeout}s)"
            }
        except Exception as e:
            result = {
                "name": name,
                "url": url,
                "method": method,
                "status": "ERROR",
                "success": False,
                "response": str(e)[:150]
            }
        
        # 記錄結果
        if self.current_category:
            self.results["categories"][self.current_category]["tests"].append(result)
            if result["success"]:
                self.results["categories"][self.current_category]["passed"] += 1
            else:
                self.results["categories"][self.current_category]["failed"] += 1
        
        # 顯示結果
        status = "✅" if result["success"] else "❌"
        print(f"{status} {name} ({result['status']})")
        
        return result["success"]
    
    def run_all_tests(self):
        """執行所有測試"""
        print("\n" + "="*60)
        print("🧪 築未科技 AI 系統完整功能測試")
        print("="*60)
        
        # ===== 1. 核心服務健康檢查 =====
        self.category("1. 核心服務健康檢查")
        self.test("Brain Server 健康", "http://localhost:8002/health")
        self.test("Smart Bridge 健康", "http://localhost:8003/health")
        self.test("AI Vision 健康", "http://localhost:8030/healthz")
        self.test("CMS 健康", "http://localhost:8020/api/projects")
        self.test("Ollama 服務", "http://localhost:11460/api/tags")
        self.test("Qdrant 向量庫", "http://localhost:6333/collections")
        
        # ===== 2. Ollama 本地模型 =====
        self.category("2. Ollama 本地模型")
        self.test(
            "Qwen3:4B 快速推理",
            "http://localhost:11460/api/generate",
            method="POST",
            data={"model": "qwen3:4b", "prompt": "簡單回答：1+1=?", "stream": False},
            timeout=30
        )
        self.test(
            "Qwen3:8B 程式碼",
            "http://localhost:11460/api/generate",
            method="POST",
            data={"model": "qwen3:8b", "prompt": "寫一個 Python hello world", "stream": False},
            timeout=20
        )
        self.test(
            "Nomic Embedding",
            "http://localhost:11460/api/embeddings",
            method="POST",
            data={"model": "nomic-embed-text", "prompt": "測試文本"}
        )
        
        # ===== 3. Brain Server - 認證系統 =====
        self.category("3. 認證系統")
        self.test("用戶列表（需 admin）", "http://localhost:8002/api/auth/users")
        
        # ===== 4. Brain Server - 角色系統 =====
        self.category("4. 角色知識庫系統")
        self.test("角色列表", "http://localhost:8002/api/jarvis/roles")
        self.test("角色統計", "http://localhost:8002/api/jarvis/roles/stats")
        self.test("營建工程師統計", "http://localhost:8002/api/jarvis/roles/construction_engineer/stats")
        
        # ===== 5. Brain Server - 商用系統 =====
        self.category("5. 商用授權系統")
        self.test("License 驗證", "http://localhost:8002/api/commercial/license/validate")
        self.test("離線檢查", "http://localhost:8002/api/commercial/license/offline-check")
        self.test("裝置資訊", "http://localhost:8002/api/commercial/device-info")
        self.test("功能列表", "http://localhost:8002/api/commercial/features")
        self.test("系統狀態", "http://localhost:8002/api/commercial/system-status")
        
        # ===== 6. Brain Server - 用量計量 =====
        self.category("6. 用量計量系統")
        self.test("今日用量", "http://localhost:8002/api/usage/today")
        self.test("我的用量", "http://localhost:8002/api/usage/me")
        self.test("配額查詢", "http://localhost:8002/api/usage/quota")
        self.test("系統用量", "http://localhost:8002/api/usage/system")
        
        # ===== 7. Smart Bridge =====
        self.category("7. Smart Bridge 智慧橋接")
        self.test("專案列表", "http://localhost:8003/api/projects")
        self.test("成本統計", "http://localhost:8003/api/cost-stats")
        self.test("專案同步", "http://localhost:8003/api/projects/sync", method="POST")
        
        # ===== 8. AI Vision =====
        self.category("8. AI 視覺辨識")
        self.test("系統資訊", "http://localhost:8030/api/vision/info")
        self.test("模型列表", "http://localhost:8030/api/vision/models")
        self.test("歷史記錄", "http://localhost:8030/api/vision/history")
        self.test("系統統計", "http://localhost:8030/api/vision/stats")
        
        # ===== 9. CMS 營建管理 =====
        self.category("9. 營建管理系統")
        self.test("專案列表", "http://localhost:8020/api/projects")
        self.test("施工日誌", "http://localhost:8020/api/daily-logs?project_id=1")
        self.test("語音草稿", "http://localhost:8020/voice/drafts")
        
        # ===== 10. 外網域名 =====
        self.category("10. Cloudflare Tunnel 外網")
        self.test("Jarvis 外網", "https://jarvis.zhe-wei.net/health", timeout=15)
        self.test("Vision 外網", "https://vision.zhe-wei.net/healthz", timeout=15)
        self.test("CMS 外網", "https://cms.zhe-wei.net/api/projects", timeout=15)
        self.test("Bridge 外網", "https://bridge.zhe-wei.net/health", timeout=15)
        
        # 生成報告
        self.generate_report()
    
    def generate_report(self):
        """生成測試報告"""
        print("\n" + "="*60)
        print("📊 完整測試報告")
        print("="*60)
        
        total_passed = 0
        total_failed = 0
        
        for category, data in self.results["categories"].items():
            passed = data["passed"]
            failed = data["failed"]
            total = passed + failed
            total_passed += passed
            total_failed += failed
            
            status = "✅" if failed == 0 else "⚠️" if passed > failed else "❌"
            print(f"\n{status} {category}")
            print(f"   通過: {passed}/{total} ({passed/total*100:.1f}%)")
            
            # 顯示失敗的測試
            if failed > 0:
                for test in data["tests"]:
                    if not test["success"]:
                        print(f"   ❌ {test['name']}: {test['status']} - {test['response'][:80]}")
        
        total = total_passed + total_failed
        print("\n" + "="*60)
        print(f"總計: {total_passed}/{total} 通過 ({total_passed/total*100:.1f}%)")
        print(f"✅ 通過: {total_passed}")
        print(f"❌ 失敗: {total_failed}")
        print("="*60)
        
        # 儲存詳細報告
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 詳細報告已儲存至 {report_file}")
        
        # 系統健康度評估
        health_score = total_passed / total * 100
        if health_score >= 95:
            health_status = "🟢 優秀"
        elif health_score >= 85:
            health_status = "🟡 良好"
        elif health_score >= 70:
            health_status = "🟠 尚可"
        else:
            health_status = "🔴 需要關注"
        
        print(f"\n🏥 系統健康度: {health_status} ({health_score:.1f}%)")

if __name__ == "__main__":
    tester = ComprehensiveSystemTester()
    tester.run_all_tests()

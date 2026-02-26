#!/usr/bin/env python3
"""
築未科技 AI 系統全面功能測試腳本
包含：核心服務、Ollama 模型、Brain Server API、Smart Bridge、AI Vision、
商用系統、外網域名、Error Log 分析、點雲讀取、GPU/CPU 監控、自癒測試
"""
import requests
import json
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path


class SystemTester:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {}
        }
        self.error_log_path = "zhewei_memory/Experience/Error_Logs.jsonl"

    def test(self, name, url, method="GET", data=None, headers=None, expected_status=200, timeout=30):
        """執行單一測試"""
        try:
            if method == "GET":
                resp = requests.get(url, timeout=timeout)
            elif method == "POST":
                resp = requests.post(url, json=data, headers=headers, timeout=timeout)

            success = resp.status_code == expected_status
            result = {
                "name": name,
                "url": url,
                "status": resp.status_code,
                "success": success,
                "response": resp.text[:200] if not success else "✅"
            }
        except Exception as e:
            result = {
                "name": name,
                "url": url,
                "status": "ERROR",
                "success": False,
                "response": str(e)
            }

        self.results["tests"].append(result)
        status = "✅" if result["success"] else "❌"
        print(f"{status} {name}")
        return result["success"]

    def test_local_command(self, name, command, expected_result="success"):
        """執行本地指令測試"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if expected_result == "success":
                success = result.returncode == 0
            elif expected_result == "non_empty":
                success = len(result.stdout.strip()) > 0
            else:
                success = True

            response = result.stdout.strip() if result.stdout else result.stderr.strip()

            test_result = {
                "name": name,
                "command": command,
                "status": result.returncode,
                "success": success,
                "response": response[:200] if response else "✅"
            }
        except Exception as e:
            test_result = {
                "name": name,
                "command": command,
                "status": "ERROR",
                "success": False,
                "response": str(e)
            }

        self.results["tests"].append(test_result)
        status = "✅" if test_result["success"] else "❌"
        print(f"{status} {name}")
        return test_result["success"]

    def test_python_function(self, name, func, *args, **kwargs):
        """執行 Python 函式測試"""
        try:
            result = func(*args, **kwargs)
            success = result is not None

            test_result = {
                "name": name,
                "success": success,
                "response": str(result)[:200] if result else "❌ 無回傳值"
            }
        except Exception as e:
            test_result = {
                "name": name,
                "success": False,
                "response": str(e)
            }

        self.results["tests"].append(test_result)
        status = "✅" if test_result["success"] else "❌"
        print(f"{status} {name}")
        return test_result["success"]

    def run_all_tests(self):
        """執行所有測試"""
        print("\n" + "="*60)
        print("🧪 築未科技 AI 系統全面功能測試")
        print("="*60 + "\n")

        # 1. 核心服務健康檢查
        print("📋 1. 核心服務健康檢查")
        self.test("Brain Server", "http://localhost:8002/health")
        self.test("Smart Bridge", "http://localhost:8003/health")
        self.test("AI Vision", "http://localhost:8030/healthz")
        self.test("CMS 專案列表", "http://localhost:8020/api/projects")
        self.test("Ollama 服務", "http://localhost:11460/api/tags")

        # 2. Ollama 模型測試
        print("\n📋 2. Ollama 本地模型測試")
        self.test(
            "DeepSeek-R1 推理",
            "http://localhost:11460/api/generate",
            method="POST",
            data={
                "model": "deepseek-r1:14b",
                "prompt": "1+1=?",
                "stream": False
            }
        )

        self.test(
            "Embedding 模型",
            "http://localhost:11460/api/embeddings",
            method="POST",
            data={
                "model": "nomic-embed-text",
                "prompt": "測試文本"
            }
        )

        # 3. Brain Server API 測試
        print("\n📋 3. Brain Server API 測試")
        self.test("角色知識庫統計", "http://localhost:8002/api/jarvis/roles/stats")
        self.test("角色列表", "http://localhost:8002/api/jarvis/roles")
        self.test("系統自檢", "http://localhost:8002/api/jarvis/self-check")

        # 4. Smart Bridge 測試
        print("\n📋 4. Smart Bridge 測試")
        self.test("專案列表", "http://localhost:8003/api/projects")
        self.test("成本統計", "http://localhost:8003/api/cost-stats")

        # 5. AI Vision 測試
        print("\n📋 5. AI Vision 測試")
        self.test("系統資訊", "http://localhost:8030/api/vision/info")
        self.test("模型列表", "http://localhost:8030/api/vision/models")
        self.test("歷史記錄", "http://localhost:8030/api/vision/history")
        self.test("系統統計", "http://localhost:8030/api/vision/stats")

        # 6. 商用系統測試
        print("\n📋 6. 商用系統測試")
        self.test("License 驗證", "http://localhost:8002/api/commercial/license/validate")
        self.test("系統狀態", "http://localhost:8002/api/commercial/system-status")
        self.test("用量統計", "http://localhost:8002/api/usage/today")

        # 7. 外網域名測試
        print("\n📋 7. 外網域名測試")
        self.test("Jarvis 外網", "https://jarvis.zhe-wei.net/health")
        self.test("Vision 外網", "https://vision.zhe-wei.net/healthz")
        self.test("CMS 外網", "https://cms.zhe-wei.net/api/projects")
        self.test("Bridge 外網", "https://bridge.zhe-wei.net/health")

        # 8. Error Log 分析測試
        print("\n📋 8. Error Log 分析測試")
        self.test_error_log_analysis()

        # 9. RS10 點雲讀取測試
        print("\n📋 9. RS10 點雲讀取測試")
        self.test_pointcloud_reader()

        # 10. GPU/CPU 監控測試
        print("\n📋 10. GPU/CPU 監控測試")
        self.test_hardware_monitoring()

        # 11. 自癒系統測試
        print("\n📋 11. 自癒系統測試")
        self.test_self_healing()

        # 生成報告
        self.generate_report()

    def test_error_log_analysis(self):
        """Error Log 分析測試"""
        try:
            error_log_path = Path(self.error_log_path)
            if error_log_path.exists():
                with open(error_log_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    error_count = len([l for l in lines if l.strip()])
                    self.results["tests"].append({
                        "name": "Error Log 讀取",
                        "success": True,
                        "response": f"找到 {error_count} 筆錯誤記錄"
                    })
                    print(f"✅ Error Log 讀取: 找到 {error_count} 筆錯誤記錄")
            else:
                self.results["tests"].append({
                    "name": "Error Log 讀取",
                    "success": True,
                    "response": "無 Error Log 檔案"
                })
                print("✅ Error Log 讀取: 無 Error Log 檔案")
        except Exception as e:
            self.results["tests"].append({
                "name": "Error Log 讀取",
                "success": False,
                "response": str(e)
            })
            print(f"❌ Error Log 讀取: {e}")

    def test_pointcloud_reader(self):
        """RS10 點雲讀取測試"""
        try:
            # 測試 autonomous_coder 模組
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from ai_modules.autonomous_coder import RS10PointCloudReader

            reader = RS10PointCloudReader()
            files = reader.scan_directory()

            self.results["tests"].append({
                "name": "點雲掃描",
                "success": True,
                "response": f"找到 {len(files)} 個點雲檔案"
            })
            print(f"✅ 點雲掃描: 找到 {len(files)} 個點雲檔案")

            # 測試中繼資料讀取
            if files:
                metadata = reader.read_metadata(files[0]["path"])
                self.results["tests"].append({
                    "name": "點雲中繼資料讀取",
                    "success": "error" not in metadata,
                    "response": str(metadata)[:100]
                })
                print(f"✅ 點雲中繼資料讀取: {metadata.get('format', 'unknown')}")

        except Exception as e:
            self.results["tests"].append({
                "name": "點雲讀取測試",
                "success": False,
                "response": str(e)
            })
            print(f"❌ 點雲讀取測試: {e}")

    def test_hardware_monitoring(self):
        """GPU/CPU 監控測試"""
        # Python 環境檢查
        self.test_local_command(
            "Python 版本",
            "python --version",
            expected_result="non_empty"
        )

        # CUDA 檢查
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            self.results["tests"].append({
                "name": "CUDA 可用性",
                "success": True,
                "response": f"可用: {cuda_available}"
            })
            print(f"✅ CUDA 可用性: {cuda_available}")

            if cuda_available:
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
                self.results["tests"].append({
                    "name": "GPU 型號",
                    "success": True,
                    "response": f"{gpu_name}, {gpu_memory:.1f}GB"
                })
                print(f"✅ GPU 型號: {gpu_name}, {gpu_memory:.1f}GB")

        except ImportError:
            print("⚠️ PyTorch 未安裝，跳過 CUDA 檢查")

        # 記憶體檢查
        self.test_local_command(
            "系統記憶體",
            "wmic OS get TotalVisibleMemorySize,FreePhysicalMemory /value",
            expected_result="non_empty"
        )

    def test_self_healing(self):
        """自癒系統測試"""
        try:
            # 測試 autonomous_coder 模組
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from ai_modules.autonomous_coder import AutonomousSystemManager

            manager = AutonomousSystemManager()
            report = manager.run_self_check()

            self.results["tests"].append({
                "name": "自癒系統自檢",
                "success": True,
                "response": f"狀態: {report.get('overall_status', 'unknown')}"
            })
            print(f"✅ 自癒系統自檢: 狀態 {report.get('overall_status', 'unknown')}")

        except Exception as e:
            self.results["tests"].append({
                "name": "自癒系統測試",
                "success": False,
                "response": str(e)
            })
            print(f"❌ 自癒系統測試: {e}")

    def generate_report(self):
        """生成測試報告"""
        total = len(self.results["tests"])
        passed = sum(1 for t in self.results["tests"] if t.get("success", False))
        failed = total - passed

        print("\n" + "="*60)
        print("📊 測試報告")
        print("="*60)
        print(f"總測試數：{total}")
        print(f"✅ 通過：{passed}")
        print(f"❌ 失敗：{failed}")
        print(f"成功率：{passed/total*100:.1f}%")

        if failed > 0:
            print("\n❌ 失敗的測試：")
            for t in self.results["tests"]:
                if not t.get("success", False):
                    print(f"  - {t.get('name', 'Unknown')}: {str(t.get('response', ''))[:100]}")

        # 儲存報告
        with open("test_report.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print("\n📄 詳細報告已儲存至 test_report.json")


if __name__ == "__main__":
    tester = SystemTester()
    tester.run_all_tests()

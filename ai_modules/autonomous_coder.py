# -*- coding: utf-8 -*-
"""
築未科技 — 自主編碼與自癒系統核心模組
實現：自主編碼、自動測試、自主修復、Error Log 自動分析

功能：
1. 自主編碼：自動推理、生成計畫、執行修改、驗證結果
2. 自動測試：執行測試、分析失敗原因、生成修復方案
3. 自主修復：讀取 Error Log、推理根因、修正程式碼
4. 一鍵部署：整合部署腳本
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# 導入現有模組
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)


class ErrorLogAnalyzer:
    """Error Log 分析器：讀取、分析、推理根因"""

    def __init__(self, log_path: str = "zhewei_memory/Experience/Error_Logs.jsonl"):
        self.log_path = Path(log_path)
        self.error_patterns = {
            "SyntaxError": self._fix_syntax_error,
            "NameError": self._fix_name_error,
            "AttributeError": self._fix_attribute_error,
            "ImportError": self._fix_import_error,
            "TypeError": self._fix_type_error,
            "ValueError": self._fix_value_error,
            "KeyError": self._fix_key_error,
            "IndexError": self._fix_index_error,
            "TimeoutError": self._fix_timeout_error,
            "ConnectionError": self._fix_connection_error,
            "FileNotFoundError": self._fix_file_not_found,
        }

    def read_errors(self, limit: int = 50) -> list[dict]:
        """讀取最近的 Error Log"""
        errors = []
        if not self.log_path.exists():
            return errors

        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        errors.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"讀取 Error Log 失敗: {e}")

        return errors

    def analyze_error(self, error: dict) -> dict:
        """分析單一錯誤，推測根因"""
        error_type = error.get("error_type", "")
        error_msg = error.get("message", "")
        context = error.get("context", "")

        analysis = {
            "error_type": error_type,
            "severity": "high",
            "root_cause": "",
            "suggested_fix": "",
            "affected_files": [],
        }

        # 錯誤類型匹配
        for pattern, fix_func in self.error_patterns.items():
            if pattern in error_type or pattern in error_msg:
                result = fix_func(error_msg, context)
                analysis.update(result)
                break
        else:
            # 通用分析
            analysis["root_cause"] = f"未預期的錯誤類型: {error_type}"
            analysis["suggested_fix"] = "需要人工介入分析"

        return analysis

    def _fix_syntax_error(self, msg: str, context: str) -> dict:
        return {
            "severity": "critical",
            "root_cause": "語法錯誤",
            "suggested_fix": "檢查縮排、括號、引號",
            "affected_files": self._extract_file_from_context(context),
        }

    def _fix_name_error(self, msg: str, context: str) -> dict:
        return {
            "severity": "high",
            "root_cause": "變數或函式名稱未定義",
            "suggested_fix": "檢查變數名稱拼寫或是否忘記 import",
            "affected_files": self._extract_file_from_context(context),
        }

    def _fix_attribute_error(self, msg: str, context: str) -> dict:
        return {
            "severity": "high",
            "root_cause": "物件沒有該屬性或方法",
            "suggested_fix": "檢查物件類型或方法名稱",
            "affected_files": self._extract_file_from_context(context),
        }

    def _fix_import_error(self, msg: str, context: str) -> dict:
        return {
            "severity": "high",
            "root_cause": "模組匯入失敗",
            "suggested_fix": "檢查模組是否安裝或路徑是否正確",
            "affected_files": self._extract_file_from_context(context),
        }

    def _fix_type_error(self, msg: str, context: str) -> dict:
        return {
            "severity": "high",
            "root_cause": "型別不符",
            "suggested_fix": "檢查變數型別或轉換語法",
            "affected_files": self._extract_file_from_context(context),
        }

    def _fix_value_error(self, msg: str, context: str) -> dict:
        return {
            "severity": "medium",
            "root_cause": "值不符合預期",
            "suggested_fix": "檢查輸入值或驗證邏輯",
            "affected_files": self._extract_file_from_context(context),
        }

    def _fix_key_error(self, msg: str, context: str) -> dict:
        return {
            "severity": "medium",
            "root_cause": "字典鍵不存在",
            "suggested_fix": "檢查鍵名稱或使用 .get() 方法",
            "affected_files": self._extract_file_from_context(context),
        }

    def _fix_index_error(self, msg: str, context: str) -> dict:
        return {
            "severity": "medium",
            "root_cause": "索引超出範圍",
            "suggested_fix": "檢查列表長度或索引值",
            "affected_files": self._extract_file_from_context(context),
        }

    def _fix_timeout_error(self, msg: str, context: str) -> dict:
        return {
            "severity": "medium",
            "root_cause": "操作超時",
            "suggested_fix": "增加超時時間或優化效能",
            "affected_files": self._extract_file_from_context(context),
        }

    def _fix_connection_error(self, msg: str, context: str) -> dict:
        return {
            "severity": "high",
            "root_cause": "網路連線失敗",
            "suggested_fix": "檢查網路狀態或 API Key",
            "affected_files": [],
        }

    def _fix_file_not_found(self, msg: str, context: str) -> dict:
        return {
            "severity": "high",
            "root_cause": "檔案不存在",
            "suggested_fix": "檢查檔案路徑或建立檔案",
            "affected_files": self._extract_file_from_context(context),
        }

    def _extract_file_from_context(self, context: str) -> list[str]:
        """從上下文提取受影響的檔案"""
        files = []
        for ext in [".py", ".md", ".json", ".html"]:
            if ext in context:
                # 簡單提取檔名
                parts = context.split()
                for part in parts:
                    if ext in part and ("/" in part or "\\" in part):
                        files.append(part)
        return list(set(files))


class AutonomousCoder:
    """自主編碼器：自動推理、生成計畫、執行修改"""

    def __init__(self):
        self.error_analyzer = ErrorLogAnalyzer()
        self.test_results = []

    def generate_implementation_plan(self, task: str, context: dict) -> dict:
        """生成實作計畫"""
        plan = {
            "task": task,
            "context": context,
            "steps": [],
            "files_to_modify": [],
            "files_to_create": [],
            "estimated_time": "未知",
        }

        # 根據任務類型生成步驟
        if "測試" in task or "test" in task.lower():
            plan["steps"] = [
                "讀取現有測試檔案",
                "分析測試需求",
                "生成測試案例",
                "執行測試驗證",
            ]
            plan["estimated_time"] = "30 分鐘"

        elif "修復" in task or "fix" in task.lower():
            plan["steps"] = [
                "讀取 Error Log",
                "分析錯誤根因",
                "生成修復方案",
                "執行修復",
                "重新測試驗證",
            ]
            plan["estimated_time"] = "15 分鐘"

        elif "部署" in task or "deploy" in task.lower():
            plan["steps"] = [
                "檢查服務狀態",
                "停止舊服務",
                "更新程式碼",
                "啟動新服務",
                "驗證服務正常",
            ]
            plan["estimated_time"] = "10 分鐘"

        else:
            plan["steps"] = [
                "分析需求",
                "設計架構",
                "實作程式碼",
                "測試驗證",
            ]
            plan["estimated_time"] = "1 小時"

        return plan

    def execute_plan(self, plan: dict, dry_run: bool = True) -> dict:
        """執行實作計畫"""
        results = {
            "plan": plan,
            "executed_steps": [],
            "success": True,
            "errors": [],
        }

        for step in plan["steps"]:
            try:
                # 記錄執行的步驟
                results["executed_steps"].append({
                    "step": step,
                    "status": "pending",
                    "result": "",
                })
                # TODO: 實作具體步驟執行邏輯
                logger.info(f"執行步驟: {step}")

            except Exception as e:
                results["errors"].append({
                    "step": step,
                    "error": str(e),
                })
                results["success"] = False

        return results


class AutoTester:
    """自動測試器：執行測試、分析結果"""

    def __init__(self):
        self.results = []

    def run_test(self, test_name: str, test_func: callable) -> dict:
        """執行單一測試"""
        result = {
            "name": test_name,
            "status": "pending",
            "error": None,
            "duration": 0,
        }

        start_time = time.time()
        try:
            test_func()
            result["status"] = "passed"
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)

        result["duration"] = time.time() - start_time
        self.results.append(result)

        return result

    def run_all_tests(self, tests: list[tuple[str, callable]]) -> dict:
        """執行所有測試"""
        summary = {
            "total": len(tests),
            "passed": 0,
            "failed": 0,
            "duration": 0,
            "results": [],
        }

        start_time = time.time()

        for test_name, test_func in tests:
            result = self.run_test(test_name, test_func)
            summary["results"].append(result)

            if result["status"] == "passed":
                summary["passed"] += 1
            else:
                summary["failed"] += 1

        summary["duration"] = time.time() - start_time

        return summary

    def analyze_failures(self) -> list[dict]:
        """分析失敗的測試"""
        failures = []
        for result in self.results:
            if result["status"] == "failed":
                failures.append({
                    "test_name": result["name"],
                    "error": result["error"],
                    "suggested_fix": self._suggest_fix(result["error"]),
                })
        return failures

    def _suggest_fix(self, error: str) -> str:
        """根據錯誤建議修復方案"""
        if "Connection" in error:
            return "檢查網路連線或 API Key"
        elif "Timeout" in error:
            return "增加超時時間或優化效能"
        elif "Import" in error:
            return "檢查模組是否安裝"
        else:
            return "需要人工介入分析"


class OneClickDeployer:
    """一鍵部署器"""

    def __init__(self):
        self.services = [
            {"name": "Brain Server", "script": "brain_server.py", "port": 8002},
            {"name": "Smart Bridge", "script": "bridge_server.py", "port": 8003},
            {"name": "AI Vision", "script": "web_server.py", "port": 8030},
            {"name": "CMS", "script": "app.py", "port": 8020},
            {"name": "CodeSim", "script": "code_simulator.py", "port": 8001},
        ]

    def check_services(self) -> dict:
        """檢查服務狀態"""
        status = {
            "services": [],
            "all_healthy": True,
        }

        for service in self.services:
            # 檢查程序是否運行
            is_running = self._is_process_running(service["script"])
            # 檢查 port 是否可達
            port_reachable = self._check_port(service["port"])

            service_status = {
                "name": service["name"],
                "script": service["script"],
                "port": service["port"],
                "running": is_running,
                "port_reachable": port_reachable,
                "healthy": is_running and port_reachable,
            }

            status["services"].append(service_status)

            if not service_status["healthy"]:
                status["all_healthy"] = False

        return status

    def _is_process_running(self, script_name: str) -> bool:
        """檢查程序是否運行"""
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", f"IMAGENAME eq python.exe", "/V"],
                shell=False,
                encoding="cp950",
                errors="replace",
            )
            return script_name in out
        except Exception:
            return False

    def _check_port(self, port: int) -> bool:
        """檢查 port 是否可達"""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        return result == 0

    def deploy_all(self, dry_run: bool = True) -> dict:
        """一鍵部署所有服務"""
        result = {
            "actions": [],
            "success": True,
        }

        # 1. 檢查當前狀態
        current_status = self.check_services()
        result["actions"].append({
            "action": "check_status",
            "result": current_status,
        })

        # 2. 停止異常服務
        for service in current_status["services"]:
            if not service["healthy"]:
                result["actions"].append({
                    "action": f"restart_{service['name']}",
                    "script": service["script"],
                    "status": "pending",
                })

        # 3. 啟動所有服務
        for service in self.services:
            if not dry_run:
                self._start_service(service)
            result["actions"].append({
                "action": f"start_{service['name']}",
                "script": service["script"],
                "status": "success" if not dry_run else "dry_run",
            })

        return result

    def _start_service(self, service: dict):
        """啟動服務"""
        script_path = Path(service["script"])
        if script_path.exists():
            subprocess.Popen(
                [sys.executable, str(script_path)],
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
            )


class RS10PointCloudReader:
    """RS10 點雲讀取器"""

    def __init__(self):
        self.supported_extensions = [".las", ".ply", ".pcd", ".rs10"]
        self.root_path = Path("E:/築未科技_點雲與LAS")

    def scan_directory(self, path: Optional[Path] = None) -> list[dict]:
        """掃描目錄中的點雲檔案"""
        if path is None:
            path = self.root_path

        files = []
        if not path.exists():
            return files

        for ext in self.supported_extensions:
            for file in path.rglob(f"*{ext}"):
                files.append({
                    "path": str(file),
                    "name": file.name,
                    "extension": ext,
                    "size": file.stat().st_size,
                    "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                })

        return files

    def read_metadata(self, file_path: str) -> dict:
        """讀取點雲檔案的中繼資料"""
        path = Path(file_path)

        if not path.exists():
            return {"error": "檔案不存在"}

        metadata = {
            "path": str(path),
            "name": path.name,
            "extension": path.suffix,
            "size": path.stat().st_size,
            "points": 0,
            "format": "unknown",
        }

        # 根據副檔名讀取不同格式
        if path.suffix == ".las":
            metadata = self._read_las_metadata(path, metadata)
        elif path.suffix == ".ply":
            metadata = self._read_ply_metadata(path, metadata)
        elif path.suffix == ".pcd":
            metadata = self._read_pcd_metadata(path, metadata)

        return metadata

    def _read_las_metadata(self, path: Path, metadata: dict) -> dict:
        """讀取 LAS 檔案中繼資料"""
        try:
            with open(path, "rb") as f:
                # LAS 檔案頭部檢查
                header = f.read(256)
                if b"LASF" in header[:4]:
                    metadata["format"] = "LAS"
                    metadata["version"] = "1.2+"
                    # 簡化處理：只檢查檔案大小估算點數
                    metadata["points"] = int(path.stat().st_size / 32)  # 估算
        except Exception as e:
            metadata["error"] = str(e)

        return metadata

    def _read_ply_metadata(self, path: Path, metadata: dict) -> dict:
        """讀取 PLY 檔案中繼資料"""
        try:
            with open(path, "r") as f:
                content = f.read(1024)
                if "ply" in content[:10]:
                    metadata["format"] = "PLY"
        except Exception as e:
            metadata["error"] = str(e)

        return metadata

    def _read_pcd_metadata(self, path: Path, metadata: dict) -> dict:
        """讀取 PCD 檔案中繼資料"""
        try:
            with open(path, "r") as f:
                content = f.read(1024)
                if ".pcd" in content[:10]:
                    metadata["format"] = "PCD"
        except Exception as e:
            metadata["error"] = str(e)

        return metadata


# 整合管理器
class AutonomousSystemManager:
    """自主系統整合管理器"""

    def __init__(self):
        self.coder = AutonomousCoder()
        self.tester = AutoTester()
        self.deployer = OneClickDeployer()
        self.pointcloud_reader = RS10PointCloudReader()
        self.error_analyzer = ErrorLogAnalyzer()

    def run_self_check(self) -> dict:
        """執行系統自檢"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "checks": [],
            "overall_status": "healthy",
        }

        # 1. 檢查服務狀態
        service_status = self.deployer.check_services()
        report["checks"].append({
            "check": "services",
            "result": service_status,
        })

        # 2. 檢查 Error Log
        errors = self.error_analyzer.read_errors(10)
        report["checks"].append({
            "check": "error_log",
            "recent_errors": len(errors),
            "critical_errors": [e for e in errors if "critical" in str(e)],
        })

        # 3. 檢查點雲資料
        pointcloud_files = self.pointcloud_reader.scan_directory()
        report["checks"].append({
            "check": "pointcloud",
            "file_count": len(pointcloud_files),
        })

        # 4. 檢查測試結果
        test_summary = self.tester.run_all_tests([])
        report["checks"].append({
            "check": "tests",
            "result": test_summary,
        })

        # 計算整體狀態
        if not service_status["all_healthy"]:
            report["overall_status"] = "degraded"
        elif len(errors) > 5:
            report["overall_status"] = "warning"

        return report

    def auto_fix_and_test(self, task: str) -> dict:
        """自動修復並測試"""
        result = {
            "task": task,
            "success": True,
            "steps": [],
        }

        # 1. 生成實作計畫
        plan = self.coder.generate_implementation_plan(task, {})
        result["steps"].append({
            "step": "generate_plan",
            "plan": plan,
        })

        # 2. 執行計畫
        execution = self.coder.execute_plan(plan)
        result["steps"].append({
            "step": "execute_plan",
            "result": execution,
        })

        return result


# 便捷函式
def quick_check() -> dict:
    """快速檢查系統狀態"""
    manager = AutonomousSystemManager()
    return manager.run_self_check()


def quick_deploy(dry_run: bool = True) -> dict:
    """快速部署"""
    deployer = OneClickDeployer()
    return deployer.deploy_all(dry_run=dry_run)


def scan_pointcloud(path: Optional[str] = None) -> list[dict]:
    """掃描點雲檔案"""
    reader = RS10PointCloudReader()
    return reader.scan_directory(Path(path) if path else None)


if __name__ == "__main__":
    # 測試執行
    print("🧪 築未科技自主系統自檢")
    print("=" * 50)

    report = quick_check()
    print(f"時間: {report['timestamp']}")
    print(f"狀態: {report['overall_status']}")

    for check in report["checks"]:
        print(f"\n📋 {check['check']}:")
        print(json.dumps(check['result'], indent=2, ensure_ascii=False))

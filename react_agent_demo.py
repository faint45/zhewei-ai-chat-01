# -*- coding: utf-8 -*-
"""
築未科技 — ReAct 代理示範（核心修正版）
模擬任務分類、引擎分流與報表產出；實際運作應接 agent_logic.AgentManager 與 ai_service。
"""
import argparse
import json
import os
import sys
from datetime import datetime

# 路徑（可透過環境變數覆寫）
REPORT_ROOT = os.path.join(os.environ.get("ZHEWEI_MEMORY_ROOT", "Z:/Zhewei_Brain"), "Reports")
REPORT_FALLBACK = os.path.join(os.environ.get("BRAIN_WORKSPACE", "D:/brain_workspace"), "Zhewei_Brain", "Reports")


class MockAIService:
    """模擬 AI 服務呼叫；實際應接 ai_service.py 產出 JSON。"""

    def call(self, engine: str, prompt: str) -> str:
        return '{"action": "run_vision_engine", "action_input": "input/test.jpg"}'


def classify_task(task_text: str) -> str:
    """根據關鍵字強制分流。"""
    vision_keywords = ["分析", "jpg", "png", "辨識", "影片", "lpc"]
    task_lower = (task_text or "").lower()
    return "vision" if any(k in task_lower for k in vision_keywords) else "conversation"


class ReActAgent:
    def __init__(self):
        self.ai = MockAIService()
        self.max_iterations = 5

    def run(self, user_request: str) -> None:
        print("=" * 60)
        print("🧠 築未科技大腦 - 代理邏輯 (核心修正版)")
        print("=" * 60)

        task_type = classify_task(user_request)
        engine = "gemini" if task_type == "vision" else "ollama"

        enhanced_prompt = user_request
        if task_type == "vision":
            enhanced_prompt += "\n【本輪為視覺任務，請優先使用 run_vision_engine，再依辨識結果呼叫 generate_progress_report。】"

        print(f"📋 任務內容: {user_request}")
        print(f"🔀 任務分類: {task_type} → 優先引擎: {engine}")
        print("-" * 40)

        for i in range(self.max_iterations):
            print(f"--- 迭代 {i+1}/{self.max_iterations} ---")
            if task_type == "vision":
                print("🔧 動作: run_vision_engine")
                print("📤 結果: {'success': True, 'data': 'LPC 標記辨識完成', 'risk_level': 'Level 2'}")
                self.generate_progress_report(user_request, "Success", "LPC Detected")
                break
            else:
                print("🤖 處理一般對話任務...")
                break

    def generate_progress_report(self, task: str, status: str, detail: str) -> None:
        """產出報表至 Z 槽（或備援路徑）。"""
        z_root = os.path.dirname(REPORT_ROOT)
        report_dir = REPORT_ROOT if (z_root and os.path.exists(z_root)) else REPORT_FALLBACK
        os.makedirs(report_dir, exist_ok=True)
        filename = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_report.json"
        report_path = os.path.join(report_dir, filename)
        report_data = {
            "task": task,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "detail": detail,
            "system": "Zhewei_Brain_2.2",
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        print(f"📊 報告已生成: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="築未科技 AI 大腦指令介面")
    parser.add_argument("--task", type=str, required=True, help="下達給 AI 的任務指令")
    args = parser.parse_args()

    agent = ReActAgent()
    agent.run(args.task)

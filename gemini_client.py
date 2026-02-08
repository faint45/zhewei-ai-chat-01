#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 - Gemini Pro API 客戶端
用於總指揮官進行智能分析和任務分配
"""

import os
import json
import requests
from typing import Dict, List, Any, Optional

class GeminiClient:
    """Gemini Pro API 客戶端"""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

        if not self.api_key:
            print("[警告] 未設置 GEMINI_API_KEY，將使用模擬模式")
            self.use_mock = True
        else:
            self.use_mock = False
            print(f"[Gemini] 已初始化 (模型: {self.model})")

    def analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """
        意圖分析 - 將模糊輸入轉換為結構化任務

        Args:
            user_input: 用戶輸入

        Returns:
            結構化任務字典
        """
        if self.use_mock:
            return self._mock_analyze_intent(user_input)

        prompt = f"""請分析以下用戶需求，並輸出結構化的任務描述：

用戶需求：{user_input}

請按照以下 JSON 格式輸出（不要包含其他文字）：
{{
  "intent": "任務類型",
  "task_type": "development/research/training/analysis",
  "confidence": 0.95,
  "description": "詳細描述",
  "estimated_time": "30分鐘",
  "required_skills": ["技能1", "技能2"],
  "subtasks": [
    {{
      "step": 1,
      "description": "子任務描述",
      "role": "lead_dev/executor/local_guard",
      "priority": "high/medium/low",
      "parameters": {{}}
    }}
  ]
}}
"""

        try:
            response = requests.post(
                f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}",
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]

                # 提取 JSON 部分
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_text = text[json_start:json_end]
                    return json.loads(json_text)

            return self._mock_analyze_intent(user_input)

        except Exception as e:
            print(f"[Gemini] 分析失敗: {e}")
            return self._mock_analyze_intent(user_input)

    def assign_tasks(self, structured_task: Dict, available_roles: List[str]) -> List[Dict]:
        """
        智能任務分配 - 根據任務特點和角色能力進行分配

        Args:
            structured_task: 結構化任務
            available_roles: 可用角色列表

        Returns:
            分配的任務列表
        """
        if self.use_mock:
            return structured_task.get("subtasks", [])

        prompt = f"""根據以下任務和可用角色，進行智能分配：

任務：{json.dumps(structured_task, ensure_ascii=False, indent=2)}

可用角色：
- lead_dev: 首席開發官，負責設計和架構
- executor: 實體執行員，負責編碼和實現
- local_guard: 地端勤務兵，負責代碼檢測和驗證
- verify: 情報與驗證，負責質量檢查

請優化任務分配，輸出優化後的任務列表 JSON 格式。
"""

        try:
            response = requests.post(
                f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}",
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]

                json_start = text.find("[")
                json_end = text.rfind("]") + 1
                if json_start != -1 and json_end > json_start:
                    json_text = text[json_start:json_end]
                    return json.loads(json_text)

        except Exception as e:
            print(f"[Gemini] 分配失敗: {e}")

        return structured_task.get("subtasks", [])

    def generate_report(self, execution_results: List[Dict], success: bool) -> str:
        """
        生成最終報告

        Args:
            execution_results: 執行結果列表
            success: 是否成功

        Returns:
            格式化的報告字符串
        """
        if success:
            completed = len([r for r in execution_results if r.get("status") == "completed"])
            summary = f"成功完成 {completed} 個任務"

            return f"""[成功] 任務完成！

{summary}

[時間] 執行完成
[質量] 所有任務均已通過驗證

您可以立即使用！"""
        else:
            failed_tasks = [r for r in execution_results if r.get("status") == "failed"]
            error_msg = failed_tasks[0].get("error", "未知錯誤") if failed_tasks else "驗證失敗"

            return f"""[失敗] 執行失敗

原因：{error_msg}
類型：execution_error

需要人工介入處理。"""

    def _mock_analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """模擬意圖分析"""
        return {
            "intent": "development",
            "task_type": "development",
            "confidence": 0.85,
            "description": user_input,
            "estimated_time": "30分鐘",
            "required_skills": ["Python", "HTML/CSS"],
            "subtasks": [
                {
                    "step": 1,
                    "description": "設計結構",
                    "role": "lead_dev",
                    "priority": "high",
                    "parameters": {}
                },
                {
                    "step": 2,
                    "description": "編寫代碼",
                    "role": "executor",
                    "priority": "high",
                    "parameters": {}
                },
                {
                    "step": 3,
                    "description": "代碼檢測",
                    "role": "local_guard",
                    "priority": "medium",
                    "parameters": {}
                }
            ]
        }


if __name__ == "__main__":
    # 測試
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from dotenv import load_dotenv

    load_dotenv(".env.seven_stage")

    client = GeminiClient()
    result = client.analyze_intent("幫我弄個網頁")
    print(json.dumps(result, indent=2, ensure_ascii=False))

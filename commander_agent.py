#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 - Commander Agent (指揮官)
使用 Claude 3.5 Sonnet 作為核心調度器
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import anthropic
from datetime import datetime


class TaskType(Enum):
    """任務類型"""
    VISION = "vision"        # 視覺任務
    DEVELOPMENT = "development"  # 開發任務
    RETRIEVAL = "retrieval"  # 檢索任務
    SYSTEM = "system"       # 系統任務
    GENERAL = "general"     # 通用任務


class AgentType(Enum):
    """代理類型"""
    VISION_AGENT = "vision_agent"
    DEV_AGENT = "dev_agent"
    RETRIEVAL_AGENT = "retrieval_agent"
    OLLAMA_LOCAL = "ollama_local"


@dataclass
class Task:
    """任務數據結構"""
    task_id: str
    task_type: TaskType
    description: str
    parameters: Dict[str, Any]
    assigned_agent: AgentType
    priority: int = 1
    deadline: Optional[datetime] = None
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class CommanderAgent:
    """指揮官代理 - 任務調度核心"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)

        # 任務隊列
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
        self.failed_tasks: List[Task] = []

        # 工作區配置
        self.workspace_base = "D:/brain_workspace"

    def analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """
        意圖分析 - 將模糊輸入轉換為結構化任務

        Args:
            user_input: 用戶的模糊輸入（如「幫我弄個網頁」）

        Returns:
            結構化的意圖分析結果
        """
        prompt = f"""你是一個任務意圖分析專家。請分析用戶的輸入，並返回結構化的JSON。

用戶輸入：{user_input}

請返回以下JSON格式：
{{
  "intent": "主要意圖",
  "task_type": "vision|development|retrieval|system|general",
  "confidence": 0.95,
  "subtasks": [
    {{
      "step": 1,
      "description": "具體執行步驟",
      "agent": "vision_agent|dev_agent|retrieval_agent|ollama_local",
      "parameters": {{}}
    }}
  ],
  "estimated_time": "2小時",
  "resources_needed": ["YOLOv8", "RTX 4060 Ti", "Python"]
}}

只返回JSON，不要其他內容。"""

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            # 解析 JSON
            result = json.loads(response.content[0].text)
            return result

        except Exception as e:
            print(f"[Commander] 意圖分析失敗: {e}")
            return {
                "intent": "unknown",
                "task_type": "general",
                "confidence": 0.0,
                "subtasks": []
            }

    def assign_task(self, task: Task) -> bool:
        """
        分配任務給合適的代理

        Args:
            task: 要分配的任務

        Returns:
            是否成功分配
        """
        # 根據任務類型分配
        if task.task_type == TaskType.VISION:
            task.assigned_agent = AgentType.OLLAMA_LOCAL
        elif task.task_type == TaskType.DEVELOPMENT:
            task.assigned_agent = AgentType.DEV_AGENT
        elif task.task_type == TaskType.RETRIEVAL:
            task.assigned_agent = AgentType.RETRIEVAL_AGENT
        else:
            task.assigned_agent = AgentType.OLLAMA_LOCAL

        self.task_queue.append(task)
        print(f"[Commander] 任務已分配: {task.task_id} -> {task.assigned_agent.value}")
        return True

    def create_task_from_intent(self, user_input: str) -> List[Task]:
        """
        從用戶輸入創建任務列表

        Args:
            user_input: 用戶輸入

        Returns:
            任務列表
        """
        # 分析意圖
        intent = self.analyze_intent(user_input)

        # 創建任務
        tasks = []
        for i, subtask in enumerate(intent.get("subtasks", [])):
            task = Task(
                task_id=f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{i}",
                task_type=TaskType(intent.get("task_type", "general")),
                description=subtask["description"],
                parameters=subtask.get("parameters", {}),
                assigned_agent=AgentType(subtask.get("agent", "ollama_local")),
                priority=1
            )
            tasks.append(task)

        return tasks

    def verify_task_result(self, task: Task, result: Any) -> Dict[str, Any]:
        """
        驗證任務結果（異構驗證）

        Args:
            task: 已完成的任務
            result: 任務結果

        Returns:
            驗證結果
        """
        prompt = f"""你是一個代碼審查專家。請審查以下任務結果。

任務描述：{task.description}
任務類型：{task.task_type.value}

執行結果：
{json.dumps(result, indent=2, ensure_ascii=False) if isinstance(result, dict) else str(result)}

請返回以下JSON格式：
{{
  "status": "approved|needs_revision|rejected",
  "confidence": 0.95,
  "issues": [
    {{
      "type": "syntax|logic|performance|security",
      "description": "問題描述",
      "severity": "critical|high|medium|low"
    }}
  ],
  "suggestions": ["改進建議"],
  "revision_required": false
}}

只返回JSON，不要其他內容。"""

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            result = json.loads(response.content[0].text)
            return result

        except Exception as e:
            print(f"[Commander] 驗證失敗: {e}")
            return {
                "status": "approved",
                "confidence": 0.0,
                "issues": [],
                "suggestions": []
            }

    def generate_final_report(self, success: bool, details: Dict[str, Any]) -> str:
        """
        生成最終報告（只報喜）

        Args:
            success: 是否成功
            details: 詳細信息

        Returns:
            格式化的報告
        """
        if success:
            return f"""✅ 任務完成！

{details.get('summary', '所有工作已順利完成。')}

📁 結果位置：{details.get('output_path', 'N/A')}
⏱️ 執行時間：{details.get('execution_time', 'N/A')}
🎯 質量評分：{details.get('quality_score', 'N/A')}

您可以立即使用！🚀"""
        else:
            # 只報告關鍵錯誤（如硬體故障或權限問題）
            return f"""❌ 執行失敗

原因：{details.get('error', '未知錯誤')}
類型：{details.get('error_type', 'system_error')}

需要人工介入處理。"""


# 測試代碼
if __name__ == "__main__":
    # 測試 Commander
    commander = CommanderAgent()

    # 測試意圖分析
    test_input = "幫我弄個網頁，要有企業形象和聯絡表單"
    intent = commander.analyze_intent(test_input)

    print("=" * 50)
    print("意圖分析結果：")
    print(json.dumps(intent, indent=2, ensure_ascii=False))

    # 創建任務
    tasks = commander.create_task_from_intent(test_input)
    print("\n" + "=" * 50)
    print("生成的任務：")
    for task in tasks:
        print(f"- {task.task_id}: {task.description} -> {task.assigned_agent.value}")

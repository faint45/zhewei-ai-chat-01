#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 - Commander Agent (指揮官)
使用本地 Ollama 作為核心調度器（無需外部 API Key）
可選：若有 ANTHROPIC_API_KEY 則使用 Claude 作為高階引擎
"""

import os
import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

import requests


class TaskType(Enum):
    """任務類型"""
    VISION = "vision"
    DEVELOPMENT = "development"
    RETRIEVAL = "retrieval"
    SYSTEM = "system"
    GENERAL = "general"


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


_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "").strip().rstrip("/")


def _resolve_ollama_url() -> str:
    candidates = []
    if _OLLAMA_BASE_URL:
        candidates.append(_OLLAMA_BASE_URL)
    candidates.extend(["http://localhost:11460", "http://localhost:11434"])
    for base in candidates:
        try:
            r = requests.get(f"{base}/api/tags", timeout=2)
            if r.status_code == 200:
                return base
        except Exception:
            continue
    return candidates[0] if candidates else "http://localhost:11434"


def _resolve_model(base_url: str) -> str:
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=3)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            preferred = ["zhewei-brain:latest", "qwen3:32b", "qwen3:8b", "qwen3:4b", "gemma3:4b"]
            for m in preferred:
                if m in models:
                    return m
            for m in models:
                if "embed" not in m and "moondream" not in m and "llava" not in m:
                    return m
    except Exception:
        pass
    return "zhewei-brain:latest"


def _extract_json(text: str) -> Optional[Dict]:
    """從 LLM 回應中提取 JSON"""
    if not text:
        return None
    for pattern in (r"```json\s*([\s\S]*?)\s*```", r"```\s*([\s\S]*?)\s*```"):
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i+1])
                    except json.JSONDecodeError:
                        break
    return None


class CommanderAgent:
    """指揮官代理 - 任務調度核心（本地 Ollama 優先）"""

    def __init__(self):
        self.ollama_url = _resolve_ollama_url()
        self.ollama_model = _resolve_model(self.ollama_url)
        self.claude_client = None

        # 嘗試載入 Claude（可選）
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if api_key:
            try:
                import anthropic
                self.claude_client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                pass

        # 任務隊列
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
        self.failed_tasks: List[Task] = []
        self.workspace_base = "D:/brain_workspace"

        print(f"[Commander] Ollama: {self.ollama_url} | model: {self.ollama_model}")
        if self.claude_client:
            print("[Commander] Claude API 可用（高階引擎）")

    def _llm_call(self, prompt: str, temperature: float = 0.1) -> str:
        """統一 LLM 呼叫：優先 Ollama，Claude 作為備援"""
        # 先試 Ollama
        try:
            r = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.ollama_model, "prompt": prompt, "stream": False,
                      "options": {"temperature": temperature}},
                timeout=120,
            )
            if r.status_code == 200:
                return (r.json().get("response") or "").strip()
        except Exception:
            pass

        # 備援 Claude
        if self.claude_client:
            try:
                response = self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
            except Exception:
                pass

        return ""

    def analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """意圖分析 - 將模糊輸入轉換為結構化任務"""
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
  "estimated_time": "預估時間",
  "resources_needed": ["所需資源"]
}}

只返回JSON，不要其他內容。"""

        raw = self._llm_call(prompt)
        result = _extract_json(raw)
        if result:
            return result
        return {"intent": "unknown", "task_type": "general", "confidence": 0.0, "subtasks": []}

    def assign_task(self, task: Task) -> bool:
        """分配任務給合適的代理"""
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
        """從用戶輸入創建任務列表"""
        intent = self.analyze_intent(user_input)
        tasks = []
        for i, subtask in enumerate(intent.get("subtasks", [])):
            task = Task(
                task_id=f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{i}",
                task_type=TaskType(intent.get("task_type", "general")),
                description=subtask.get("description", ""),
                parameters=subtask.get("parameters", {}),
                assigned_agent=AgentType(subtask.get("agent", "ollama_local")),
                priority=1,
            )
            tasks.append(task)
        return tasks

    def verify_task_result(self, task: Task, result: Any) -> Dict[str, Any]:
        """驗證任務結果（異構驗證）"""
        prompt = f"""你是一個代碼審查專家。請審查以下任務結果。

任務描述：{task.description}
任務類型：{task.task_type.value}

執行結果：
{json.dumps(result, indent=2, ensure_ascii=False) if isinstance(result, dict) else str(result)}

請返回以下JSON格式：
{{
  "status": "approved|needs_revision|rejected",
  "confidence": 0.95,
  "issues": [],
  "suggestions": [],
  "revision_required": false
}}

只返回JSON，不要其他內容。"""

        raw = self._llm_call(prompt)
        parsed = _extract_json(raw)
        if parsed:
            return parsed
        return {"status": "approved", "confidence": 0.0, "issues": [], "suggestions": []}

    def generate_final_report(self, success: bool, details: Dict[str, Any]) -> str:
        """生成最終報告"""
        if success:
            return (
                f"✅ 任務完成！\n\n"
                f"{details.get('summary', '所有工作已順利完成。')}\n\n"
                f"📁 結果位置：{details.get('output_path', 'N/A')}\n"
                f"⏱️ 執行時間：{details.get('execution_time', 'N/A')}\n"
                f"🎯 質量評分：{details.get('quality_score', 'N/A')}\n\n"
                f"您可以立即使用！"
            )
        return (
            f"❌ 執行失敗\n\n"
            f"原因：{details.get('error', '未知錯誤')}\n"
            f"類型：{details.get('error_type', 'system_error')}\n\n"
            f"需要人工介入處理。"
        )


if __name__ == "__main__":
    commander = CommanderAgent()

    test_input = "幫我弄個網頁，要有企業形象和聯絡表單"
    intent = commander.analyze_intent(test_input)

    print("=" * 50)
    print("意圖分析結果：")
    print(json.dumps(intent, indent=2, ensure_ascii=False))

    tasks = commander.create_task_from_intent(test_input)
    print("\n" + "=" * 50)
    print("生成的任務：")
    for task in tasks:
        print(f"- {task.task_id}: {task.description} -> {task.assigned_agent.value}")

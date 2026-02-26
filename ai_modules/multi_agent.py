#!/usr/bin/env python3
"""
築未科技 — 多 Agent 協作模組 v2.0（CrewAI 替代方案）
支援多個 AI Agent 分工合作，複雜任務拆解執行

架構：
- Agent：可攜帶工具、可委派任務給其他 Agent
- Task：帶依賴關係的任務單元
- Crew：管理 Agent 團隊，支援 sequential / parallel 執行
- Tool：Agent 可呼叫的外部工具
- SharedMemory：Agent 之間共享的短期記憶

向後相容：PlannerAgent / ExecutorAgent / ReviewerAgent / MultiAgentCoordinator
"""

import json
import os
import time
import hashlib
import threading
import concurrent.futures
import requests
from typing import List, Dict, Optional, Callable, Any

OLLAMA_BASE = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11460").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:32b")


# ═══════════════════════════════════════════
# Tool 系統
# ═══════════════════════════════════════════

class Tool:
    """Agent 可呼叫的工具"""

    def __init__(self, name: str, description: str, func: Callable[..., str]):
        self.name = name
        self.description = description
        self.func = func

    def run(self, **kwargs) -> str:
        try:
            return str(self.func(**kwargs))
        except Exception as e:
            return f"[Tool {self.name} 錯誤] {e}"

    def to_prompt(self) -> str:
        return f"- {self.name}: {self.description}"


# ═══════════════════════════════════════════
# SharedMemory — Agent 之間共享的短期記憶
# ═══════════════════════════════════════════

class SharedMemory:
    """Agent 之間共享的短期記憶（線程安全）"""

    def __init__(self, max_entries: int = 100):
        self._store: Dict[str, Any] = {}
        self._log: List[Dict] = []
        self._max = max_entries
        self._lock = threading.Lock()

    def set(self, key: str, value: Any, agent: str = ""):
        with self._lock:
            self._store[key] = value
            self._log.append({"t": time.time(), "agent": agent, "key": key, "action": "set"})
            if len(self._log) > self._max:
                self._log = self._log[-self._max:]

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        return dict(self._store)

    def summary(self, max_items: int = 10) -> str:
        items = list(self._store.items())[-max_items:]
        if not items:
            return "（無共享記憶）"
        return "\n".join(f"- {k}: {str(v)[:200]}" for k, v in items)

    def clear(self):
        with self._lock:
            self._store.clear()
            self._log.clear()


# ═══════════════════════════════════════════
# Agent v2
# ═══════════════════════════════════════════

class Agent:
    """基礎 Agent — 支援工具呼叫、委派、共享記憶"""

    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        model: str = "",
        tools: Optional[List[Tool]] = None,
        allow_delegation: bool = False,
        memory: Optional[SharedMemory] = None,
        verbose: bool = False,
    ):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model or OLLAMA_MODEL
        self.base_url = OLLAMA_BASE
        self.tools = tools or []
        self.allow_delegation = allow_delegation
        self.memory = memory
        self.verbose = verbose
        self._delegates: Dict[str, "Agent"] = {}
        self._conversation: List[Dict] = []

    def add_delegate(self, agent: "Agent"):
        self._delegates[agent.name] = agent

    def run(self, task: str, context: str = "") -> str:
        """執行任務（支援工具呼叫 + 委派）"""
        system = self.system_prompt
        if self.tools:
            tool_desc = "\n".join(t.to_prompt() for t in self.tools)
            system += (
                f"\n\n你可以使用以下工具，用 JSON 格式呼叫："
                f'\n{{"tool": "工具名", "args": {{"參數": "值"}}}}'
                f"\n可用工具：\n{tool_desc}"
            )
        if self.allow_delegation and self._delegates:
            names = ", ".join(self._delegates.keys())
            system += (
                f"\n\n你可以委派任務給其他 Agent："
                f'\n{{"delegate": "Agent名", "task": "委派任務描述"}}'
                f"\n可委派對象：{names}"
            )
        if self.memory:
            mem_summary = self.memory.summary()
            if mem_summary != "（無共享記憶）":
                system += f"\n\n共享記憶：\n{mem_summary}"

        messages = [{"role": "system", "content": system}]
        if context:
            messages.append({"role": "user", "content": f"背景資訊：\n{context}\n\n任務：{task}"})
        else:
            messages.append({"role": "user", "content": task})

        response = self._call_llm(messages)

        # 嘗試解析工具呼叫或委派
        response = self._handle_actions(response, task, context)

        # 寫入共享記憶
        if self.memory:
            self.memory.set(f"{self.name}_last_output", response[:500], self.name)

        return response

    def _call_llm(self, messages: List[Dict]) -> str:
        try:
            r = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 2048, "num_gpu": 99},
                },
                timeout=120,
            )
            if r.status_code == 200:
                msg = r.json().get("message") or {}
                content = msg.get("content") or ""
                if not content.strip() and msg.get("thinking"):
                    content = msg["thinking"]
                return content.strip()
        except Exception as e:
            return f"[{self.name} 錯誤] {e}"
        return f"[{self.name}] 無回應"

    def _handle_actions(self, response: str, task: str, context: str) -> str:
        """解析並執行工具呼叫或委派"""
        try:
            # 找 JSON 區塊
            start = response.find("{")
            end = response.rfind("}") + 1
            if start < 0 or end <= start:
                return response
            action = json.loads(response[start:end])

            # 工具呼叫
            if "tool" in action and self.tools:
                tool_name = action["tool"]
                args = action.get("args", {})
                for t in self.tools:
                    if t.name == tool_name:
                        if self.verbose:
                            print(f"  [{self.name}] 呼叫工具: {tool_name}({args})")
                        tool_result = t.run(**args)
                        if self.memory:
                            self.memory.set(f"tool_{tool_name}", tool_result[:300], self.name)
                        return f"{response}\n\n工具結果：\n{tool_result}"

            # 委派
            if "delegate" in action and self.allow_delegation:
                delegate_name = action["delegate"]
                delegate_task = action.get("task", task)
                if delegate_name in self._delegates:
                    if self.verbose:
                        print(f"  [{self.name}] 委派給: {delegate_name}")
                    delegate_result = self._delegates[delegate_name].run(delegate_task, context)
                    return f"{response}\n\n{delegate_name} 回覆：\n{delegate_result}"
        except (json.JSONDecodeError, KeyError):
            pass
        return response


# ═══════════════════════════════════════════
# Task — 帶依賴的任務單元
# ═══════════════════════════════════════════

class Task:
    """任務單元（CrewAI Task 替代）"""

    def __init__(
        self,
        description: str,
        agent: Optional[Agent] = None,
        expected_output: str = "",
        context: str = "",
        depends_on: Optional[List["Task"]] = None,
        callback: Optional[Callable[[Dict], None]] = None,
    ):
        self.id = hashlib.md5(description.encode()).hexdigest()[:8]
        self.description = description
        self.agent = agent
        self.expected_output = expected_output
        self.context = context
        self.depends_on = depends_on or []
        self.callback = callback
        self.result: Optional[str] = None
        self.status: str = "pending"  # pending / running / done / failed
        self.elapsed: float = 0

    def execute(self, extra_context: str = "") -> str:
        self.status = "running"
        start = time.time()
        ctx_parts = []
        if self.context:
            ctx_parts.append(self.context)
        if extra_context:
            ctx_parts.append(extra_context)
        for dep in self.depends_on:
            if dep.result:
                ctx_parts.append(f"[{dep.description[:40]}] 結果：\n{dep.result[:500]}")
        full_ctx = "\n\n".join(ctx_parts)

        prompt = self.description
        if self.expected_output:
            prompt += f"\n\n期望輸出格式：{self.expected_output}"

        if self.agent:
            self.result = self.agent.run(prompt, full_ctx)
        else:
            self.result = f"[無指定 Agent] {prompt}"

        self.elapsed = round(time.time() - start, 2)
        self.status = "done"
        if self.callback:
            try:
                self.callback({"task_id": self.id, "result": self.result, "elapsed": self.elapsed})
            except Exception:
                pass
        return self.result


# ═══════════════════════════════════════════
# Crew — Agent 團隊管理（CrewAI Crew 替代）
# ═══════════════════════════════════════════

class Crew:
    """
    Agent 團隊 — 管理多個 Agent 和 Task 的執行

    支援：
    - sequential：依序執行所有 Task
    - parallel：無依賴的 Task 並行執行
    - hierarchical：Planner 自動分配 Task 給 Agent
    """

    def __init__(
        self,
        agents: Optional[List[Agent]] = None,
        tasks: Optional[List[Task]] = None,
        process: str = "sequential",  # sequential / parallel / hierarchical
        memory: Optional[SharedMemory] = None,
        verbose: bool = False,
        max_iterations: int = 3,
    ):
        self.agents = agents or []
        self.tasks = tasks or []
        self.process = process
        self.memory = memory or SharedMemory()
        self.verbose = verbose
        self.max_iterations = max_iterations
        self._results: List[Dict] = []

        # 讓所有 Agent 共享記憶
        for a in self.agents:
            a.memory = self.memory

    def kickoff(self, context: str = "") -> Dict:
        """啟動 Crew 執行所有 Task"""
        start = time.time()
        self._results = []

        if self.process == "parallel":
            self._run_parallel(context)
        elif self.process == "hierarchical":
            self._run_hierarchical(context)
        else:
            self._run_sequential(context)

        final_result = self.tasks[-1].result if self.tasks else ""
        return {
            "ok": all(t.status == "done" for t in self.tasks),
            "result": final_result,
            "task_results": [
                {"id": t.id, "desc": t.description[:60], "status": t.status,
                 "result": (t.result or "")[:300], "elapsed": t.elapsed}
                for t in self.tasks
            ],
            "elapsed": round(time.time() - start, 1),
            "process": self.process,
        }

    def _run_sequential(self, context: str):
        for task in self.tasks:
            if self.verbose:
                agent_name = task.agent.name if task.agent else "?"
                print(f"[Crew] 執行: {task.description[:50]}... → {agent_name}")
            task.execute(context)

    def _run_parallel(self, context: str):
        # 分層：先執行無依賴的，再執行有依賴的
        done_ids = set()
        remaining = list(self.tasks)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            while remaining:
                ready = [t for t in remaining if all(d.id in done_ids for d in t.depends_on)]
                if not ready:
                    # 避免死鎖：強制執行第一個
                    ready = [remaining[0]]
                futures = {pool.submit(t.execute, context): t for t in ready}
                for f in concurrent.futures.as_completed(futures):
                    t = futures[f]
                    done_ids.add(t.id)
                    remaining.remove(t)

    def _run_hierarchical(self, context: str):
        # 用第一個 Agent 當 Planner，自動分配任務
        if not self.agents:
            self._run_sequential(context)
            return
        planner = self.agents[0]
        task_descs = "\n".join(f"{i+1}. {t.description}" for i, t in enumerate(self.tasks))
        agent_descs = "\n".join(f"- {a.name} ({a.role})" for a in self.agents)
        plan_prompt = (
            f"以下是需要完成的任務：\n{task_descs}\n\n"
            f"可用的 Agent：\n{agent_descs}\n\n"
            f"請為每個任務指定最適合的 Agent，用 JSON 回傳："
            f'\n{{"assignments": [{{"task": 1, "agent": "Agent名"}}]}}'
        )
        plan = planner.run(plan_prompt, context)
        assignments = self._parse_assignments(plan)

        # 根據分配執行
        agent_map = {a.name: a for a in self.agents}
        for i, task in enumerate(self.tasks):
            assigned = assignments.get(i + 1)
            if assigned and assigned in agent_map:
                task.agent = agent_map[assigned]
            elif not task.agent and self.agents:
                task.agent = self.agents[min(i, len(self.agents) - 1)]
            task.execute(context)

    def _parse_assignments(self, text: str) -> Dict[int, str]:
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                return {a["task"]: a["agent"] for a in data.get("assignments", [])}
        except Exception:
            pass
        return {}


# ═══════════════════════════════════════════
# 預設 Agent（向後相容）
# ═══════════════════════════════════════════

class PlannerAgent(Agent):
    """規劃 Agent：分析任務、制定計畫"""

    def __init__(self, model: str = "", **kwargs):
        super().__init__(
            name="Planner",
            role="規劃師",
            system_prompt=(
                "你是一個任務規劃專家。你的職責是：\n"
                "1. 分析使用者的任務需求\n"
                "2. 將複雜任務拆解為可執行的步驟\n"
                "3. 為每個步驟指定負責的角色\n"
                "請用 JSON 格式回傳計畫：\n"
                '{"steps": [{"id": 1, "task": "步驟描述", "role": "executor/reviewer"}]}'
            ),
            model=model,
            **kwargs,
        )


class ExecutorAgent(Agent):
    """執行 Agent：執行具體步驟"""

    def __init__(self, model: str = "", **kwargs):
        super().__init__(
            name="Executor",
            role="執行者",
            system_prompt=(
                "你是一個任務執行專家。你的職責是：\n"
                "1. 根據指定的步驟精確執行\n"
                "2. 提供詳細的執行結果\n"
                "3. 如果遇到問題，清楚描述障礙\n"
                "請直接回傳執行結果。"
            ),
            model=model,
            **kwargs,
        )


class ReviewerAgent(Agent):
    """審查 Agent：檢查結果品質"""

    def __init__(self, model: str = "", **kwargs):
        super().__init__(
            name="Reviewer",
            role="審查員",
            system_prompt=(
                "你是一個品質審查專家。你的職責是：\n"
                "1. 檢查執行結果是否正確完整\n"
                "2. 找出潛在問題和改善空間\n"
                "3. 給出品質評分 (1-10)\n"
                "請用 JSON 格式回傳：\n"
                '{"score": 8, "issues": ["問題1"], "suggestions": ["建議1"], "approved": true}'
            ),
            model=model,
            **kwargs,
        )


class MultiAgentCoordinator:
    """
    多 Agent 協調器：管理 Agent 之間的協作
    """

    def __init__(self, model: str = ""):
        self.planner = PlannerAgent(model)
        self.executor = ExecutorAgent(model)
        self.reviewer = ReviewerAgent(model)
        self.history: List[Dict] = []

    def execute_task(self, task: str, context: str = "", max_iterations: int = 3) -> Dict:
        """
        執行複雜任務（多 Agent 協作）

        流程：
        1. Planner 制定計畫
        2. Executor 逐步執行
        3. Reviewer 審查結果
        4. 如果不通過，回到步驟 2 修正

        Returns:
            {"ok": bool, "result": str, "plan": list, "reviews": list, "iterations": int}
        """
        start_time = time.time()
        self.history = []

        # 1. 規劃
        plan_response = self.planner.run(task, context)
        self.history.append({"agent": "Planner", "output": plan_response})

        # 解析計畫
        steps = self._parse_plan(plan_response)
        if not steps:
            steps = [{"id": 1, "task": task, "role": "executor"}]

        # 2. 逐步執行 + 審查
        results = []
        reviews = []
        for iteration in range(max_iterations):
            # 執行所有步驟
            step_results = []
            for step in steps:
                exec_context = f"計畫步驟 {step['id']}: {step['task']}\n\n之前的結果：\n" + "\n".join(results[-3:]) if results else ""
                result = self.executor.run(step["task"], exec_context)
                step_results.append(result)
                self.history.append({"agent": "Executor", "step": step["id"], "output": result})

            combined_result = "\n\n".join(step_results)
            results.append(combined_result)

            # 3. 審查
            review_context = f"原始任務：{task}\n\n執行結果：\n{combined_result}"
            review = self.reviewer.run("請審查以下執行結果", review_context)
            self.history.append({"agent": "Reviewer", "output": review})
            reviews.append(review)

            # 檢查是否通過
            review_data = self._parse_review(review)
            if review_data.get("approved", False) or review_data.get("score", 0) >= 7:
                return {
                    "ok": True,
                    "result": combined_result,
                    "plan": steps,
                    "reviews": reviews,
                    "iterations": iteration + 1,
                    "score": review_data.get("score", 0),
                    "elapsed": round(time.time() - start_time, 1),
                }

        # 最大迭代後回傳最後結果
        return {
            "ok": True,
            "result": results[-1] if results else "無結果",
            "plan": steps,
            "reviews": reviews,
            "iterations": max_iterations,
            "score": self._parse_review(reviews[-1]).get("score", 5) if reviews else 5,
            "elapsed": round(time.time() - start_time, 1),
        }

    def quick_task(self, task: str) -> str:
        """快速任務：單 Agent 直接執行（不需要多 Agent 協作）"""
        return self.executor.run(task)

    def _parse_plan(self, text: str) -> List[Dict]:
        """解析計畫 JSON"""
        try:
            # 嘗試找到 JSON
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                return data.get("steps", [])
        except Exception:
            pass
        return []

    def _parse_review(self, text: str) -> Dict:
        """解析審查 JSON"""
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except Exception:
            pass
        return {"score": 5, "approved": False}


# ═══════════════════════════════════════════
# 全域單例 + 便捷函數
# ═══════════════════════════════════════════

_coordinator: Optional[MultiAgentCoordinator] = None
_crew: Optional[Crew] = None


def get_coordinator() -> MultiAgentCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = MultiAgentCoordinator()
    return _coordinator


def get_crew(process: str = "sequential", verbose: bool = False) -> Crew:
    """取得預設 Crew（含 Planner + Executor + Reviewer）"""
    global _crew
    if _crew is None:
        mem = SharedMemory()
        agents = [
            PlannerAgent(memory=mem),
            ExecutorAgent(memory=mem),
            ReviewerAgent(memory=mem),
        ]
        _crew = Crew(agents=agents, process=process, memory=mem, verbose=verbose)
    return _crew


def multi_agent_task(task: str, context: str = "") -> Dict:
    """便捷函數：多 Agent 協作執行任務"""
    return get_coordinator().execute_task(task, context)


def quick_task(task: str) -> str:
    """便捷函數：快速單 Agent 任務"""
    return get_coordinator().quick_task(task)


def crew_task(tasks: List[Dict], process: str = "sequential") -> Dict:
    """
    便捷函數：Crew 模式執行多任務

    Args:
        tasks: [{"description": str, "agent_role": "planner/executor/reviewer", "expected_output": str}]
        process: "sequential" / "parallel" / "hierarchical"

    Returns:
        Crew.kickoff() 結果
    """
    crew = get_crew(process)
    role_map = {"planner": crew.agents[0], "executor": crew.agents[1], "reviewer": crew.agents[2]}
    task_objs = []
    for t in tasks:
        agent = role_map.get(t.get("agent_role", "executor"), crew.agents[1])
        task_objs.append(Task(
            description=t["description"],
            agent=agent,
            expected_output=t.get("expected_output", ""),
            context=t.get("context", ""),
        ))
    crew.tasks = task_objs
    return crew.kickoff()

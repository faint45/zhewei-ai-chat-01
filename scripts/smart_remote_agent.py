# -*- coding: utf-8 -*-
"""
Smart Remote Agent - 智慧遙控代理
自然語言理解 + 多步驟任務規劃 + VLM 視覺理解 + 智慧搜尋
"""
import asyncio
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import urllib.request
import urllib.parse

import os

# 容器內使用 host.docker.internal，否則使用 localhost
HOST_API_URL = os.environ.get("HOST_API_URL", "http://host.docker.internal:8010")


def call_host_api(path: str, method: str = "GET", json_body: dict = None) -> dict:
    """呼叫 Host API。"""
    url = f"{HOST_API_URL}{path}"
    try:
        if method == "POST" and json_body:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        else:
            req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_screenshot(format: str = "base64") -> dict:
    """取得截圖。"""
    return call_host_api(f"/screenshot?format={format}")


def list_windows() -> dict:
    """列出視窗。"""
    return call_host_api("/windows")


def execute_command(command: str, cmd_type: str = "shell") -> dict:
    """執行命令。"""
    return call_host_api("/execute", method="POST", json_body={"command": command, "type": cmd_type})


def open_app(app_name: str) -> dict:
    """開啟應用程式。"""
    return call_host_api("/execute", method="POST", json_body={"command": app_name, "type": "app"})


def search_files(path: str, pattern: str) -> dict:
    """搜尋檔案。"""
    return call_host_api("/search", method="POST", json_body={"path": path, "pattern": pattern})


def open_terminal(term_type: str = "cmd", command: str = "") -> dict:
    """開啟終端機。"""
    return call_host_api("/open_terminal", method="POST", json_body={"type": term_type, "command": command})


def send_keystroke(text: str = "", keys: List[str] = None) -> dict:
    """傳送鍵盤輸入。"""
    return call_host_api("/keystroke", method="POST", json_body={"text": text, "keys": keys or []})


def mouse_action(action: str, x: int = 0, y: int = 0) -> dict:
    """滑鼠操作。"""
    return call_host_api("/mouse", method="POST", json_body={"action": action, "x": x, "y": y})


class SmartRemoteAgent:
    """智慧遙控代理。"""

    def __init__(self, llm_provider: str = "gemini", model: str = "gemini-2.5-flash"):
        self.llm_provider = llm_provider
        self.model = model
        self.history: List[Dict] = []
        self.execution_log: List[Dict] = []

    def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """呼叫 LLM。"""
        try:
            from ai_service import AIServiceFactory
            service = AIServiceFactory.get_service(self.llm_provider)
            if not system_prompt:
                system_prompt = "你是智慧遙控助手，用 JSON 回答。"
            response = service.chat(prompt, system_prompt=system_prompt, model=self.model)
            return response
        except Exception as e:
            return f"LLM 錯誤: {e}"

    def _call_vlm(self, instruction: str, screenshot_b64: str = None) -> dict:
        """呼叫 VLM 分析截圖。"""
        if not screenshot_b64:
            result = get_screenshot("base64")
            screenshot_b64 = result.get("image", "")
        if not screenshot_b64:
            return {"ok": False, "error": "無法取得截圖"}

        prompt = f"""
使用者指令: {instruction}

分析截圖，找出:
1. 可互動元素（按鈕、輸入框、選單等）的位置
2. 應該執行的動作（點擊座標、輸入文字等）
3. 規劃執行步驟

回傳 JSON:
{{
  "elements": [
    {{"type": "button|input|menu|window", "text": "文字", "x": X, "y": Y, "width": W, "height": H}}
  ],
  "plan": [
    {{"action": "click|type|hotkey", "target": "元素描述", "x": X, "y": Y, "text": "輸入文字"}}
  ],
  "reasoning": "為什麼這樣做"
}}
"""
        response = self._call_llm(prompt, "你是 GUI 分析專家，用 JSON 回傳分析結果。")
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            return json.loads(response)
        except:
            return {"ok": False, "raw": response}

    def _parse_instruction(self, instruction: str) -> dict:
        """解析自然語言指令為動作計劃。"""
        system_prompt = """
你是任務規劃專家。分析使用者指令，規劃執行步驟。

指令類型:
- open_app: 開啟軟體
- execute_cmd: 執行命令
- search_file: 搜尋檔案
- gui_action: GUI 操作
- open_terminal: 開啟終端機
- multi_step: 多步驟複合任務

回傳 JSON:
{
  "intent": "主要意圖",
  "type": "open_app|execute_cmd|search_file|gui_action|open_terminal|multi_step",
  "entities": {"app": "應用名", "command": "命令", "path": "路徑", "pattern": "模式"},
  "plan": [
    {"step": 1, "action": "動作", "target": "目標", "params": {}}
  ],
  "requires_vlm": 是否需要視覺分析,
  "confidence": 0.0-1.0
}
"""
        response = self._call_llm(instruction, system_prompt)
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            return json.loads(response)
        except:
            # Fallback: 智能解析常見指令
            instruction_lower = instruction.lower()
            
            # 開啟軟體映射表
            app_mapping = {
                "記事本": "notepad",
                "notepad": "notepad",
                "記事本notepad": "notepad",
                "計算機": "calc",
                "calc": "calc",
                "小算盤": "calc",
                "檔案總管": "explorer",
                "explorer": "explorer",
                "瀏覽器": "chrome",
                "chrome": "chrome",
                "edge": "edge",
                "word": "winword",
                "excel": "excel",
                "powerpoint": "powerpoint",
                "terminal": "cmd",
                "cmd": "cmd",
                "命令提示字元": "cmd",
                "powershell": "powershell",
                "vscode": "code",
                "code": "code",
            }
            
            # 檢查是否匹配常見軟體
            for app_name, cmd in app_mapping.items():
                if app_name in instruction_lower:
                    return {
                        "intent": instruction,
                        "type": "open_app",
                        "entities": {"app": app_name},
                        "plan": [{"step": 1, "action": "open_app", "target": cmd}],
                        "requires_vlm": False,
                        "confidence": 0.9
                    }
            
            # 預設 fallback
            return {"intent": instruction, "type": "multi_step", "plan": [{"step": 1, "action": "execute", "target": instruction}], "confidence": 0.5}

    def _execute_step(self, step: dict) -> dict:
        """執行單一步驟。"""
        action = step.get("action", "")
        target = step.get("target", "")
        params = step.get("params", {})

        result = {"step": step, "success": False, "output": ""}

        if action == "open_app":
            result.update(open_app(target))
        elif action == "execute_cmd":
            cmd = params.get("command", target)
            cmd_type = params.get("type", "shell")
            result.update(execute_command(cmd, cmd_type))
        elif action == "search_file":
            path = params.get("path", "C:\\Users")
            pattern = params.get("pattern", target)
            result.update(search_files(path, pattern))
        elif action == "open_terminal":
            term_type = params.get("type", "cmd")
            command = params.get("command", "")
            result.update(open_terminal(term_type, command))
        elif action == "click":
            x = params.get("x", 0)
            y = params.get("y", 0)
            result.update(mouse_action("click", x, y))
        elif action == "type":
            text = params.get("text", target)
            result.update(send_keystroke(text=text))
        elif action == "hotkey":
            keys = params.get("keys", target.split("+"))
            result.update(send_keystroke(keys=keys))
        elif action == "wait":
            time.sleep(params.get("seconds", 1))
            result["success"] = True
        elif action == "execute":
            # 通用執行：根據 target 判斷是開啟軟體還是執行命令
            cmd = params.get("command", target)
            cmd_type = params.get("type", "shell")
            result.update(execute_command(cmd, cmd_type))
        else:
            result["output"] = f"未知動作: {action}"

        result["success"] = result.get("ok", False)
        return result

    def _execute_vlm_plan(self, plan: dict) -> dict:
        """執行 VLM 規劃的動作。"""
        results = []
        for step in plan.get("plan", []):
            action = step.get("action", "")
            if action == "click":
                x = step.get("x", 0)
                y = step.get("y", 0)
                r = mouse_action("click", x, y)
            elif action == "type":
                r = send_keystroke(text=step.get("text", ""))
            elif action == "hotkey":
                r = send_keystroke(keys=step.get("keys", []))
            elif action == "wait":
                time.sleep(step.get("seconds", 1))
                r = {"ok": True}
            else:
                r = {"ok": False, "error": f"未知動作: {action}"}
            results.append(r)
            time.sleep(0.3)

        return {"ok": True, "steps_executed": len(results), "results": results}

    def run(self, instruction: str, execute: bool = True, max_steps: int = 10) -> dict:
        """執行智慧遙控任務。"""
        start_time = time.time()
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "instruction": instruction
        })

        result = {
            "instruction": instruction,
            "start_time": datetime.now().isoformat(),
            "steps": [],
            "success": False,
            "error": None
        }

        try:
            parsed = self._parse_instruction(instruction)
            result["parsed"] = parsed

            if parsed.get("requires_vlm"):
                vlm_result = self._call_vlm(instruction)
                result["vlm_analysis"] = vlm_result
                if execute and vlm_result.get("plan"):
                    exec_result = self._execute_vlm_plan(vlm_result)
                    result["vlm_execution"] = exec_result

            if not parsed.get("requires_vlm") or not execute:
                plan = parsed.get("plan", [])
                for i, step in enumerate(plan[:max_steps]):
                    step_result = self._execute_step(step)
                    result["steps"].append(step_result)
                    if not step_result.get("success"):
                        break
                    time.sleep(0.5)

            result["success"] = any(s.get("success") for s in result["steps"]) if result["steps"] else True
            result["steps_executed"] = len(result["steps"])

        except Exception as e:
            result["error"] = str(e)

        result["end_time"] = datetime.now().isoformat()
        result["duration_seconds"] = round(time.time() - start_time, 2)
        self.execution_log.append(result)
        return result

    def ask(self, question: str) -> str:
        """問答模式（不執行）。"""
        return self._call_llm(question, "你是智慧遙控助手，回答用戶問題。")

    def analyze_screen(self, focus_area: str = "全螢幕") -> dict:
        """分析當前螢幕。"""
        return self._call_vlm(f"分析{focus_area}，找出可互動元素。")


def smart_remote_run(instruction: str, execute: bool = True, provider: str = "gemini") -> dict:
    """便捷函數：執行智慧遙控。"""
    agent = SmartRemoteAgent(llm_provider=provider)
    return agent.run(instruction, execute=execute)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        instruction = " ".join(sys.argv[1:])
        result = smart_remote_run(instruction, execute=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("用法: python smart_remote_agent.py <指令>")
        print("範例: python smart_remote_agent.py 開啟記事本")
        print("範例: python smart_remote_agent.py 搜尋 D:\\ 的 *.py 檔案")
        print("範例: python smart_remote_agent.py 開啟終端機並執行 dir")

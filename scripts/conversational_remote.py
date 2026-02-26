# -*- coding: utf-8 -*-
"""
Conversational Remote - 對話式遙控系統
語音輸入 → AI 理解 → 執行 → 語音/文字回覆
無需看螢幕，像聊天一樣控制電腦
"""
import asyncio
import json
import time
from datetime import datetime
from typing import Optional, Callable
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from smart_remote_agent import SmartRemoteAgent, call_host_api, get_screenshot


class ConversationalRemote:
    """對話式遙控系統。"""

    def __init__(self, llm_provider: str = "gemini"):
        self.agent = SmartRemoteAgent(llm_provider=llm_provider)
        self.conversation_history = []
        self.execution_history = []
        self.context = {}

    def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """呼叫 LLM。"""
        try:
            from ai_service import AIServiceFactory
            service = AIServiceFactory.get_service(self.llm_provider)
            return service.chat(prompt, system_prompt=system_prompt)
        except Exception as e:
            return f"LLM 錯誤: {e}"

    def _summarize_result(self, result: dict) -> str:
        """將執行結果摘要為自然語言。"""
        if result.get("success"):
            steps = result.get("steps_executed", 0)
            duration = result.get("duration_seconds", 0)
            return f"✅ 已完成 {steps} 個步驟，耗時 {duration} 秒。"
        error = result.get("error", "未知錯誤")
        return f"❌ 執行失敗：{error}"

    def _parse_conversational(self, message: str) -> dict:
        """解析對話式指令。"""
        system_prompt = """
你是對話式遙控助手。用戶會用自然對話說想要做什麼，你需要理解並規劃動作。

常見意圖:
- execute_action: 執行具體動作（開軟體、搜尋、執行命令）
- ask_question: 問問題（不執行）
- check_status: 檢查狀態
- multi_step: 多步驟複合任務

回傳 JSON:
{
  "intent": "用戶意圖摘要",
  "type": "execute_action|ask_question|check_status|multi_step",
  "action": "具體動作描述",
  "params": {"command": "...", "app": "...", "path": "...", "search": "..."},
  "response_type": "explanation|confirmation|result",
  "needs_confirmation": 是否需要確認,
  "confidence": 0.0-1.0
}
"""
        response = self._call_llm(message, system_prompt)
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            return json.loads(response)
        except:
            return {"intent": message, "type": "execute_action", "action": message, "confidence": 0.5}

    def chat(self, message: str, execute: bool = True) -> dict:
        """
        對話式遙控主入口。
        
        Args:
            message: 用戶的自然語言訊息
            execute: 是否執行動作
        
        Returns:
            {"response": "回覆文字", "executed": bool, "result": dict}
        """
        timestamp = datetime.now().isoformat()
        self.conversation_history.append({"role": "user", "message": message, "timestamp": timestamp})

        parsed = self._parse_conversational(message)
        result = {
            "timestamp": timestamp,
            "user_message": message,
            "parsed": parsed,
            "executed": False,
            "response": "",
            "result": None
        }

        if parsed.get("needs_confirmation") and execute:
            confirm_prompt = f"用戶說：「{message}」，你想要：\n\n{parsed.get('intent')}\n\n確認執行嗎？請回覆「是」繼續，或「否」取消。"
            result["response"] = confirm_prompt
            result["needs_confirmation"] = True
            self.conversation_history.append({"role": "assistant", "message": confirm_prompt, "timestamp": datetime.now().isoformat()})
            return result

        if parsed.get("type") == "ask_question":
            answer = self.agent.ask(message)
            result["response"] = answer
            self.conversation_history.append({"role": "assistant", "message": answer, "timestamp": datetime.now().isoformat()})
            return result

        if parsed.get("type") == "check_status":
            status = self.get_system_status()
            result["response"] = status["summary"]
            result["result"] = status
            self.conversation_history.append({"role": "assistant", "message": status["summary"], "timestamp": datetime.now().isoformat()})
            return result

        if execute:
            action = parsed.get("action", message)
            exec_result = self.agent.run(action, execute=True)
            result["executed"] = True
            result["result"] = exec_result
            result["response"] = self._summarize_result(exec_result)
            self.execution_history.append(exec_result)
            self.conversation_history.append({"role": "assistant", "message": result["response"], "timestamp": datetime.now().isoformat()})
        else:
            plan = self.agent._parse_instruction(message)
            result["response"] = f"我打算：\n1. {plan.get('intent', message)}\n\n需要我執行嗎？"
            self.conversation_history.append({"role": "assistant", "message": result["response"], "timestamp": datetime.now().isoformat()})

        return result

    def get_system_status(self) -> dict:
        """取得系統狀態摘要。"""
        sysinfo = call_host_api("/sysinfo")
        windows = call_host_api("/windows")
        screenshot = get_screenshot("base64")

        win_count = len(windows.get("windows", [])) if windows.get("ok") else 0
        cpu = sysinfo.get("cpu_percent", "?")

        summary = f"""📊 系統狀態：
- CPU：{cpu}%
- 記憶體：{sysinfo.get('memory_percent', '?')}%
- 開啟視窗：{win_count} 個
- 截圖：{'✅' if screenshot.get('ok') else '❌'}"""

        return {
            "ok": True,
            "summary": summary,
            "details": {
                "sysinfo": sysinfo,
                "windows": windows,
                "screenshot": screenshot.get("ok")
            }
        }

    def get_conversation_history(self, limit: int = 20) -> list:
        """取得對話歷史。"""
        return self.conversation_history[-limit:]

    def clear_history(self):
        """清除對話歷史。"""
        self.conversation_history = []
        self.execution_history = []


def conversational_chat(message: str, execute: bool = True, provider: str = "gemini") -> dict:
    """便捷函數：對話式遙控。"""
    remote = ConversationalRemote(llm_provider=provider)
    return remote.chat(message, execute=execute)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        result = conversational_chat(message, execute=True)
        print(f"\n👤 你說：{message}")
        print(f"\n🤖 回覆：{result['response']}")
        if result.get('executed'):
            print(f"\n✅ 已執行 {result.get('result', {}).get('steps_executed', 0)} 步驟")
    else:
        print("對話式遙控系統")
        print("=" * 40)
        print("用法: python conversational_remote.py <指令>")
        print("範例: python conversational_remote.py 開啟記事本")
        print("範例: python conversational_remote.py 檢查系統狀態")
        print("範例: python conversational_remote.py 搜尋 D:\\ 的 Python 檔案")
        print()
        print("互動模式：")
        print("=" * 40)
        remote = ConversationalRemote()
        while True:
            try:
                msg = input("\n👤 你說：")
                if msg.lower() in ['exit', 'quit', '退出']:
                    break
                result = remote.chat(msg)
                print(f"\n🤖 回覆：{result['response']}")
            except KeyboardInterrupt:
                break
        print("\n再見！")

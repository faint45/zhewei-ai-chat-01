# -*- coding: utf-8 -*-
"""
築未科技 — AI 服務介面，對接 Google Gemini / Ollama / 阿里雲（預留）等
環境加載 .env；BaseAIService 抽象基類，各服務實作 chat(messages)；AIServiceFactory.create(provider) 一鍵切換。
"""
import asyncio
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

# 環境加載：讀取 .env 檔案中的 GEMINI_API_KEY（專案根目錄優先，再載入 ~/.openclaw/.env，不覆寫既有鍵）
try:
    from dotenv import load_dotenv
    ROOT = Path(__file__).resolve().parent
    load_dotenv(ROOT / ".env")
    ue = Path(os.path.expanduser("~/.openclaw/.env"))
    if ue.is_file():
        load_dotenv(ue, override=False)
except ImportError:
    pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_TIMEOUT = float(os.environ.get("GEMINI_TIMEOUT", "60"))

OLLAMA_BASE_URL = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_CODER_MODEL") or os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120"))


def _error_json(message: str) -> str:
    """回傳符合 ReAct 規範的 JSON 錯誤訊息，讓 AgentManager 能識別並結束。"""
    return json.dumps({"done": True, "result": message}, ensure_ascii=False)


class BaseAIService(ABC):
    """AI 服務抽象基類：所有引擎實作 chat(messages) -> str。"""

    @abstractmethod
    async def chat(self, messages: list) -> str:
        pass


def _react_to_gemini_history(messages: Sequence[dict]) -> tuple[str, list, str]:
    """
    將 ReAct 的歷史紀錄轉換為 Gemini 的對話格式。
    回傳 (system_instruction, history, last_user_content)。
    Gemini: history = [{"role": "user"|"model", "parts": [str]}, ...]；最後一則 user 單獨作為 send_message 的輸入。
    """
    system_instruction = ""
    gemini_history = []
    last_user_content = ""

    for m in messages:
        role = m.get("role", "")
        content = (m.get("content") or "").strip()
        if role == "system":
            system_instruction = content
        elif role == "user":
            last_user_content = content
            gemini_history.append({"role": "user", "parts": [content]})
        elif role == "assistant":
            gemini_history.append({"role": "model", "parts": [content]})

    # 最後一則為 user，作為本輪要送給 Gemini 的輸入；history 為其前的所有輪
    if gemini_history and gemini_history[-1]["role"] == "user":
        last_user_content = gemini_history[-1]["parts"][0]
        history_for_chat = gemini_history[:-1]
    else:
        history_for_chat = gemini_history

    return system_instruction, history_for_chat, last_user_content


def _gemini_chat_sync(messages: Sequence[dict]) -> str:
    """
    同步呼叫 Gemini：ReAct history 轉 Gemini 格式，start_chat + send_message。
    API 超時或失敗時回傳 _error_json(...)。
    """
    if not GEMINI_API_KEY:
        return _error_json("未設定 GEMINI_API_KEY，請在 .env 或 ~/.openclaw/.env 設定。")

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        system_instruction, history_for_chat, last_user_content = _react_to_gemini_history(messages)
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            system_instruction=system_instruction or None,
        )
        chat = model.start_chat(history=history_for_chat)
        response = chat.send_message(last_user_content or "請回覆。")
        if response and response.text:
            return response.text.strip()
        return _error_json("Gemini 未回傳文字。")
    except Exception as e:
        return _error_json(f"API 錯誤: {e}")


class AIService(BaseAIService):
    """
    對接 Google Gemini API：實作 chat(messages) 異步方法，
    將 ReAct 的歷史紀錄轉換為 Gemini 的對話格式並呼叫 API；
    超時或失敗時回傳符合規範的 JSON 錯誤訊息供 AgentManager 識別。
    """

    async def chat(self, messages: list) -> str:
        """
        異步呼叫 Gemini；messages 為 ReAct history（含 system / user / assistant）。
        內部轉為 Gemini 對話格式並以 run_in_executor 執行同步請求，帶超時。
        """
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_gemini_chat_sync, list(messages)),
                timeout=GEMINI_TIMEOUT,
            )
        except asyncio.TimeoutError:
            return _error_json(f"API 逾時（{GEMINI_TIMEOUT} 秒）。")
        except Exception as e:
            return _error_json(f"呼叫失敗: {e}")


# 供 brain_server 等模組使用：from ai_service import GeminiService, OllamaService
GeminiService = AIService


def _react_to_ollama_messages(messages: Sequence[dict]) -> list[dict]:
    """將 ReAct 歷史轉為 Ollama /api/chat 的 messages：system 併入首則 user，其餘 user/assistant 照搬。"""
    out = []
    system_parts = []
    for m in messages:
        role = m.get("role", "")
        content = (m.get("content") or "").strip()
        if role == "system":
            system_parts.append(content)
        elif role == "user":
            content = ("\n\n".join(system_parts) + "\n\n" + content).strip() if system_parts else content
            system_parts = []
            out.append({"role": "user", "content": content})
        elif role == "assistant":
            out.append({"role": "assistant", "content": content})
    return out


class OllamaService(BaseAIService):
    """
    本地大腦：呼叫本地 Ollama 服務（Qwen2.5-Coder 等），免費/消耗電力。
    使用 httpx 非同步 POST /api/chat；stream=False，options 確保輸出穩定、擴大上下文。
    若服務異常，回傳 JSON 錯誤（含 done: True）讓 AgentManager 識別。
    """

    def __init__(self, model_name: str | None = None):
        base = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        self.base_url = f"{base}/api/chat"
        self.model_name = model_name or OLLAMA_MODEL
        self.timeout = OLLAMA_TIMEOUT

    async def chat(self, messages: list) -> str:
        """
        呼叫本地 Ollama 服務；messages 為 ReAct history，會先轉為 Ollama 的 messages 格式。
        """
        ollama_messages = _react_to_ollama_messages(list(messages))
        if not ollama_messages:
            return _error_json("Ollama：無有效對話內容。")

        payload = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": 0.2,  # 降低溫度以提高穩定性 [cite: 2026-02-05]
                "num_ctx": 8192,     # 擴大上下文，適合處理長程式碼
            },
        }

        try:
            import httpx
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.base_url, json=payload)
                response.raise_for_status()
                result = response.json()
                content = (result.get("message") or {}).get("content") or ""
                return content.strip() or _error_json("Ollama 未回傳文字。")
        except Exception as e:
            # 若本地服務異常，回傳 JSON 錯誤讓 Manager 識別（done + result 與 ReAct 一致）
            return _error_json(f"Ollama 服務異常: {e}")


class AliyunService(BaseAIService):
    """預留：阿里雲通義千問 (Qwen API)，未來對接 DashScope API。"""

    async def chat(self, messages: list) -> str:
        # 未來在此處對接 DashScope API
        return json.dumps({"thought": "阿里雲正在思考...", "done": True, "result": "阿里雲服務尚未接線。"}, ensure_ascii=False)


class TencentService(BaseAIService):
    """預留：騰訊雲混元等，尚未接線。"""

    async def chat(self, messages: list) -> str:
        return _error_json("騰訊雲服務尚未接線，請使用 gemini 或 ollama。")


ANTHROPIC_API_KEY = (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY") or "").strip()
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
ANTHROPIC_TIMEOUT = float(os.environ.get("ANTHROPIC_TIMEOUT", "120"))


class ClaudeService(BaseAIService):
    """
    階段 4/6 編碼與回饋修正：對接 Anthropic Claude API。
    有設 ANTHROPIC_API_KEY 或 CLAUDE_API_KEY 時，agent_logic 可注入供階段 4/6 使用。
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = (api_key or ANTHROPIC_API_KEY).strip()
        self.model = model or ANTHROPIC_MODEL
        self.timeout = ANTHROPIC_TIMEOUT

    async def chat(self, messages: list) -> str:
        if not self.api_key:
            return _error_json("未設定 ANTHROPIC_API_KEY 或 CLAUDE_API_KEY，請在 .env 設定。")
        system_parts = []
        anthropic_messages = []
        for m in messages:
            role = m.get("role", "")
            content = (m.get("content") or "").strip()
            if role == "system":
                system_parts.append(content)
            elif role == "user":
                anthropic_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                anthropic_messages.append({"role": "assistant", "content": content})
        if not anthropic_messages:
            return _error_json("Claude：無有效對話內容。")
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=self.api_key)
            system = "\n\n".join(system_parts).strip() if system_parts else None
            response = await asyncio.wait_for(
                client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system or None,
                    messages=anthropic_messages,
                ),
                timeout=self.timeout,
            )
            text = (response.content[0].text if response.content else "").strip()
            return text or _error_json("Claude 未回傳文字。")
        except asyncio.TimeoutError:
            return _error_json(f"Claude API 逾時（{self.timeout} 秒）。")
        except Exception as e:
            return _error_json(f"Claude API 錯誤: {e}")


class SmartAIService(BaseAIService):
    """
    智能調度：本地優先策略 [cite: 2026-02-05]
    - 簡單任務 / 程式碼片段：強制本地（節省金幣）
    - 複雜任務：先試 Ollama，失敗或邏輯不足再轉 Gemini
    """

    def __init__(self, gemini_service: BaseAIService | None = None, ollama_service: BaseAIService | None = None):
        self.gemini = gemini_service if gemini_service is not None else AIService()
        self.ollama = ollama_service if ollama_service is not None else OllamaService()
        self.threshold = 0.7  # 信心水準門檻 [cite: 2026-02-05]

    async def _call_ollama(self, messages: list) -> str:
        """接現有 Ollama 呼叫邏輯 [cite: 2026-02-05]"""
        return await self.ollama.chat(messages)

    async def _call_gemini(self, messages: list) -> str:
        """接現有 Gemini API 呼叫邏輯"""
        return await self.gemini.chat(messages)

    async def smart_request(self, prompt: str, task_type: str = "conversation") -> str:
        """
        智能調度入口：本地優先策略 [cite: 2026-02-05]
        prompt 為單一使用者輸入時使用；若需 ReAct 全歷史請用 chat(messages)。
        """
        messages = [{"role": "user", "content": prompt}]
        if task_type == "code_snippet" or len(prompt) < 100:
            return await self._call_ollama(messages)
        try:
            print("🛡️ 防護盾：嘗試使用本地算力 (RTX 4060 Ti)...")
            response = await self._call_ollama(messages)
            if "Unknown action" in (response or "") or not (response or "").strip():
                raise Exception("本地邏輯信心不足")
            return response
        except Exception as e:
            print(f"💰 本地防線失守 (原因: {e})，啟動 Gemini 救援...")
            return await self._call_gemini(messages)

    async def chat(self, messages: list) -> str:
        """
        與 BaseAIService 一致：ReAct 全歷史調度。短內容強制本地，否則先本地後雲端。
        """
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = (m.get("content") or "").strip()
                break
        if len(last_user) < 100:
            return await self._call_ollama(messages)
        try:
            print("🛡️ 防護盾：嘗試使用本地算力 (RTX 4060 Ti)...")
            response = await self._call_ollama(messages)
            if "Unknown action" in (response or "") or not (response or "").strip():
                raise Exception("本地邏輯信心不足")
            return response
        except Exception as e:
            print(f"💰 本地防線失守 (原因: {e})，啟動 Gemini 救援...")
            return await self._call_gemini(messages)


class AIServiceFactory:
    """服務工廠：一鍵切換雲端引擎；預設本地 Ollama 最省錢。"""

    @staticmethod
    def create(provider: str) -> BaseAIService:
        if provider == "gemini":
            return GeminiService()
        if provider == "ollama":
            return OllamaService()
        if provider == "claude":
            return ClaudeService()
        if provider == "aliyun":
            return AliyunService()
        if provider == "tencent":
            return TencentService()
        return OllamaService()  # 預設本地最省錢

    get_service = create  # 相容舊用法

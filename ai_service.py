# -*- coding: utf-8 -*-
"""
築未科技 — AI 服務介面，對接 Google Gemini / Ollama / DeepSeek / MiniMax 等
環境加載 .env；BaseAIService 抽象基類，各服務實作 chat(messages)；AIServiceFactory.create(provider) 一鍵切換。
"""
import asyncio
import json
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

# 用量追蹤
try:
    from ai_usage_tracker import usage_tracker, track_api_call
    USAGE_TRACKING = True
except ImportError:
    USAGE_TRACKING = False
    def track_api_call(*args, **kwargs): pass

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
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TIMEOUT = float(os.environ.get("GEMINI_TIMEOUT", "90"))
GEMINI_FALLBACK_MODELS = [
    x.strip()
    for x in (os.environ.get("GEMINI_FALLBACK_MODELS") or "gemini-2.5-flash,gemini-2.5-pro,gemini-2.0-flash,gemini-1.5-flash").split(",")
    if x.strip()
]

OLLAMA_BASE_URL = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11460").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_CODER_MODEL") or os.environ.get("OLLAMA_MODEL", "qwen3:32b")
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120"))
OLLAMA_STRONG_MODEL = os.environ.get("OLLAMA_STRONG_MODEL", "qwen3:32b")
OLLAMA_FAST_MODEL = os.environ.get("OLLAMA_FAST_MODEL", "qwen3:4b")
OLLAMA_BRAIN_MODEL = os.environ.get("OLLAMA_BRAIN_MODEL", "zhewei-brain-v5-structured")

LLAMA_SWAP_URL = (os.environ.get("LLAMA_SWAP_URL") or "http://localhost:10005").rstrip("/")
LLAMA_SWAP_MODEL = os.environ.get("LLAMA_SWAP_MODEL", "qwen3-32b")
LLAMA_SWAP_TIMEOUT = float(os.environ.get("LLAMA_SWAP_TIMEOUT", "120"))

MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "").strip()
MINIMAX_MODEL = os.environ.get("MINIMAX_MODEL", "MiniMax-M2.5")
MINIMAX_API_URL = os.environ.get("MINIMAX_API_URL", "https://api.minimax.io/v1/text/chatcompletion_v2")
MINIMAX_TIMEOUT = float(os.environ.get("MINIMAX_TIMEOUT", "120"))

# 智慧路由模式：local_only（純本地零雲端）/ local_first（本地優先）/ smart_route / cloud_first
AI_COST_MODE = os.environ.get("AI_COST_MODE", "local_only").strip().lower()
OLLAMA_REASON_MODEL = os.environ.get("OLLAMA_REASON_MODEL", "deepseek-r1:14b")


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

        candidates = []
        for m in [GEMINI_MODEL, *GEMINI_FALLBACK_MODELS]:
            if m not in candidates:
                candidates.append(m)

        last_error = ""
        for model_name in candidates:
            try:
                model = genai.GenerativeModel(
                    model_name,
                    system_instruction=system_instruction or None,
                )
                chat = model.start_chat(history=history_for_chat)
                response = chat.send_message(last_user_content or "請回覆。")
                if response and response.text:
                    return response.text.strip()
                last_error = f"{model_name}: Gemini 未回傳文字。"
            except Exception as e:
                msg = str(e)
                last_error = f"{model_name}: {msg}"
                # model not found -> try next candidate
                if ("404" in msg and "not found" in msg.lower()) or ("is not found" in msg.lower()):
                    continue
                # other errors can still fallback to next model once
                continue

        return _error_json(f"API 錯誤: {last_error or 'unknown'}")
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
    本地大腦：呼叫本地 Ollama 服務（Qwen3:8B 等），免費/消耗電力。
    使用 httpx 非同步 POST /api/chat；stream=False，options 確保輸出穩定、擴大上下文。
    若服務異常，回傳 JSON 錯誤（含 done: True）讓 AgentManager 識別。
    增強穩定性：自動重試、健康檢查、多模型備援。
    """

    def __init__(self, model_name: str | None = None):
        base = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11460").rstrip("/")
        self.base_url = f"{base}/api/chat"
        self.model_name = model_name or OLLAMA_MODEL
        self.timeout = OLLAMA_TIMEOUT
        self.fallback_models = ["qwen3:8b", "qwen3:4b", "gemma3:4b", "zhewei-brain"]
        self._health_checked = False

    async def _health_check(self) -> bool:
        """健康檢查：確認 Ollama 服務可用"""
        try:
            import httpx
            base = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11460").rstrip("/")
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{base}/api/tags")
                if r.status_code == 200:
                    data = r.json()
                    models = [m["name"] for m in data.get("models", [])]
                    self._health_checked = True
                    return any(self.model_name in m for m in models)
            return False
        except Exception:
            return False

    async def chat(self, messages: list) -> str:
        """
        呼叫本地 Ollama 服務；messages 為 ReAct history，會先轉為 Ollama 的 messages 格式。
        增強穩定性：自動重試、模型備援。
        """
        # 首次健康檢查
        if not self._health_checked:
            if not await self._health_check():
                return _error_json("Ollama 服務未響應，請確認 Ollama 已啟動 (localhost:11434)")

        ollama_messages = _react_to_ollama_messages(list(messages))
        if not ollama_messages:
            return _error_json("Ollama：無有效對話內容。")

        # 嘗試主要模型
        content = await self._try_generate(self.model_name, ollama_messages)
        if content:
            return content

        # 模型失敗，嘗試備援模型
        for fallback in self.fallback_models:
            if fallback != self.model_name:
                content = await self._try_generate(fallback, ollama_messages)
                if content:
                    return content

        return _error_json("所有本地模型均無法回應，請檢查 Ollama 服務狀態")

    async def _try_generate(self, model: str, messages: list) -> str | None:
        """嘗試生成回應（支援 Qwen3 thinking 模式 + GPU offload）"""
        import httpx
        # 根據模型大小自動配置
        # 注意：不指定 num_gpu 讓 Ollama 自動跨雙卡分配（硬編碼 99 會報 memory layout 錯誤）
        num_ctx = 8192
        options = {
            "temperature": 0.2,
            "num_ctx": num_ctx,
            "num_batch": 512,
        }
        if "70b" in model or "72b" in model:
            options["num_gpu"] = 12  # 70B 需 CPU offload，限制 GPU 層數
            options["num_ctx"] = 2048
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.base_url, json=payload)
                response.raise_for_status()
                result = response.json()
                msg = result.get("message") or {}
                content = msg.get("content") or ""
                # Qwen3 thinking 模式：content 可能為空，真正答案在 thinking 欄位
                if not content.strip() and msg.get("thinking"):
                    content = msg["thinking"]
                return content.strip() if content else None
        except Exception:
            return None


class LiteLLMService(BaseAIService):
    """
    LiteLLM 統一路由：透過單一介面呼叫 100+ LLM 提供商。
    支援 OpenAI / Anthropic / Gemini / Ollama / DeepSeek / Groq 等。
    """

    def __init__(self, model: str = "ollama/qwen3:8b"):
        self.model = model
        self.timeout = 120

    async def chat(self, messages: list) -> str:
        try:
            import litellm
            litellm.set_verbose = False
            # 轉換 messages 格式
            llm_messages = []
            for m in messages:
                role = m.get("role", "user")
                content = (m.get("content") or "").strip()
                if content:
                    llm_messages.append({"role": role, "content": content})
            if not llm_messages:
                return _error_json("LiteLLM：無有效對話內容。")

            response = await asyncio.wait_for(
                asyncio.to_thread(
                    litellm.completion,
                    model=self.model,
                    messages=llm_messages,
                    temperature=0.2,
                    max_tokens=4096,
                ),
                timeout=self.timeout,
            )
            text = (response.choices[0].message.content or "").strip()
            return text or _error_json("LiteLLM 未回傳文字。")
        except asyncio.TimeoutError:
            return _error_json(f"LiteLLM 逾時（{self.timeout} 秒）。")
        except Exception as e:
            return _error_json(f"LiteLLM 錯誤: {e}")


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


class MiniMaxService(BaseAIService):
    """
    MiniMax M2.5 — 開源前沿推理模型（230B MoE, 10B active）。
    性能匹配 Claude Opus 4.6，成本僅 1/20。
    API: https://api.minimax.io/v1/text/chatcompletion_v2
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = (api_key or MINIMAX_API_KEY).strip()
        self.model = model or MINIMAX_MODEL
        self.api_url = MINIMAX_API_URL
        self.timeout = MINIMAX_TIMEOUT

    async def chat(self, messages: list) -> str:
        if not self.api_key:
            return _error_json("未設定 MINIMAX_API_KEY，請在 .env 設定。")

        # 轉換 messages 為 MiniMax 格式（相容 OpenAI 風格）
        mm_messages = []
        for m in messages:
            role = m.get("role", "")
            content = (m.get("content") or "").strip()
            if role == "system":
                mm_messages.append({"role": "system", "content": content})
            elif role == "user":
                mm_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                mm_messages.append({"role": "assistant", "content": content})
        if not mm_messages:
            return _error_json("MiniMax：無有效對話內容。")

        payload = {
            "model": self.model,
            "messages": mm_messages,
            "stream": False,
            "temperature": 0.3,
            "top_p": 0.95,
            "max_completion_tokens": 8192,
        }

        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                # 檢查 API 層級錯誤
                base_resp = result.get("base_resp", {})
                if base_resp.get("status_code", 0) != 0:
                    return _error_json(f"MiniMax API 錯誤: {base_resp.get('status_msg', 'unknown')}")
                # 提取回應文字
                choices = result.get("choices", [])
                if choices:
                    text = (choices[0].get("message") or {}).get("content", "").strip()
                    return text or _error_json("MiniMax 未回傳文字。")
                return _error_json("MiniMax 未回傳 choices。")
        except asyncio.TimeoutError:
            return _error_json(f"MiniMax API 逾時（{self.timeout} 秒）。")
        except Exception as e:
            return _error_json(f"MiniMax API 錯誤: {e}")


DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_TIMEOUT = float(os.environ.get("DEEPSEEK_TIMEOUT", "120"))


class DeepSeekService(BaseAIService):
    """
    DeepSeek 滿血版 — 開源推理模型（671B MoE, 37B active）。
    支援超長上下文（200K），推理能力強大。
    """
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.model = model or DEEPSEEK_MODEL
        self.timeout = DEEPSEEK_TIMEOUT

    async def chat(self, messages: list) -> str:
        if not self.api_key:
            return _error_json("未設定 DEEPSEEK_API_KEY，請在 .env 設定。")

        import httpx
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
                r.raise_for_status()
                data = r.json()
                content = data["choices"][0]["message"]["content"]
                
                # 用量追蹤
                if USAGE_TRACKING:
                    input_tokens = sum(len(str(m)) for m in messages)
                    output_tokens = len(str(content))
                    track_api_call("deepseek", self.model, input_tokens, output_tokens)
                
                return json.dumps({"done": True, "result": content}, ensure_ascii=False)
        except Exception as e:
            return _error_json(f"DeepSeek API 錯誤: {e}")


class SmartAIService(BaseAIService):
    """
    智慧路由調度引擎 — 雙 GPU 本地優先架構。

    核心設計理念（2026-02 升級：RTX 5070 Ti 16GB + RTX 4060 Ti 8GB）：
    ┌──────────────────────────────────────────────┐
    │  🏠 Ollama qwen3:32b = 軍師（大腦）本地！      │
    │    → 思考、分析、規劃、方向建議、專業判斷       │
    │    → 32B Q4 全 GPU 25-30 tok/s 接近 GPT-4     │
    │                                                │
    │  🏠 Ollama qwen3:8b = 士兵（執行）              │
    │    → 程式碼生成、文字翻譯、格式轉換、重複任務   │
    │    → 60+ tok/s 極速回應                        │
    │                                                │
    │  ☁️ DeepSeek = 雲端備援（僅超長上下文）          │
    │    → 200K context、本地處理不了的複雜任務       │
    │                                                │
    │  🟣 Claude = 最後備援將軍                       │
    │    → 全部本地 + DeepSeek 都掛了才上             │
    └──────────────────────────────────────────────┘

    三種模式：
    - smart_route（推薦）：本地 32b 軍師 / 8b 士兵 / 雲端備援
    - local_first：省錢模式，全部本地
    - cloud_first：品質優先，全部雲端
    """

    # ── 任務分類關鍵字 ──

    # 🧠 思考型任務（交給 Gemini 軍師）
    _THINK_KEYWORDS = [
        "分析", "策略", "規劃", "建議", "方向", "評估", "判斷", "比較",
        "架構", "設計", "決策", "優缺點", "風險", "趨勢", "預測",
        "為什麼", "怎麼看", "如何選", "哪個好", "值不值",
        "analyze", "strategy", "plan", "suggest", "evaluate", "compare",
        "design", "architecture", "decision", "pros and cons", "recommend",
        "報告", "研究", "深入", "詳細", "完整", "全面",
    ]

    # ⚡ 執行型任務（交給 Ollama 士兵）
    _EXEC_KEYWORDS = [
        "寫", "生成", "產生", "翻譯", "轉換", "格式化", "修改", "改寫",
        "程式", "code", "function", "class", "html", "css", "json", "sql",
        "write", "generate", "create", "convert", "format", "translate",
        "template", "boilerplate", "snippet", "example",
        "摘要", "總結", "列出", "整理", "排版",
        "hello", "你好", "謝謝", "ok", "好的",
    ]

    # ── 本地健康探針設定 ──
    _HEALTH_CACHE_TTL = 30       # 健康狀態快取秒數
    _HEALTH_PROBE_TIMEOUT = 2.0  # 探針超時秒數

    def __init__(
        self,
        gemini_service: BaseAIService | None = None,
        ollama_service: BaseAIService | None = None,
        claude_service: BaseAIService | None = None,
        minimax_service: BaseAIService | None = None,
    ):
        self.gemini = gemini_service if gemini_service is not None else AIService()
        self.ollama = ollama_service if ollama_service is not None else OllamaService(model_name=OLLAMA_STRONG_MODEL)
        self.ollama_fast = OllamaService(model_name=OLLAMA_FAST_MODEL)
        self.ollama_reason = OllamaService(model_name=OLLAMA_REASON_MODEL)
        self.brain = OllamaService(model_name=OLLAMA_BRAIN_MODEL)  # 蒸餾專才
        self.claude = claude_service if claude_service is not None else ClaudeService()
        self.minimax = minimax_service if minimax_service is not None else MiniMaxService()
        self.llama_swap = LlamaSwapService()
        self.mode = AI_COST_MODE
        # TaskPlanner 精準指派引擎
        try:
            from ai_modules.task_planner import planner as _tp, PrePlanner as _pp
            self._task_planner = _tp
            self._pre_planner = _pp()
        except ImportError:
            self._task_planner = None
            self._pre_planner = None
        # 健康狀態快取：(is_healthy: bool, timestamp: float)
        self._ollama_health: tuple[bool, float] = (True, 0.0)
        self._llama_swap_health: tuple[bool, float] = (False, 0.0)
        self._consecutive_ollama_failures = 0
        # 用量計量：當前用戶 ID（由呼叫端設定）
        self._current_user_id: str = "anonymous"

    async def _check_ollama_health(self) -> bool:
        """
        輕量級 Ollama 健康探針：GET /api/tags（2s 超時）。
        結果快取 30 秒，避免每次請求都探測。
        連續失敗 3 次後標記為不健康，直到探針恢復。
        """
        cached_healthy, cached_ts = self._ollama_health
        if time.time() - cached_ts < self._HEALTH_CACHE_TTL:
            return cached_healthy

        try:
            import httpx
            base = OLLAMA_BASE_URL
            async with httpx.AsyncClient(timeout=self._HEALTH_PROBE_TIMEOUT) as client:
                r = await client.get(f"{base}/api/tags")
                healthy = r.status_code == 200
        except Exception:
            healthy = False

        self._ollama_health = (healthy, time.time())
        if healthy:
            if self._consecutive_ollama_failures > 0:
                print("🔄 Ollama 恢復正常！切回本地執行。")
            self._consecutive_ollama_failures = 0
        else:
            self._consecutive_ollama_failures += 1
            if self._consecutive_ollama_failures == 1:
                print("⚠️ Ollama 本地服務異常，自動切換至雲端。")
        return healthy

    def _classify_task(self, messages: list) -> str:
        """
        分類任務類型：think（思考/規劃）或 execute（執行/生成）。

        規則：
        1. 含思考關鍵字 → think（交給 Gemini 軍師）
        2. 含執行關鍵字 → execute（交給 Ollama 士兵）
        3. 短訊息（<30 字）→ execute（簡單對話，本地處理）
        4. 長訊息或多輪對話 → think（需要深度理解）
        5. 預設 → think（寧可用好的，不要用差的）
        """
        last_user = ""
        total_len = 0
        for m in messages:
            total_len += len(m.get("content") or "")
            if m.get("role") == "user":
                last_user = (m.get("content") or "").strip()

        lower = last_user.lower()

        # 計算思考/執行信號強度
        think_score = sum(1 for kw in self._THINK_KEYWORDS if kw in lower)
        exec_score = sum(1 for kw in self._EXEC_KEYWORDS if kw in lower)

        # 短訊息且無明確思考信號 → 執行（本地處理）
        if len(last_user) < 30 and think_score == 0:
            return "execute"

        # 明確思考信號較強 → 思考
        if think_score > exec_score:
            return "think"

        # 明確執行信號較強 → 執行
        if exec_score > think_score:
            return "execute"

        # 長文或多輪 → 需要深度理解 → 思考
        if len(last_user) > 300 or total_len > 2000:
            return "think"

        # 預設：交給軍師（品質優先）
        return "think"

    def _is_error_response(self, response: str) -> bool:
        """判斷回應是否為錯誤/空白。"""
        if not response or not response.strip():
            return True
        error_markers = ["Unknown action", "服務異常", "API 錯誤", "API 逾時", "未回傳文字"]
        return any(m in response for m in error_markers)

    async def _check_llama_swap_health(self) -> bool:
        """檢查 llama-swap 是否運行中（快取 60 秒）。"""
        cached_healthy, cached_ts = self._llama_swap_health
        if time.time() - cached_ts < 60:
            return cached_healthy
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(f"{LLAMA_SWAP_URL}/v1/models")
                healthy = r.status_code == 200
        except Exception:
            healthy = False
        self._llama_swap_health = (healthy, time.time())
        return healthy

    async def _call_with_fallback(self, messages: list, chain: list[str], task_label: str = "") -> str:
        """依序嘗試 chain 中的服務，本地異常時自動跳過切雲端。每次呼叫自動記錄用量。"""
        services = {"ollama": self.ollama, "ollama_fast": self.ollama_fast, "ollama_reason": self.ollama_reason, "brain": self.brain, "gemini": self.gemini, "claude": self.claude, "minimax": self.minimax, "llama_swap": self.llama_swap}
        labels = {"ollama": "🏠 軍師 Ollama 32b", "ollama_fast": "⚡ 士兵 Ollama fast", "ollama_reason": "🧠 推理 DeepSeek-R1 14b", "brain": "🧬 專才 Brain-v3", "gemini": "☁️ 軍師 Gemini", "claude": "🟣 備援 Claude", "minimax": "🔵 尖兵 MiniMax", "llama_swap": "🔄 備援 LlamaSwap"}
        model_names = {"ollama": OLLAMA_STRONG_MODEL, "ollama_fast": OLLAMA_FAST_MODEL, "ollama_reason": OLLAMA_REASON_MODEL, "brain": OLLAMA_BRAIN_MODEL, "gemini": GEMINI_MODEL, "claude": ANTHROPIC_MODEL, "minimax": MINIMAX_MODEL, "llama_swap": LLAMA_SWAP_MODEL}
        ollama_healthy = await self._check_ollama_health()
        # 估算輸入 token
        input_text = " ".join(m.get("content", "") for m in messages)
        try:
            from usage_metering import estimate_tokens, record_usage
            input_tokens = estimate_tokens(input_text)
        except Exception:
            input_tokens = 0
        last_error = ""
        for name in chain:
            svc = services.get(name)
            if svc is None:
                continue
            # 本地異常時跳過 Ollama（包含 fast），直接用雲端
            if name in ("ollama", "ollama_fast", "brain") and not ollama_healthy:
                print(f"🧠 智慧路由 [{self.mode}|{task_label}] ⏭️ 跳過 {name}（本地異常）")
                last_error = f"{name}: 本地服務不可用"
                continue
            # llama-swap 未運行時跳過
            if name == "llama_swap":
                if not await self._check_llama_swap_health():
                    continue
            # 未設定 API Key 時跳過 MiniMax
            if name == "minimax" and not MINIMAX_API_KEY:
                continue
            t0 = time.time()
            try:
                print(f"🧠 智慧路由 [{self.mode}|{task_label}] → {labels.get(name, name)}")
                response = await svc.chat(messages)
                duration_ms = int((time.time() - t0) * 1000)
                if not self._is_error_response(response):
                    # Ollama 實際呼叫成功 → 更新健康狀態
                    if name in ("ollama", "ollama_fast"):
                        self._ollama_health = (True, time.time())
                        self._consecutive_ollama_failures = 0
                    # 記錄成功用量
                    try:
                        out_tokens = estimate_tokens(response)
                        record_usage(
                            provider=name, model=model_names.get(name, name),
                            input_tokens=input_tokens, output_tokens=out_tokens,
                            duration_ms=duration_ms, success=True,
                            user_id=self._current_user_id, task_type=task_label or "chat",
                        )
                    except Exception:
                        pass
                    return response
                last_error = f"{name}: 回應品質不足"
                # 記錄品質不足
                try:
                    record_usage(
                        provider=name, model=model_names.get(name, name),
                        input_tokens=input_tokens, output_tokens=0,
                        duration_ms=duration_ms, success=False, error_msg="回應品質不足",
                        user_id=self._current_user_id, task_type=task_label or "chat",
                    )
                except Exception:
                    pass
                # Ollama 回應異常 → 記錄失敗
                if name in ("ollama", "ollama_fast", "brain"):
                    self._consecutive_ollama_failures += 1
            except Exception as e:
                duration_ms = int((time.time() - t0) * 1000)
                last_error = f"{name}: {e}"
                # 記錄異常
                try:
                    record_usage(
                        provider=name, model=model_names.get(name, name),
                        input_tokens=input_tokens, output_tokens=0,
                        duration_ms=duration_ms, success=False, error_msg=str(e)[:200],
                        user_id=self._current_user_id, task_type=task_label or "chat",
                    )
                except Exception:
                    pass
                if name in ("ollama", "ollama_fast", "brain"):
                    self._consecutive_ollama_failures += 1
                    # 即時標記不健康，下次不再嘗試（直到快取過期重新探測）
                    self._ollama_health = (False, time.time())
                    print(f"⚠️ Ollama 呼叫失敗: {e}，切換雲端")
                continue
        return _error_json(f"所有 AI 服務均失敗: {last_error}")

    async def smart_request(self, prompt: str, task_type: str = "conversation") -> str:
        """智慧調度入口：prompt 為單一使用者輸入。"""
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages)

    async def chat(self, messages: list) -> str:
        """
        主調度方法 — TaskPlanner 精準指派 + Pre-Planning + QualityGate。

        升級架構（2026-02-28）：
          L0 greeting  → 4b 秒回（0 成本）
          L1 quick     → 4b/8b 快速回應
          L2 domain    → brain-v3 專才 或 32b + RAG
          L3 complex   → 32b + 品質檢查 + 重試
          L4 expert    → 32b + RAG + 品檢 + 雲端覆核

        向後相容：無 TaskPlanner 時退回舊邏輯（think/execute 二分法）。
        """
        # ── TaskPlanner 精準指派 ──
        if self._task_planner is not None:
            return await self._chat_with_planner(messages)

        # ── 向後相容：舊邏輯 ──
        task = self._classify_task(messages)
        thinking_mode = os.environ.get("THINKING_PROTOCOL", "auto")
        if thinking_mode != "off" and task == "think":
            try:
                from ai_modules.thinking_protocol import inject_thinking
                messages = inject_thinking(messages, mode="lite")
            except ImportError:
                pass

        if self.mode == "cloud_first":
            if thinking_mode != "off" and task == "think":
                try:
                    from ai_modules.thinking_protocol import inject_thinking
                    messages = inject_thinking(messages, mode="full")
                except ImportError:
                    pass
            return await self._call_with_fallback(messages, ["deepseek", "minimax", "claude", "ollama"], task)

        if self.mode == "local_only":
            if task == "think":
                return await self._call_with_fallback(messages, ["ollama", "ollama_reason", "llama_swap", "ollama_fast"], "think")
            else:
                return await self._call_with_fallback(messages, ["ollama_fast", "ollama", "llama_swap"], "execute")

        if self.mode == "local_first":
            if task == "think":
                return await self._call_with_fallback(messages, ["ollama", "ollama_reason", "llama_swap", "deepseek", "claude"], "think")
            else:
                return await self._call_with_fallback(messages, ["ollama_fast", "ollama", "llama_swap", "deepseek"], "execute")

        if task == "think":
            return await self._call_with_fallback(messages, ["ollama", "llama_swap", "deepseek", "minimax", "claude"], "think")
        else:
            return await self._call_with_fallback(messages, ["ollama_fast", "ollama", "llama_swap", "minimax", "deepseek"], "execute")

    async def _chat_with_planner(self, messages: list) -> str:
        """
        TaskPlanner 驅動的精準調度。

        流程：
        1. TaskPlanner.plan() — 分類 + 產出 TaskPlan
        2. PrePlanner.prepare_messages() — SOP/RAG/格式注入
        3. _call_with_fallback() — 按 model_chain 執行
        4. QualityGate — 品質檢查 + 自動升級
        5. log_task() — 記錄到訓練日誌
        """
        t0 = time.time()
        plan = self._task_planner.plan(messages)

        # 取出最後一條 user 訊息（用於品檢和日誌）
        last_user = ""
        for m in messages:
            if m.get("role") == "user":
                last_user = (m.get("content") or "").strip()

        print(f"📋 TaskPlanner: {plan.level} {plan.label} | domain={plan.domain} | chain={plan.model_chain}")

        # ── local_only 模式：過濾掉雲端模型 ──
        chain = list(plan.model_chain)
        cloud_models = {"deepseek", "gemini", "claude", "minimax"}
        if self.mode == "local_only":
            chain = [m for m in chain if m not in cloud_models]
            if not chain:
                chain = ["ollama_fast", "ollama", "brain", "llama_swap"]
        elif self.mode == "cloud_first":
            # 雲端優先：把雲端模型排前面
            local = [m for m in chain if m not in cloud_models]
            cloud = [m for m in chain if m in cloud_models]
            if not cloud:
                cloud = ["deepseek", "minimax", "claude"]
            chain = cloud + local

        # ── Pre-Planning：準備 messages ──
        prepared = self._pre_planner.prepare_messages(plan, messages) if self._pre_planner else messages

        # ── 執行 ──
        response = await self._call_with_fallback(prepared, chain, f"{plan.level}_{plan.label}")
        duration_ms = int((time.time() - t0) * 1000)

        # ── QualityGate 品質檢查 ──
        if plan.quality_gate and not self._is_error_response(response):
            try:
                from ai_modules.ai_sop import QualityGate
                qg = QualityGate(min_score=plan.quality_min_score)
                result = qg.check(last_user, response)
                if not result.get("pass", True):
                    issues = result.get("issues", [])
                    print(f"⚠️ QualityGate 不通過: {issues} (score={result.get('score', 0)})")
                    # 自動升級：用更強的模型重試
                    if plan.escalation:
                        escalation_chain = ["deepseek", "minimax", "claude"]
                        # local_only 模式不升級到雲端
                        if self.mode != "local_only":
                            print(f"🔄 品質升級: 交給 {escalation_chain}")
                            response2 = await self._call_with_fallback(prepared, escalation_chain, f"{plan.level}_escalated")
                            if not self._is_error_response(response2):
                                response = response2
                    elif plan.max_retries > 0:
                        # 同模型重試一次
                        print(f"🔄 重試中...")
                        response2 = await self._call_with_fallback(prepared, chain[:2], f"{plan.level}_retry")
                        if not self._is_error_response(response2):
                            result2 = qg.check(last_user, response2)
                            if result2.get("score", 0) > result.get("score", 0):
                                response = response2
            except ImportError:
                pass

        # ── 記錄到訓練日誌 ──
        try:
            self._task_planner.log_task(plan, last_user, response, chain[0], duration_ms)
        except Exception:
            pass

        return response


class LlamaSwapService(BaseAIService):
    """
    llama-swap 後端：OpenAI 相容 API，多模型熱切換。
    當 Ollama 不可用時作為本地 fallback，port 10005。
    """

    def __init__(self, model_name: str | None = None):
        self.base_url = LLAMA_SWAP_URL
        self.model_name = model_name or LLAMA_SWAP_MODEL
        self.timeout = LLAMA_SWAP_TIMEOUT

    async def chat(self, messages: list) -> str:
        import httpx
        ollama_messages = _react_to_ollama_messages(list(messages))
        if not ollama_messages:
            return _error_json("LlamaSwap：無有效對話內容。")
        body = {
            "model": self.model_name,
            "messages": ollama_messages,
            "max_tokens": 4096,
            "stream": False,
            "temperature": 0.3,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(f"{self.base_url}/v1/chat/completions", json=body)
                r.raise_for_status()
                data = r.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content and content.strip():
                    return content.strip()
                return _error_json("LlamaSwap 回應為空")
        except Exception as e:
            return _error_json(f"LlamaSwap 服務異常: {e}")


class AIServiceFactory:
    """服務工廠：一鍵切換雲端引擎；預設智慧路由。"""

    @staticmethod
    def create(provider: str) -> BaseAIService:
        if provider == "gemini":
            return GeminiService()
        if provider == "ollama":
            return OllamaService()
        if provider == "claude":
            return ClaudeService()
        if provider == "minimax":
            return MiniMaxService()
        if provider == "deepseek":
            return DeepSeekService()
        if provider == "llama_swap":
            return LlamaSwapService()
        if provider == "smart":
            return SmartAIService()
        if provider == "aliyun":
            return AliyunService()
        if provider == "tencent":
            return TencentService()
        if provider == "litellm":
            return LiteLLMService()
        # 預設：根據 AI_COST_MODE 決定
        if AI_COST_MODE == "smart_route":
            return SmartAIService()
        return OllamaService()

    get_service = create  # 相容舊用法

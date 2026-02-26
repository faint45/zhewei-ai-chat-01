# -*- coding: utf-8 -*-
"""
築未科技 — 代碼模擬器：AI 集成服務
直接接入現有 ai_modules/ai_providers.py 統一 AI 系統
流式回應保留 httpx async streaming（Ollama / Groq / Gemini / DeepSeek 等）
"""
import os
import sys
import json
import asyncio
import httpx
from pathlib import Path
from typing import Dict, Any, Optional, AsyncGenerator

# 載入 .env
try:
    from dotenv import load_dotenv
    ROOT = Path(__file__).resolve().parent.parent
    load_dotenv(ROOT / ".env")
    ue = Path(os.path.expanduser("~/.openclaw/.env"))
    if ue.is_file():
        load_dotenv(ue, override=False)
except ImportError:
    pass

# 將專案根目錄加入 sys.path，以便 import ai_modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 接入現有 AI 系統
try:
    from ai_modules.ai_providers import ask_sync, get_available, ask_ensemble
    AI_SYSTEM_AVAILABLE = True
    print("[AICodeService] ✅ 已接入 ai_modules/ai_providers.py 統一 AI 系統")
except ImportError as e:
    AI_SYSTEM_AVAILABLE = False
    print(f"[AICodeService] ⚠️ 無法載入 ai_providers: {e}，使用內建 fallback")

TIMEOUT = 60

# ── Provider configs ────────────────────────────────────
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_CODER_MODEL") or os.environ.get("OLLAMA_MODEL", "qwen3:32b")

# 流式 API 端點配置
STREAM_CONFIGS = {
    "ollama": {
        "url": lambda: f"{OLLAMA_URL}/api/chat",
        "headers": lambda: {},
        "body": lambda msgs, m: {"model": m or OLLAMA_MODEL, "messages": msgs, "stream": True},
        "parse": "ollama",
    },
    "groq": {
        "url": lambda: "https://api.groq.com/openai/v1/chat/completions",
        "headers": lambda: {"Authorization": f"Bearer {os.environ.get('GROQ_API_KEY', '')}"},
        "body": lambda msgs, m: {"model": m or "llama-3.3-70b-versatile", "messages": msgs, "stream": True},
        "parse": "openai",
        "key_env": "GROQ_API_KEY",
    },
    "gemini": {
        "url": lambda: f"https://generativelanguage.googleapis.com/v1beta/models/{os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash')}:streamGenerateContent?alt=sse&key={os.environ.get('GEMINI_API_KEY', '')}",
        "headers": lambda: {},
        "parse": "gemini",
        "key_env": "GEMINI_API_KEY",
    },
    "deepseek": {
        "url": lambda: "https://api.deepseek.com/v1/chat/completions",
        "headers": lambda: {"Authorization": f"Bearer {os.environ.get('DEEPSEEK_API_KEY', '')}"},
        "body": lambda msgs, m: {"model": m or "deepseek-chat", "messages": msgs, "stream": True},
        "parse": "openai",
        "key_env": "DEEPSEEK_API_KEY",
    },
    "mistral": {
        "url": lambda: "https://api.mistral.ai/v1/chat/completions",
        "headers": lambda: {"Authorization": f"Bearer {os.environ.get('MISTRAL_API_KEY', '')}"},
        "body": lambda msgs, m: {"model": m or "mistral-small-latest", "messages": msgs, "stream": True},
        "parse": "openai",
        "key_env": "MISTRAL_API_KEY",
    },
    "openai": {
        "url": lambda: "https://api.openai.com/v1/chat/completions",
        "headers": lambda: {"Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}"},
        "body": lambda msgs, m: {"model": m or "gpt-4o-mini", "messages": msgs, "stream": True},
        "parse": "openai",
        "key_env": "OPENAI_API_KEY",
    },
    "claude": {
        "url": lambda: "https://api.anthropic.com/v1/messages",
        "headers": lambda: {"x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""), "anthropic-version": "2023-06-01"},
        "parse": "claude",
        "key_env": "ANTHROPIC_API_KEY",
    },
    "qwen": {
        "url": lambda: "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "headers": lambda: {"Authorization": f"Bearer {os.environ.get('DASHSCOPE_API_KEY', '')}"},
        "body": lambda msgs, m: {"model": m or "qwen-plus", "messages": msgs, "stream": True},
        "parse": "openai",
        "key_env": "DASHSCOPE_API_KEY",
    },
    "openrouter": {
        "url": lambda: "https://openrouter.ai/api/v1/chat/completions",
        "headers": lambda: {"Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY', '')}"},
        "body": lambda msgs, m: {"model": m or "deepseek/deepseek-chat-v3-0324:free", "messages": msgs, "stream": True},
        "parse": "openai",
        "key_env": "OPENROUTER_API_KEY",
    },
    "grok": {
        "url": lambda: "https://api.x.ai/v1/chat/completions",
        "headers": lambda: {"Authorization": f"Bearer {os.environ.get('XAI_API_KEY', '')}"},
        "body": lambda msgs, m: {"model": m or "grok-2-latest", "messages": msgs, "stream": True},
        "parse": "openai",
        "key_env": "XAI_API_KEY",
    },
}

# 流式降級順序（本地優先，節省成本）
STREAM_FALLBACK = ["ollama", "groq", "gemini", "deepseek", "mistral", "openrouter", "qwen", "openai", "claude", "grok"]


class AICodeService:
    """
    統一 AI 代碼服務
    - 非流式對話：直接用 ai_providers.ask_sync()（本地 Ollama 優先）
    - 流式對話：httpx async streaming（本地優先降級）
    - 代碼任務：啟用 use_coder_model（本地 qwen3:8b）
    """

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        self._ollama_available = None
        self._ollama_checked_at = 0  # 上次健康檢查時間戳

    async def close(self):
        await self.client.aclose()

    # ── 本地優先：Ollama ────────────────────────────────
    async def _try_ollama_first(self, messages: list, model: str = "", use_coder: bool = False) -> Optional[Dict[str, Any]]:
        """嘗試用本地 Ollama 回應，成功返回結果，失敗返回 None"""
        import time
        # 30 秒內已確認離線則跳過
        if self._ollama_available is False and (time.time() - self._ollama_checked_at) < 30:
            return None
        # 代碼任務自動用 coder 模型
        if use_coder:
            m = model or os.environ.get("OLLAMA_CODER_MODEL", "qwen3:32b")
        else:
            m = model or OLLAMA_MODEL
        try:
            r = await self.client.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": m, "messages": messages, "stream": False},
                timeout=120,
            )
            if r.status_code == 200:
                content = r.json().get("message", {}).get("content", "")
                if content:
                    self._ollama_available = True
                    self._ollama_checked_at = time.time()
                    print(f"[AIChat] ✅ 本地 Ollama ({m}) 回應成功，零成本")
                    return {"content": content, "provider": f"Ollama({m})", "model": m}
        except Exception as e:
            self._ollama_available = False
            self._ollama_checked_at = time.time()
            print(f"[AIChat] ⚠️ 本地 Ollama 不可用: {e}")
        return None

    # ── Public API: 非流式對話 ──────────────────────────
    async def chat(self, messages: list, provider: str = "auto", model: str = "") -> Dict[str, Any]:
        """非流式對話 — 接入 ai_providers.ask_sync() 統一系統，失敗自動降級"""
        system_prompt, user_prompt = self._extract_prompts(messages)
        print(f"[AIChat] provider={provider}, AI_SYSTEM={AI_SYSTEM_AVAILABLE}, prompt_len={len(user_prompt)}")

        # auto 模式：優先用 ai_providers 統一系統（自帶 10 AI 降級）
        if AI_SYSTEM_AVAILABLE and provider == "auto":
            try:
                # 本地優先：先嘗試 Ollama，失敗再走 ask_sync 降級鏈
                ollama_result = await self._try_ollama_first(messages)
                if ollama_result:
                    return ollama_result

                result, used_provider = await asyncio.to_thread(
                    ask_sync, user_prompt,
                    system_prompt=system_prompt,
                    use_coder_model=True,
                )
                if result and "連線失敗" not in result and "預算已達上限" not in result:
                    print(f"[AIChat] ✅ ask_sync 成功 via {used_provider}")
                    return {"content": result, "provider": used_provider, "model": model}
                print(f"[AIChat] ⚠️ ask_sync 回傳失敗訊息，嘗試 httpx fallback")
            except Exception as e:
                print(f"[AIChat] ⚠️ ask_sync 異常: {e}，嘗試 httpx fallback")

        # auto 模式 fallback 或指定 provider：用 httpx 直接呼叫（帶降級鏈）
        if provider == "auto":
            chain = self._get_stream_chain()
            # 跳過 ollama（已在 _try_ollama_first 試過）
            chain = [p for p in chain if p != "ollama"]
            for p in chain:
                result = await self._chat_direct(messages, p, model)
                if "error" not in result:
                    return result
                print(f"[AIChat] {p} 失敗: {result.get('error', '')[:80]}")
            return {"error": "所有 AI 提供者均失敗", "provider": "none"}

        return await self._chat_direct(messages, provider, model)

    async def _chat_direct(self, messages: list, provider: str, model: str = "") -> Dict[str, Any]:
        """直接用 httpx 呼叫指定 provider"""
        cfg = STREAM_CONFIGS.get(provider)
        if not cfg:
            return {"error": f"未知提供者: {provider}", "provider": provider}
        key_env = cfg.get("key_env")
        if key_env and not os.environ.get(key_env, "").strip():
            return {"error": f"{key_env} 未設定", "provider": provider}
        try:
            parse_type = cfg["parse"]
            if parse_type == "gemini":
                return await self._chat_gemini_direct(messages, model)
            elif parse_type == "claude":
                return await self._chat_claude_direct(messages, model)
            elif parse_type == "ollama":
                # Ollama 用 /api/chat 格式
                result = await self._try_ollama_first(messages, model)
                return result or {"error": "Ollama 無回應", "provider": "ollama"}
            else:
                # OpenAI 相容格式（Groq/DeepSeek/Mistral/OpenAI/Qwen/OpenRouter/Grok）
                body_fn = cfg.get("body")
                if not body_fn:
                    return {"error": f"{provider} 不支持直接呼叫", "provider": provider}
                body = body_fn(messages, model)
                body["stream"] = False
                r = await self.client.post(cfg["url"](), headers=cfg["headers"](), json=body, timeout=120)
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                return {"content": content, "provider": provider, "model": model}
        except Exception as e:
            return {"error": str(e), "provider": provider}

    async def _chat_gemini_direct(self, messages: list, model: str = "") -> Dict[str, Any]:
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        m = model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        contents = []
        for msg in messages:
            role = "user" if msg["role"] in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        r = await self.client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}",
            json={"contents": contents},
        )
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return {"content": text, "provider": "Gemini", "model": m}

    async def _chat_claude_direct(self, messages: list, model: str = "") -> Dict[str, Any]:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        m = model or "claude-sonnet-4-20250514"
        system_msg, chat_msgs = "", []
        for msg in messages:
            if msg["role"] == "system":
                system_msg += msg["content"] + "\n"
            else:
                chat_msgs.append(msg)
        body = {"model": m, "max_tokens": 4096, "messages": chat_msgs}
        if system_msg:
            body["system"] = system_msg.strip()
        r = await self.client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            json=body,
        )
        r.raise_for_status()
        text = r.json()["content"][0]["text"]
        return {"content": text, "provider": "Claude", "model": m}

    # ── Public API: 流式對話 ────────────────────────────
    async def chat_stream(self, messages: list, provider: str = "auto", model: str = "") -> AsyncGenerator[str, None]:
        """流式對話 — 自動降級多個 provider"""
        if provider == "auto":
            chain = self._get_stream_chain()
        else:
            chain = [provider]

        for p in chain:
            try:
                got_data = False
                async for chunk in self._stream_provider(p, messages, model):
                    got_data = True
                    yield chunk
                if got_data:
                    return
            except Exception:
                continue
        yield json.dumps({"error": "所有 AI 提供者流式回應均失敗"})

    def _get_stream_chain(self) -> list:
        """取得流式降級鏈"""
        available = self.get_available_providers()
        return [p for p in STREAM_FALLBACK if p in available] or ["ollama"]

    async def _stream_provider(self, provider: str, messages: list, model: str = "") -> AsyncGenerator[str, None]:
        """統一流式呼叫"""
        cfg = STREAM_CONFIGS.get(provider)
        if not cfg:
            return
        key_env = cfg.get("key_env")
        if key_env and not os.environ.get(key_env, "").strip():
            return

        parse_type = cfg["parse"]

        if parse_type == "ollama":
            body = cfg["body"](messages, model)
            async with self.client.stream("POST", cfg["url"](), headers=cfg["headers"](), json=body, timeout=120) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            token = data.get("message", {}).get("content", "")
                            if token:
                                yield token
                        except json.JSONDecodeError:
                            pass

        elif parse_type == "gemini":
            m = model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
            key = os.environ.get("GEMINI_API_KEY", "")
            contents = []
            for msg in messages:
                role = "user" if msg["role"] in ("user", "system") else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:streamGenerateContent?alt=sse&key={key}"
            async with self.client.stream("POST", url, json={"contents": contents}) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if text:
                                yield text
                        except (json.JSONDecodeError, IndexError, KeyError):
                            pass

        elif parse_type == "claude":
            key = os.environ.get("ANTHROPIC_API_KEY", "")
            m = model or "claude-sonnet-4-20250514"
            system_msg, chat_msgs = "", []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg += msg["content"] + "\n"
                else:
                    chat_msgs.append(msg)
            body = {"model": m, "max_tokens": 4096, "messages": chat_msgs, "stream": True}
            if system_msg:
                body["system"] = system_msg.strip()
            async with self.client.stream(
                "POST", "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                json=body,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "content_block_delta":
                                text = data.get("delta", {}).get("text", "")
                                if text:
                                    yield text
                        except (json.JSONDecodeError, KeyError):
                            pass

        elif parse_type == "openai":
            body = cfg["body"](messages, model)
            async with self.client.stream("POST", cfg["url"](), headers=cfg["headers"](), json=body) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line.strip() != "data: [DONE]":
                        try:
                            data = json.loads(line[6:])
                            delta = data["choices"][0].get("delta", {}).get("content", "")
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, IndexError, KeyError):
                            pass

    # ── 代碼專用 API ────────────────────────────────────
    async def analyze_code(self, code: str, language: str, provider: str = "auto") -> Dict[str, Any]:
        """代碼分析（自動使用 coder 模型）"""
        prompt = f"""Analyze the following {language} code. Provide:
1. A brief summary of what it does
2. Potential issues or bugs
3. Performance suggestions
4. Security concerns (if any)
5. Code quality rating (1-10)

```{language}
{code}
```

Respond in a structured format."""
        return await self._code_task([{"role": "user", "content": prompt}], provider)

    async def optimize_code(self, code: str, language: str, instructions: str = "", provider: str = "auto") -> Dict[str, Any]:
        """代碼優化（自動使用 coder 模型）"""
        prompt = f"""Optimize the following {language} code.
{f'Additional instructions: {instructions}' if instructions else ''}

```{language}
{code}
```

Return ONLY the optimized code wrapped in a code block. Add brief comments explaining major changes."""
        return await self._code_task([{"role": "user", "content": prompt}], provider)

    async def fix_code(self, code: str, language: str, error: str = "", provider: str = "auto") -> Dict[str, Any]:
        """代碼修復（自動使用 coder 模型）"""
        prompt = f"""Fix the following {language} code.
{f'Error message: {error}' if error else 'Find and fix any bugs.'}

```{language}
{code}
```

Return the fixed code in a code block, followed by a brief explanation of what was wrong."""
        return await self._code_task([{"role": "user", "content": prompt}], provider)

    async def generate_code(self, description: str, language: str = "html", provider: str = "auto") -> Dict[str, Any]:
        """根據描述生成代碼（自動使用 coder 模型）"""
        prompt = f"""Generate {language} code based on this description:
{description}

Requirements:
- Write clean, modern, well-structured code
- Include necessary imports/dependencies
- Add brief comments for complex logic
- If it's a web page, make it visually appealing with modern CSS

Return the complete code in a code block."""
        return await self._code_task([{"role": "user", "content": prompt}], provider)

    async def _code_task(self, messages: list, provider: str = "auto") -> Dict[str, Any]:
        """代碼專用任務 — 本地優先用 coder 模型"""
        if provider == "auto":
            result = await self._try_ollama_first(messages, use_coder=True)
            if result:
                return result
        return await self.chat(messages, provider)

    # ── 工具方法 ────────────────────────────────────────
    def get_available_providers(self) -> list:
        """返回可用的 AI 提供者列表（優先用 ai_providers 系統）"""
        if AI_SYSTEM_AVAILABLE:
            try:
                names = get_available()
                name_map = {
                    "Groq": "groq", "Ollama": "ollama", "Gemini": "gemini",
                    "OpenRouter": "openrouter", "Grok": "grok", "DeepSeek": "deepseek",
                    "Mistral": "mistral", "混元": "hunyuan", "豆包": "doubao", "千尋": "qwen",
                }
                return [name_map.get(n, n.lower()) for n in names]
            except Exception:
                pass
        # fallback: 自行檢查
        checks = {
            "ollama": True,
            "gemini": bool(os.environ.get("GEMINI_API_KEY", "").strip()),
            "groq": bool(os.environ.get("GROQ_API_KEY", "").strip()),
            "deepseek": bool(os.environ.get("DEEPSEEK_API_KEY", "").strip()),
            "openai": bool(os.environ.get("OPENAI_API_KEY", "").strip()),
            "claude": bool(os.environ.get("ANTHROPIC_API_KEY", "").strip()),
            "mistral": bool(os.environ.get("MISTRAL_API_KEY", "").strip()),
            "qwen": bool(os.environ.get("DASHSCOPE_API_KEY", "").strip()),
            "openrouter": bool(os.environ.get("OPENROUTER_API_KEY", "").strip()),
            "grok": bool(os.environ.get("XAI_API_KEY", "").strip()),
        }
        return [k for k, v in checks.items() if v]

    @staticmethod
    def _extract_prompts(messages: list) -> tuple:
        """從 messages 提取 system_prompt 和 user_prompt"""
        system_parts = []
        user_parts = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            elif msg["role"] == "user":
                user_parts.append(msg["content"])
            elif msg["role"] == "assistant":
                user_parts.append(f"[AI 之前回覆] {msg['content']}")
        return "\n".join(system_parts), "\n".join(user_parts)

<<<<<<< HEAD
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
=======
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技大腦 - AI 服務模塊
提供與 OpenAI GPT 的連接
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from openai import AsyncOpenAI
from config_ai import AIConfig
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

class AIService:
    """AI 服務類 - 管理與 OpenAI 的連接"""
    
    def __init__(self, config: AIConfig = None):
        self.config = config or AIConfig.load_from_env()
        self.client: Optional[AsyncOpenAI] = None
        self.conversation_history: List[dict] = []
        self.cost_tracking: float = 0.0
        
        if AIConfig.validate(self.config):
            try:
                if self.config.MODEL_TYPE.value == "demo":
                    logger.info("🔄 使用演示模式")
                    return
                
                self.client = AsyncOpenAI(
                    api_key=self.config.get_api_key(),
                    base_url=self.config.get_api_base()
                )
                
                logger.info("✓ AI 服務初始化成功")
                logger.info(f"  類型: {self.config.MODEL_TYPE.value}")
                logger.info(f"  模型: {self.config.get_model_name()}")
                logger.info(f"  API: {self.config.get_api_base()}")
                
            except Exception as e:
                logger.error(f"✗ AI 服務初始化失敗: {e}")
                logger.info("🔄 切換到演示模式")
    
    async def generate_response(self, message: str, session_id: str = None) -> str:
        """生成 AI 回應"""
        try:
            # 如果是演示模式，使用基礎回應
            if self.config.MODEL_TYPE.value == "demo" or not self.client:
                return await self._demo_response(message)
            
            # 構建對話上下文
            messages = self._build_messages(message, session_id)
            
            # 調用 AI API
            logger.info(f"正在調用 {self.config.MODEL_TYPE.value} 模型處理消息: {message[:50]}...")
            
            response = await self.client.chat.completions.create(
                model=self.config.get_model_name(),
                messages=messages,
                max_tokens=self.config.MAX_TOKENS,
                temperature=self.config.TEMPERATURE,
                top_p=self.config.TOP_P
            )
            
            # 提取回應
            assistant_message = response.choices[0].message.content
            
            # 追蹤成本（僅適用於 OpenAI）
            if self.config.MODEL_TYPE.value == "openai" and self.config.ENABLE_COST_TRACKING:
                if hasattr(response, 'usage') and response.usage:
                    tokens_used = response.usage.total_tokens
                    self.cost_tracking += self._calculate_cost(tokens_used)
                    logger.info(f"Token 使用量: {tokens_used}, 累計成本: ${self.cost_tracking:.4f}")
            
            # 保存到對話歷史
            self._update_history(message, assistant_message, session_id)
            
            return assistant_message
            
        except Exception as e:
            logger.error(f"AI 生成回應失敗: {e}")
            # 如果 API 調用失敗，切換到演示模式
            return await self._demo_response(message)
    
    def _build_messages(self, user_message: str, session_id: str = None) -> List[dict]:
        """構建帶有上下文的對話消息列表"""
        # 系統提示詞 - 定義築未科技大腦的角色
        system_prompt = f"""你是築未科技大腦，一個智慧、專業的電腦代理人。

你的角色和任務：
• 提供智能、友好的對話服務
• 回答用戶關於時間、系統狀態、一般知識的問題
• 協助用戶執行各種任務
• 維護專業、有禮貌的語氣

回答風格：
• 使用台灣繁體中文
• 語氣友好、專業
• 回應簡潔明了
• 適時使用表情符號讓對話更生動

當前時間: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加對話歷史
        if session_id and len(self.conversation_history) > 0:
            recent_history = self.conversation_history[-self.config.CONTEXT_MESSAGES:]
            messages.extend(recent_history)
        
        # 添加當前用戶消息
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def _update_history(self, user_message: str, assistant_message: str, session_id: str):
        """更新對話歷史"""
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # 限制歷史記錄長度（限制 tokens 使用量）
        max_history = self.config.CONTEXT_MESSAGES * 2  # 用戶+助手消息
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
    
    def _calculate_cost(self, tokens: int) -> float:
        """計算 API 成本（估算）"""
        # GPT-4o-mini 定價：$0.15/1M input tokens, $0.60/1M output tokens
        # 簡化計算：平均 $0.375/1M tokens
        cost_per_1m_tokens = 0.375
        return (tokens / 1_000_000) * cost_per_1m_tokens
    
    async def _demo_response(self, message: str) -> str:
        """演示模式回應"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['你好', 'hello', 'hi', '嗨']):
            return f"您好！我是築未科技大腦。\n\n" \
                   f"🤖 當前模式: {self.config.MODEL_TYPE.value.upper()}\n" \
                   f"📋 可用功能：\n" \
                   f"• 智能對話\n" \
                   f"• 系統監控\n" \
                   f"• 文件管理\n" \
                   f"\n💡 提示：可以設置環境變量切換到 Ollama 或 OpenAI 模式\n" \
                   f"有什麼可以幫您的嗎？"
        
        elif '時間' in message_lower or 'date' in message_lower:
            from datetime import datetime
            return f"現在時間是：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}"
        
        elif '狀態' in message_lower or 'status' in message_lower:
            return f"🤖 築未科技大腦狀態：\n" \
                   f"• 模式: {self.config.MODEL_TYPE.value.upper()}\n" \
                   f"• 模型: {self.config.get_model_name()}\n" \
                   f"• 對話歷史: {len(self.conversation_history)} 條\n" \
                   f"• 系統運行正常"
        
        elif any(word in message_lower for word in ['ollama', '本地模型', 'local']):
            return "💡 要使用 Ollama 本地模型：\n" \
                   "1. 安裝 Ollama: https://ollama.ai/\n" \
                   "2. 拉取模型: `ollama pull llama3.1`\n" \
                   "3. 設置環境變量: `AI_MODEL_TYPE=ollama`\n" \
                   "4. 重啟服務即可使用本地 AI"
        
        else:
            return f"我收到了您的訊息：「{message}」\n\n" \
                   f"🤖 築未科技大腦正在為您服務。\n" \
                   f"💡 當前使用 {self.config.MODEL_TYPE.value} 模式\n" \
                   f"📋 可以詢問我：\n" \
                   f"• 系統狀態\n" \
                   f"• 當前時間\n" \
                   f"• 如何連接 Ollama\n" \
                   f"• 其他問題"
    
    def get_usage_stats(self) -> dict:
        """獲取使用統計"""
        return {
            "total_messages": len(self.conversation_history) // 2,
            "current_cost": round(self.cost_tracking, 4),
            "model": self.config.get_model_name(),
            "model_type": self.config.MODEL_TYPE.value,
            "context_messages": len(self.conversation_history)
        }
    
    def clear_history(self):
        """清除對話歷史"""
        self.conversation_history = []
        logger.info("對話歷史已清除")

# FastAPI 应用
app = FastAPI()

# 允许跨域请求（可选）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 AI 服务
ai_service = AIService()

@app.get("/chat")
async def chat(message: str):
    try:
        response = await ai_service.generate_response(message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
>>>>>>> bd6537def53debaba0c16f279817e4a317eed98c

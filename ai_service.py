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

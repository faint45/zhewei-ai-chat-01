#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技大腦 - 遠端對話服務器
作為電腦代理人的後端服務
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from ai_service import AIService
from config_ai import AIConfig, ai_config
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 創建 FastAPI 應用
app = FastAPI(
    title="築未科技大腦 API",
    description="遠端對話服務 - 電腦代理人系統",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生產環境中應該限制特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 數據模型
class Message(BaseModel):
    role: str  # "user" 或 "assistant"
    content: str
    timestamp: str

class ChatRequest(BaseModel):
    message: str
    session_id: str = None

class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str
    timestamp: str
    session_id: str = None

# 全局變量
active_connections: List[WebSocket] = []
chat_history: Dict[str, List[Message]] = {}

class BrainAgent:
    """築未科技大腦代理人類"""
    
    def __init__(self):
        self.name = "築未科技大腦"
        self.capabilities = [
            "遠端對話",
            "系統監控",
            "文件管理",
            "任務執行"
        ]
    
    async def process_message(self, message: str, session_id: str = None) -> str:
        """處理用戶消息並生成回應"""
        try:
            # 這裡可以連接到您實際的 AI 模型或系統
            response = await self._generate_response(message)
            
            # 保存對話歷史
            if session_id not in chat_history:
                chat_history[session_id] = []
            
            chat_history[session_id].append(Message(
                role="user",
                content=message,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            
            chat_history[session_id].append(Message(
                role="assistant",
                content=response,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            
            # 限制歷史記錄數量
            if len(chat_history[session_id]) > 100:
                chat_history[session_id] = chat_history[session_id][-100:]
            
            return response
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"處理消息時發生錯誤:\n{error_detail}")
            return f"詳細錯誤: {str(e)}"
    
    async def _generate_response(self, message: str) -> str:
        """生成回應（這裡可以連接到實際的 AI 模型）"""
        message_lower = message.lower()
        
        # 基於關鍵字的簡單回應邏輯
        if any(word in message_lower for word in ['你好', 'hello', 'hi', '嗨']):
            return f"您好！我是築未科技大腦，您的電腦代理人。我可以幫您：\n" \
                   f"• 遠端對話\n" \
                   f"• 系統監控\n" \
                   f"• 文件管理\n" \
                   f"• 執行任務\n\n" \
                   f"有什麼可以幫您的嗎？"
        
        elif '時間' in message_lower or 'date' in message_lower:
            return f"現在時間是：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}"
        
        elif '狀態' in message_lower or 'status' in message_lower:
            return f"系統狀態：\n" \
                   f"• 服務運行中\n" \
                   f"• 活躍連接：{len(active_connections)}\n" \
                   f"• 對話會話：{len(chat_history)}\n" \
                   f"• 當前時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        elif any(word in message_lower for word in ['再見', 'bye', 'byebye', '晚安']):
            return "再見！築未科技大腦隨時為您服務。祝您有美好的一天！"
        
        elif any(word in message_lower for word in ['謝謝', 'thank', '感謝']):
            return "不客氣！築未科技大腦很榮幸能為您服務。"
        
        else:
            # 默認回應 - 這裡可以連接到真實的 AI 模型
            return f"我收到了您的訊息：「{message}」\n\n" \
                   f"築未科技大腦正在學習如何更好地回應您的問題。\n" \
                   f"目前我處於演示模式，但可以連接到高級 AI 模型提供更智能的回應。\n\n" \
                   f"您可以詢問我：\n" \
                   f"• 系統狀態\n" \
                   f"• 當前時間\n" \
                   f"• 服務功能"

# 初始化大腦代理人
brain_agent = BrainAgent()

# 初始化 AI 服務
ai_service: Optional[AIService] = None
if AIConfig.validate(ai_config):
    ai_service = AIService(ai_config)
    if ai_service.config.MODEL_TYPE.value == "demo":
        logger.info("🔄 AI 服務使用演示模式")
    else:
        logger.info(f"🤖 AI 服務已啟用 - {ai_service.config.MODEL_TYPE.value} 模式")
else:
    logger.info("🔄 AI 服務未啟用，使用演示模式")

# WebSocket 連接管理
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 對話端點"""
    await websocket.accept()
    active_connections.append(websocket)
    session_id = str(id(websocket))
    
    logger.info(f"新連接建立: {session_id}")
    
    try:
        # 發送歡迎消息
        if ai_service:
            welcome_msg = await ai_service.generate_response("你好", session_id)
        else:
            welcome_msg = await brain_agent.process_message("你好", session_id)
        
        await websocket.send_json({
            "role": "assistant",
            "content": welcome_msg,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        while True:
            # 接收用戶消息
            data = await websocket.receive_json()
            message = data.get("message", "")
            
            if message:
                logger.info(f"收到消息: {message[:50]}...")
                
                # 處理消息並生成回應
                if ai_service:
                    response = await ai_service.generate_response(message, session_id)
                else:
                    response = await brain_agent.process_message(message, session_id)
                
                # 發送回應
                await websocket.send_json({
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
    
    except WebSocketDisconnect:
        logger.info(f"連接斷開: {session_id}")
        if session_id in chat_history:
            del chat_history[session_id]
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"WebSocket 錯誤:\n{error_detail}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)

# REST API 端點
@app.post("/api/chat")
async def chat_api(request: ChatRequest):
    """REST API 對話端點"""
    session_id = request.session_id or str(hash(request.message))
    response = await brain_agent.process_message(request.message, session_id)
    
    return ChatResponse(
        content=response,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        session_id=session_id
    )

@app.get("/api/status")
async def get_status():
    """獲取系統狀態"""
    ai_enabled = ai_service is not None
    ai_stats = ai_service.get_usage_stats() if ai_service else {}
    
    return {
        "system": "築未科技大腦",
        "status": "running",
        "active_connections": len(active_connections),
        "total_sessions": len(chat_history),
        "uptime": "running",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ai_enabled": ai_enabled,
        "ai_stats": ai_stats if ai_enabled else None
    }

@app.get("/api/history/{session_id}")
async def get_history(session_id: str):
    """獲取對話歷史"""
    if session_id not in chat_history:
        return {"messages": []}
    
    return {
        "session_id": session_id,
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp
            }
            for msg in chat_history[session_id]
        ]
    }

@app.get("/")
async def root():
    """根路徑 - 重定向到聊天界面"""
    try:
        with open("remote_brain.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>築未科技大腦 - 404</title>
        </head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>🔴 文件未找到</h1>
            <p>請確保 remote_brain.html 文件存在於當前目錄</p>
        </body>
        </html>
        """)

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    
    logger.info("啟動築未科技大腦服務器...")
    logger.info("WebSocket 端點: ws://localhost:8000/ws/chat")
    logger.info("REST API: http://localhost:8000/api/chat")
    
    uvicorn.run(
        app,
        host="0.0.0.0",  # 允許外部訪問
        port=8000,
        log_level="info"
    )

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技大腦 - 遠程控制本地AI模型服務器
實現類似OpenClaw的遠程指令功能
"""

import asyncio
import json
import logging
import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import subprocess
import threading
import queue
import shlex

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 創建 FastAPI 應用
app = FastAPI(
    title="築未科技遠程控制服務器",
    description="遠程控制本地AI模型執行指令",
    version="1.0.0"
)

# 配置 CORS - Phase 1.3 安全修復：使用白名單限制來源
CORS_ORIGINS_REMOTE = os.environ.get(
    "CORS_ORIGINS",
    "https://zhe-wei.net,https://brain.zhe-wei.net,http://localhost:3000,http://localhost:5100"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS_REMOTE,  # 白名單限制
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # 限制方法
    allow_headers=["Content-Type", "Authorization", "Accept"],  # 限制標頭
)

# 靜態文件目錄
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# 模板目錄
if os.path.exists("templates"):
    templates = Jinja2Templates(directory="templates")
else:
    templates = None

# 指令執行隊列
task_queue = queue.Queue()
result_queue = queue.Queue()

# 遠程指令模型
class RemoteCommand(BaseModel):
    command: str
    parameters: Dict[str, Any] = {}
    priority: int = 1

# 統一API請求模型
class UnifiedExecuteRequest(BaseModel):
    source: str  # wechat, telegram, discord, web
    user_id: str  # 用戶標識
    command: str  # 原始命令
    parameters: Dict[str, Any] = {}
    context_id: Optional[str] = None  # 上下文ID（跨平台連續性）

# 統一API響應模型
class UnifiedExecuteResponse(BaseModel):
    request_id: str
    status: str  # success, error
    result: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    context_id: Optional[str] = None
    timestamp: str

class CommandResult(BaseModel):
    command_id: str
    status: str  # pending, running, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None
    timestamp: str

# 本地AI模型控制類
class LocalAIController:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.available_models = []
        self.current_model = "llama3.1"
        
    def check_ollama_status(self):
        """檢查Ollama服務狀態"""
        try:
            import requests
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                self.available_models = [model["name"] for model in models]
                return True, f"Ollama服務正常，可用模型: {', '.join(self.available_models)}"
            else:
                return False, "Ollama服務未運行"
        except Exception as e:
            return False, f"無法連接到Ollama服務: {e}"
    
    def execute_ai_command(self, command: str, model: str = None) -> str:
        """執行AI指令"""
        try:
            import requests
            
            if model is None:
                model = self.current_model
            
            # 使用Ollama API生成回應
            payload = {
                "model": model,
                "prompt": command,
                "stream": False
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "指令執行完成")
            else:
                return f"AI指令執行失敗: {response.text}"
                
        except Exception as e:
            return f"執行AI指令時出錯: {e}"
    
    def execute_system_command(self, command: str) -> str:
        """
        執行系統指令（Phase 1.2 安全修復）
        使用 shlex.split() 安全解析，shell=False 防止注入
        """
        try:
            # 安全解析命令
            args = shlex.split(command)
            if not args:
                return "錯誤：命令格式無效"

            # 使用列表形式執行（shell=False）
            result = subprocess.run(
                args,
                shell=False,  # 關鍵安全修復
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return result.stdout if result.stdout else "指令執行成功"
            else:
                return f"指令執行失敗: {result.stderr}"

        except subprocess.TimeoutExpired:
            return "指令執行超時"
        except ValueError as e:
            return f"命令解析錯誤: {e}"
        except Exception as e:
            return f"執行系統指令時出錯: {e}"

# 初始化本地AI控制器
ai_controller = LocalAIController()

# 指令處理線程
def command_worker():
    """指令處理工作線程"""
    while True:
        try:
            # 從隊列獲取指令
            command_data = task_queue.get()
            command_id = command_data["command_id"]
            command = command_data["command"]
            
            logger.info(f"開始執行指令: {command_id}")
            
            # 執行指令
            if command.startswith("ai:"):
                # AI指令
                prompt = command[3:].strip()
                result = ai_controller.execute_ai_command(prompt)
            elif command.startswith("sys:"):
                # 系統指令
                sys_command = command[4:].strip()
                result = ai_controller.execute_system_command(sys_command)
            else:
                # 默認為AI指令
                result = ai_controller.execute_ai_command(command)
            
            # 將結果放入結果隊列
            result_queue.put({
                "command_id": command_id,
                "status": "completed",
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
            task_queue.task_done()
            
        except Exception as e:
            logger.error(f"指令執行錯誤: {e}")
            result_queue.put({
                "command_id": command_data.get("command_id", "unknown"),
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

# 啟動指令處理線程
worker_thread = threading.Thread(target=command_worker, daemon=True)
worker_thread.start()

# Auth Manager 認證管理
class AuthManager:
    """
    統一認證管理 - 防止非本人操作系統命令
    集中管理所有平台的用戶驗證
    """
    def __init__(self):
        self.authorized_users = set()
        self.user_tokens = {}  # user_id -> token
        self.token_expiry = {}  # token -> expiry_time
        
    def _generate_token(self, user_id: str) -> str:
        """生成用戶認證token"""
        token = secrets.token_urlsafe(32)
        self.user_tokens[user_id] = token
        self.token_expiry[token] = datetime.now() + timedelta(hours=24)
        return token
        
    def validate_token(self, token: str, user_id: str) -> bool:
        """驗證用戶token"""
        if token not in self.token_expiry:
            return False
            
        if datetime.now() > self.token_expiry[token]:
            # token過期
            del self.token_expiry[token]
            if user_id in self.user_tokens:
                del self.user_tokens[user_id]
            return False
            
        return self.user_tokens.get(user_id) == token
        
    def authorize_user(self, user_id: str) -> str:
        """授權用戶並返回token"""
        self.authorized_users.add(user_id)
        return self._generate_token(user_id)
        
    def is_user_authorized(self, user_id: str) -> bool:
        """檢查用戶是否已授權"""
        return user_id in self.authorized_users
        
    def revoke_authorization(self, user_id: str):
        """撤銷用戶授權"""
        if user_id in self.authorized_users:
            self.authorized_users.remove(user_id)
        if user_id in self.user_tokens:
            token = self.user_tokens[user_id]
            del self.user_tokens[user_id]
            if token in self.token_expiry:
                del self.token_expiry[token]

# Context Bridge 上下文橋接
class ContextBridge:
    """
    上下文橋接 - 實現跨平台對話連續性
    緩存各端的對話上下文，實現無縫切換
    """
    def __init__(self):
        self.user_contexts = {}  # user_id -> context_data
        self.context_histories = {}  # context_id -> conversation_history
        
    def _generate_context_id(self, user_id: str) -> str:
        """生成上下文ID"""
        return f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """獲取用戶上下文"""
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                "context_id": self._generate_context_id(user_id),
                "conversation_history": [],
                "last_activity": datetime.now(),
                "source_platforms": set()
            }
        return self.user_contexts[user_id]
        
    def add_conversation_turn(self, user_id: str, source: str, question: str, answer: str):
        """添加對話輪次"""
        context = self.get_user_context(user_id)
        context["conversation_history"].append({
            "source": source,
            "question": question,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        })
        context["last_activity"] = datetime.now()
        context["source_platforms"].add(source)
        
        # 保持對話歷史在合理範圍內（最近50輪）
        if len(context["conversation_history"]) > 50:
            context["conversation_history"] = context["conversation_history"][-50:]
            
    def get_conversation_context(self, user_id: str, max_turns: int = 10) -> str:
        """獲取對話上下文（用於AI模型）"""
        context = self.get_user_context(user_id)
        history = context["conversation_history"][-max_turns:]
        
        if not history:
            return ""
            
        context_text = "之前的對話上下文：\n"
        for turn in history:
            context_text += f"用戶({turn['source']}): {turn['question']}\n"
            context_text += f"AI: {turn['answer']}\n\n"
            
        return context_text
        
    def get_platform_continuity(self, user_id: str) -> List[str]:
        """獲取用戶使用的平台列表（用於跨平台連續性展示）"""
        context = self.get_user_context(user_id)
        return list(context["source_platforms"])
        
    def cleanup_old_contexts(self, max_age_hours: int = 24):
        """清理過期上下文"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_users = []
        
        for user_id, context in self.user_contexts.items():
            if context["last_activity"] < cutoff_time:
                expired_users.append(user_id)
                
        for user_id in expired_users:
            del self.user_contexts[user_id]

# 初始化上下文橋接
context_bridge = ContextBridge()

# Unified API 輔助函數
async def _authenticate_user(user_id: str, source: str) -> bool:
    """驗證用戶身份"""
    # 這裡可以根據實際需求實現更複雜的驗證邏輯
    # 目前簡單實現：只要用戶ID格式正確就通過
    if not user_id or len(user_id) < 3:
        return False
    
    # 自動授權新用戶
    if not auth_manager.is_user_authorized(user_id):
        token = auth_manager.authorize_user(user_id)
        logger.info(f"自動授權新用戶: {user_id} ({source})")
    
    return True

def _generate_context_id(user_id: str) -> str:
    """生成上下文ID"""
    return context_bridge._generate_context_id(user_id)

async def _execute_ai_with_context(command: str, user_id: str, context_id: str = "") -> str:
    """執行帶有上下文的AI指令"""
    # 獲取對話上下文
    context_text = context_bridge.get_conversation_context(user_id)
    
    # 構建帶有上下文的提示
    if context_text:
        full_prompt = f"{context_text}\n當前問題：{command}"
    else:
        full_prompt = command
    
    # 執行AI指令
    result = ai_controller.execute_ai_command(full_prompt)
    
    # 記錄對話輪次
    context_bridge.add_conversation_turn(user_id, "unified_api", command, result)
    
    return result

# 定期清理過期上下文
async def _cleanup_contexts():
    """定期清理過期上下文"""
    while True:
        await asyncio.sleep(3600)  # 每小時清理一次
        context_bridge.cleanup_old_contexts()
        logger.info("已清理過期對話上下文")

# 啟動定期清理任務（在事件循環中啟動）
async def start_cleanup_task():
    asyncio.create_task(_cleanup_contexts())

# 初始化認證管理器
auth_manager = AuthManager()

# WebSocket連接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# API路由
@app.get("/")
async def home(request: Request):
    """遠程控制主頁"""
    return templates.TemplateResponse("remote_control.html", {"request": request})

@app.get("/api/status")
async def get_system_status():
    """獲取系統狀態"""
    ollama_status, ollama_message = ai_controller.check_ollama_status()
    
    return {
        "service": "築未科技遠程控制服務器",
        "timestamp": datetime.now().isoformat(),
        "ollama_status": ollama_status,
        "ollama_message": ollama_message,
        "available_models": ai_controller.available_models,
        "current_model": ai_controller.current_model,
        "queue_size": task_queue.qsize(),
        "active_connections": len(manager.active_connections)
    }

@app.post("/api/command")
async def submit_command(command: RemoteCommand):
    """提交遠程指令"""
    command_id = secrets.token_urlsafe(8)
    
    # 將指令加入隊列
    task_queue.put({
        "command_id": command_id,
        "command": command.command,
        "parameters": command.parameters,
        "priority": command.priority
    })
    
    logger.info(f"收到遠程指令: {command_id} - {command.command}")
    
    return {
        "command_id": command_id,
        "status": "queued",
        "message": "指令已加入隊列",
        "queue_position": task_queue.qsize(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/command/{command_id}")
async def get_command_result(command_id: str):
    """獲取指令執行結果"""
    # 檢查結果隊列
    while not result_queue.empty():
        result = result_queue.get()
        if result["command_id"] == command_id:
            return result
        result_queue.put(result)  # 如果不是目標指令，放回隊列
    
    return {
        "command_id": command_id,
        "status": "pending",
        "message": "指令正在執行中",
        "timestamp": datetime.now().isoformat()
    }

# Unified API 統一接口
@app.post("/v1/execute")
async def unified_execute(request: UnifiedExecuteRequest):
    """
    統一執行接口 - 為所有平台提供統一的API入口
    
    支持來源：wechat, telegram, discord, web
    減少代碼重複，統一驗證和上下文管理
    """
    import time
    start_time = time.time()
    request_id = secrets.token_urlsafe(8)
    
    try:
        # 驗證用戶身份（Auth Manager）
        if not await _authenticate_user(request.user_id, request.source):
            raise HTTPException(status_code=403, detail="用戶驗證失敗")
        
        # 解析命令類型（ai: 或 sys: 前綴）
        if request.command.startswith("ai:"):
            command_type = "ai"
            actual_command = request.command[3:].strip()
        elif request.command.startswith("sys:"):
            command_type = "sys"
            actual_command = request.command[4:].strip()
        else:
            # 默認AI指令
            command_type = "ai"
            actual_command = request.command
        
        # 執行命令
        if command_type == "ai":
            # AI指令 - 支持上下文橋接
            result = await _execute_ai_with_context(
                actual_command, 
                request.user_id, 
                request.context_id
            )
            context_id = request.context_id or _generate_context_id(request.user_id)
        else:
            # 系統指令
            result = ai_controller.execute_system_command(actual_command)
            context_id = None
        
        execution_time = time.time() - start_time
        
        logger.info(f"Unified API執行成功: {request.source} - {request.user_id} - {command_type}")
        
        return UnifiedExecuteResponse(
            request_id=request_id,
            status="success",
            result=result,
            execution_time=execution_time,
            context_id=context_id,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Unified API執行失敗: {request.source} - {request.user_id} - {str(e)}")
        
        return UnifiedExecuteResponse(
            request_id=request_id,
            status="error",
            error=str(e),
            execution_time=execution_time,
            timestamp=datetime.now().isoformat()
        )

# WebSocket遠程控制
@app.websocket("/ws/control")
async def websocket_control(websocket: WebSocket):
    """WebSocket遠程控制端點"""
    await manager.connect(websocket)
    
    try:
        # 發送系統狀態
        status = await get_system_status()
        await websocket.send_json({
            "type": "status",
            "data": status
        })
        
        while True:
            # 接收指令
            data = await websocket.receive_json()
            command_type = data.get("type")
            
            if command_type == "execute":
                # 執行指令
                command = data.get("command", "")
                command_id = secrets.token_urlsafe(8)
                
                # 加入隊列
                task_queue.put({
                    "command_id": command_id,
                    "command": command,
                    "parameters": data.get("parameters", {})
                })
                
                await websocket.send_json({
                    "type": "queued",
                    "command_id": command_id,
                    "message": "指令已加入執行隊列"
                })
                
                # 等待結果
                while True:
                    if not result_queue.empty():
                        result = result_queue.get()
                        if result["command_id"] == command_id:
                            await websocket.send_json({
                                "type": "result",
                                "data": result
                            })
                            break
                    await asyncio.sleep(0.1)
                    
            elif command_type == "status":
                # 獲取狀態
                status = await get_system_status()
                await websocket.send_json({
                    "type": "status",
                    "data": status
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"WebSocket錯誤:\n{error_detail}")

if __name__ == "__main__":
    import uvicorn
    
    logger.info("啟動築未科技遠程控制服務器...")
    logger.info("控制面板: http://localhost:8005")
    logger.info("API文檔: http://localhost:8005/docs")
    
    # 檢查Ollama狀態
    status, message = ai_controller.check_ollama_status()
    logger.info(f"Ollama狀態: {message}")
    
    # 啟動定期清理任務
    async def main():
        asyncio.create_task(_cleanup_contexts())
        
        # 啟動服務器
        config = uvicorn.Config(
            app, 
            host="0.0.0.0", 
            port=8005,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    asyncio.run(main())
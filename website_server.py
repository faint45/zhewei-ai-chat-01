#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技官方網站 - 完整網站系統
包含企業官網、管理後台、用戶認證等功能
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
from ai_service import AIService
from config_ai import AIConfig, ai_config

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 創建 FastAPI 應用
app = FastAPI(
    title="築未科技官方網站",
    description="企業官網 + AI大腦 + 管理後台系統",
    version="2.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生產環境中應該限制特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 靜態文件目錄
app.mount("/static", StaticFiles(directory="static"), name="static")

# 模板目錄
templates = Jinja2Templates(directory="templates")

# 數據庫初始化
class Database:
    def __init__(self):
        self.db_path = "website.db"
        self.init_db()
    
    def init_db(self):
        """初始化數據庫表結構"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 用戶表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TEXT NOT NULL,
                last_login TEXT
            )
        ''')
        
        # 聯繫表單表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contact_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                message TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                status TEXT DEFAULT 'new'
            )
        ''')
        
        # 對話記錄表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                ip_address TEXT
            )
        ''')
        
        # 網站統計表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS site_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                visits INTEGER DEFAULT 0,
                unique_visitors INTEGER DEFAULT 0,
                contact_submissions INTEGER DEFAULT 0
            )
        ''')
        
        # 創建默認管理員用戶
        admin_password = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute('''
            INSERT OR IGNORE INTO users (username, email, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', ("admin", "admin@zhuwei-tech.com", admin_password, "admin", datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        logger.info("數據庫初始化完成")
    
    def get_connection(self):
        """獲取數據庫連接"""
        return sqlite3.connect(self.db_path)

# 初始化數據庫
db = Database()

# 數據模型
class User(BaseModel):
    username: str
    email: str
    role: str = "user"

class ContactSubmission(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    message: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str
    timestamp: str
    session_id: Optional[str] = None

# 會話管理
class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
    
    def create_session(self, user_id: int, username: str) -> str:
        """創建新會話"""
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            "user_id": user_id,
            "username": username,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[Dict]:
        """驗證會話有效性"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            # 檢查會話是否過期（24小時）
            last_activity = datetime.fromisoformat(session["last_activity"])
            if datetime.now() - last_activity > timedelta(hours=24):
                del self.sessions[session_id]
                return None
            
            # 更新最後活動時間
            session["last_activity"] = datetime.now().isoformat()
            return session
        return None

session_manager = SessionManager()

# 依賴注入函數
async def get_current_user(request: Request):
    """獲取當前用戶"""
    session_id = request.cookies.get("session_id")
    if session_id:
        session = session_manager.validate_session(session_id)
        if session:
            return session
    return None

# 網站統計
class SiteStatistics:
    def __init__(self):
        self.daily_visits = {}
        self.unique_visitors = set()
    
    def record_visit(self, ip_address: str):
        """記錄訪問"""
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.daily_visits:
            self.daily_visits[today] = 0
        self.daily_visits[today] += 1
        
        # 記錄唯一訪問者（基於IP）
        visitor_key = f"{today}_{ip_address}"
        if visitor_key not in self.unique_visitors:
            self.unique_visitors.add(visitor_key)
            
            # 保存到數據庫
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO site_stats (date, visits, unique_visitors)
                VALUES (?, COALESCE((SELECT visits FROM site_stats WHERE date = ?), 0) + 1, 
                        COALESCE((SELECT unique_visitors FROM site_stats WHERE date = ?), 0) + 1)
            ''', (today, today, today))
            conn.commit()
            conn.close()

site_stats = SiteStatistics()

# 網站路由
@app.get("/")
async def home(request: Request):
    """網站首頁"""
    # 記錄訪問統計
    client_ip = request.client.host if request.client else "unknown"
    site_stats.record_visit(client_ip)
    
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/about")
async def about(request: Request):
    """關於我們頁面"""
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/services")
async def services(request: Request):
    """服務項目頁面"""
    return templates.TemplateResponse("services.html", {"request": request})

@app.get("/products")
async def products(request: Request):
    """產品展示頁面"""
    return templates.TemplateResponse("products.html", {"request": request})

@app.get("/contact")
async def contact(request: Request):
    """聯繫我們頁面"""
    return templates.TemplateResponse("contact.html", {"request": request})

@app.get("/chat")
async def chat_page(request: Request):
    """AI對話頁面"""
    return templates.TemplateResponse("chat.html", {"request": request})

# API 路由
@app.post("/api/contact")
async def submit_contact(form_data: ContactSubmission, request: Request):
    """提交聯繫表單"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO contact_submissions (name, email, phone, message, submitted_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (form_data.name, form_data.email, form_data.phone, form_data.message, 
              datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # 更新統計
        today = datetime.now().strftime("%Y-%m-%d")
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE site_stats SET contact_submissions = contact_submissions + 1
            WHERE date = ?
        ''', (today,))
        conn.commit()
        conn.close()
        
        logger.info(f"新的聯繫表單提交: {form_data.email}")
        
        return {"success": True, "message": "感謝您的諮詢！我們將盡快與您聯繫。"}
        
    except Exception as e:
        logger.error(f"提交聯繫表單失敗: {e}")
        return {"success": False, "message": "提交失敗，請稍後重試。"}

@app.get("/api/stats")
async def get_site_stats():
    """獲取網站統計數據"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # 總訪問量
    cursor.execute("SELECT SUM(visits) FROM site_stats")
    total_visits = cursor.fetchone()[0] or 0
    
    # 總聯繫提交
    cursor.execute("SELECT SUM(contact_submissions) FROM site_stats")
    total_submissions = cursor.fetchone()[0] or 0
    
    # 今日數據
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT visits, unique_visitors, contact_submissions FROM site_stats WHERE date = ?", (today,))
    today_data = cursor.fetchone()
    
    conn.close()
    
    return {
        "total_visits": total_visits,
        "total_submissions": total_submissions,
        "today": {
            "visits": today_data[0] if today_data else 0,
            "unique_visitors": today_data[1] if today_data else 0,
            "contact_submissions": today_data[2] if today_data else 0
        }
    }

# 管理後台路由
@app.get("/admin")
async def admin_login_page(request: Request):
    """管理員登錄頁面"""
    return templates.TemplateResponse("admin/login.html", {"request": request})

@app.post("/admin/login")
async def admin_login(username: str = Form(...), password: str = Form(...)):
    """管理員登錄"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, username, password_hash FROM users WHERE username = ? AND role = 'admin'", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and user[2] == hashlib.sha256(password.encode()).hexdigest():
            session_id = session_manager.create_session(user[0], user[1])
            
            response = RedirectResponse(url="/admin/dashboard", status_code=303)
            response.set_cookie(key="session_id", value=session_id, httponly=True, max_age=86400)
            return response
        else:
            return RedirectResponse(url="/admin?error=1", status_code=303)
            
    except Exception as e:
        logger.error(f"管理員登錄失敗: {e}")
        return RedirectResponse(url="/admin?error=1", status_code=303)

@app.get("/admin/dashboard")
async def admin_dashboard(request: Request, current_user: Optional[Dict] = Depends(get_current_user)):
    """管理員儀表板"""
    if not current_user or current_user.get("role") != "admin":
        return RedirectResponse(url="/admin", status_code=303)
    
    # 獲取統計數據
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # 聯繫表單
    cursor.execute("SELECT * FROM contact_submissions ORDER BY submitted_at DESC LIMIT 10")
    submissions = cursor.fetchall()
    
    # 網站統計
    cursor.execute("SELECT * FROM site_stats ORDER BY date DESC LIMIT 7")
    stats = cursor.fetchall()
    
    # 用戶統計
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    conn.close()
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "current_user": current_user,
        "submissions": submissions,
        "stats": stats,
        "user_count": user_count
    })

# 初始化 AI 服務
ai_service: Optional[AIService] = None
if AIConfig.validate(ai_config):
    ai_service = AIService(ai_config)
    logger.info(f"🤖 AI 服務已啟用 - {ai_service.config.MODEL_TYPE.value} 模式")
else:
    logger.info("🔄 AI 服務未啟用，使用演示模式")

# WebSocket 對話功能（保留原有功能）
active_connections: List[WebSocket] = []

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 對話端點"""
    await websocket.accept()
    active_connections.append(websocket)
    session_id = str(id(websocket))
    
    logger.info(f"新聊天連接建立: {session_id}")
    
    try:
        # 發送歡迎消息
        welcome_msg = "您好！我是築未科技大腦，很高興為您服務。有什麼可以幫您的嗎？"
        
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
                logger.info(f"收到聊天消息: {message[:50]}...")
                
                # 處理消息並生成回應
                if ai_service:
                    response = await ai_service.generate_response(message, session_id)
                else:
                    # 演示模式回應
                    response = f"我收到了您的訊息：「{message}」\n\n築未科技大腦正在學習如何更好地回應您的問題。"
                
                # 保存到數據庫
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO chat_history (session_id, user_message, ai_response, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, message, response, datetime.now().isoformat()))
                conn.commit()
                conn.close()
                
                # 發送回應
                await websocket.send_json({
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
    
    except WebSocketDisconnect:
        logger.info(f"聊天連接斷開: {session_id}")
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"WebSocket 錯誤:\n{error_detail}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy", 
        "service": "築未科技官方網站",
        "timestamp": datetime.now().isoformat(),
        "ai_enabled": ai_service is not None
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info("啟動築未科技官方網站服務器...")
    logger.info("網站地址: http://localhost:8000")
    logger.info("管理後台: http://localhost:8000/admin")
    logger.info("AI對話: http://localhost:8000/chat")
    
    uvicorn.run(
        app,
        host="0.0.0.0",  # 允許外部訪問
        port=8000,
        log_level="info"
    )
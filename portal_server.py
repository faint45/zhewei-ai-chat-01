# -*- coding: utf-8 -*-
"""
築未科技 Portal 服務入口網站 PWA
Port: 8888
支援：WebSocket 對話、授權管理、離線快取
"""

import os
import asyncio
import uuid
import json
import time
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx

# 認證模組
try:
    import auth_manager as _auth
    _auth_ok = True
except ImportError:
    _auth_ok = False

ROOT = Path(__file__).resolve().parent
PORTAL_DIR = ROOT / "portal"
UPLOAD_DIR = PORTAL_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

PORTAL_VERSION = "2.1.0"
PORTAL_BUILD_TIME = datetime.now().isoformat()

app = FastAPI(title="Zhe-Wei Tech Portal PWA", version=PORTAL_VERSION)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 工作流管理
class WorkflowManager:
    def __init__(self):
        self.workflows: Dict[str, dict] = {}
        self._load()

    def _path(self):
        return PORTAL_DIR / "workflows.json"

    def _load(self):
        p = self._path()
        if p.exists():
            try:
                self.workflows = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                self.workflows = {}

    def _save(self):
        self._path().write_text(json.dumps(self.workflows, ensure_ascii=False, indent=2), encoding="utf-8")

    def create(self, name: str, steps: List[str], category: str = "general") -> dict:
        wf_id = str(uuid.uuid4())[:8]
        wf = {
            "id": wf_id,
            "name": name,
            "category": category,
            "steps": [{"name": s, "status": "pending", "started": None, "finished": None} for s in steps],
            "status": "pending",
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "progress": 0
        }
        self.workflows[wf_id] = wf
        self._save()
        return wf

    def update_step(self, wf_id: str, step_index: int, status: str) -> Optional[dict]:
        wf = self.workflows.get(wf_id)
        if not wf or step_index >= len(wf["steps"]):
            return None
        now = datetime.now().isoformat()
        wf["steps"][step_index]["status"] = status
        if status == "running":
            wf["steps"][step_index]["started"] = now
            wf["status"] = "running"
        elif status in ("done", "error"):
            wf["steps"][step_index]["finished"] = now
        done = sum(1 for s in wf["steps"] if s["status"] == "done")
        wf["progress"] = int(done / len(wf["steps"]) * 100)
        if all(s["status"] == "done" for s in wf["steps"]):
            wf["status"] = "completed"
        elif any(s["status"] == "error" for s in wf["steps"]):
            wf["status"] = "error"
        wf["updated"] = now
        self._save()
        return wf

    def list_all(self) -> list:
        return sorted(self.workflows.values(), key=lambda w: w["created"], reverse=True)

    def get(self, wf_id: str) -> Optional[dict]:
        return self.workflows.get(wf_id)

    def delete(self, wf_id: str) -> bool:
        if wf_id in self.workflows:
            del self.workflows[wf_id]
            self._save()
            return True
        return False

wf_manager = WorkflowManager()

# WebSocket 連接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.auth_requests: Dict[str, dict] = {}
    
    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        session_id = str(uuid.uuid4())
        self.active_connections[session_id] = websocket
        return session_id
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)
    
    async def request_auth(self, session_id: str, action: str, details: str) -> str:
        request_id = str(uuid.uuid4())
        self.auth_requests[request_id] = {
            "session_id": session_id,
            "action": action,
            "details": details,
            "approved": None
        }
        
        await self.send_message(session_id, {
            "type": "auth_request",
            "request_id": request_id,
            "message": f"請求授權執行: {action}\n詳情: {details}"
        })
        
        return request_id
    
    def get_auth_result(self, request_id: str) -> bool:
        if request_id in self.auth_requests:
            return self.auth_requests[request_id].get("approved", False)
        return False

manager = ConnectionManager()

# 服務配置
SERVICES = {
    "jarvis": {
        "name": "Jarvis AI Brain",
        "url": "https://jarvis.zhe-wei.net",
        "health": "https://jarvis.zhe-wei.net/health",
        "local": "http://localhost:8000/health",
        "icon": "brain",
        "color": "blue"
    },
    "bridge": {
        "name": "Smart Bridge",
        "url": "https://bridge.zhe-wei.net",
        "health": "https://bridge.zhe-wei.net/health",
        "local": "http://localhost:8003/health",
        "icon": "bridge-water",
        "color": "cyan"
    },
    "dify": {
        "name": "Dify AI Platform",
        "url": "https://dify.zhe-wei.net",
        "health": "https://dify.zhe-wei.net/health",
        "local": "http://localhost:8080/health",
        "icon": "project-diagram",
        "color": "indigo"
    },
    "cms": {
        "name": "營建管理系統",
        "url": "https://cms.zhe-wei.net",
        "health": "https://cms.zhe-wei.net/health",
        "local": "http://localhost:8020/health",
        "icon": "hard-hat",
        "color": "orange"
    },
    "vision": {
        "name": "AI 視覺辨識",
        "url": "https://vision.zhe-wei.net",
        "health": "https://vision.zhe-wei.net/healthz",
        "local": "http://localhost:8030/healthz",
        "icon": "eye",
        "color": "green"
    },
    "codesim": {
        "name": "代碼模擬器",
        "url": "https://codesim.zhe-wei.net",
        "health": "https://codesim.zhe-wei.net/health",
        "local": "http://localhost:8001/health",
        "icon": "code",
        "color": "gray"
    }
}

@app.get("/")
async def root():
    """返回入口網站首頁"""
    html_path = PORTAL_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Portal not found</h1>", status_code=404)

@app.get("/health")
async def health():
    """健康檢查"""
    return {"status": "ok", "service": "portal", "version": PORTAL_VERSION}

@app.get("/api/version")
async def get_version():
    """取得 Portal 版本資訊"""
    return {
        "version": PORTAL_VERSION,
        "build_time": PORTAL_BUILD_TIME,
        "name": "築未科技 Portal PWA"
    }

@app.get("/api/services")
async def get_services():
    """取得所有服務列表"""
    return {
        "ok": True,
        "services": SERVICES,
        "count": len(SERVICES)
    }

@app.get("/api/services/status")
async def check_services_status():
    """檢查所有服務狀態"""
    results = {}
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_id, service in SERVICES.items():
            try:
                # 優先檢查本地
                response = await client.get(service["local"])
                results[service_id] = {
                    "status": "online" if response.status_code == 200 else "error",
                    "name": service["name"],
                    "url": service["url"],
                    "response_time_ms": int(response.elapsed.total_seconds() * 1000)
                }
            except Exception:
                # 本地失敗，嘗試外網
                try:
                    response = await client.get(service["health"])
                    results[service_id] = {
                        "status": "online" if response.status_code == 200 else "error",
                        "name": service["name"],
                        "url": service["url"],
                        "response_time_ms": int(response.elapsed.total_seconds() * 1000)
                    }
                except Exception as e:
                    results[service_id] = {
                        "status": "offline",
                        "name": service["name"],
                        "url": service["url"],
                        "error": str(e)
                    }
    
    online_count = sum(1 for s in results.values() if s["status"] == "online")
    
    return {
        "ok": True,
        "services": results,
        "summary": {
            "total": len(SERVICES),
            "online": online_count,
            "offline": len(SERVICES) - online_count
        }
    }

@app.get("/api/stats")
async def get_stats():
    """取得系統統計"""
    return {
        "ok": True,
        "uptime": "99.9%",
        "avg_response_time_ms": 180,
        "total_services": len(SERVICES),
        "features": [
            "AI 對話與知識管理",
            "智慧成本優化",
            "工程專案管理",
            "視覺辨識與 OCR",
            "代碼執行與分析",
            "工作流自動化"
        ]
    }

# ── 檔案上傳 API ──
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}
ALLOWED_FILE_TYPES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".csv", ".zip", ".json", ".py", ".js", ".html", ".css", ".md"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """上傳檔案（圖片或文件）"""
    ext = Path(file.filename).suffix.lower()
    is_image = ext in ALLOWED_IMAGE_TYPES
    is_file = ext in ALLOWED_FILE_TYPES
    if not is_image and not is_file:
        return JSONResponse({"ok": False, "error": f"不支援的檔案類型: {ext}"}, status_code=400)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return JSONResponse({"ok": False, "error": "檔案大小超過 10MB 限制"}, status_code=400)

    file_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = UPLOAD_DIR / file_id
    save_path.write_bytes(content)

    result = {
        "ok": True,
        "file_id": file_id,
        "filename": file.filename,
        "size": len(content),
        "type": "image" if is_image else "file",
        "url": f"/api/uploads/{file_id}",
        "uploaded": datetime.now().isoformat()
    }
    if is_image:
        result["thumbnail"] = f"/api/uploads/{file_id}"
    return result

@app.get("/api/uploads/{file_id}")
async def get_uploaded_file(file_id: str):
    """取得已上傳的檔案"""
    fpath = UPLOAD_DIR / file_id
    if not fpath.exists():
        return JSONResponse({"ok": False, "error": "檔案不存在"}, status_code=404)
    return FileResponse(fpath)

# ── 工作流 API ──
@app.get("/api/workflows")
async def list_workflows():
    """列出所有工作流"""
    return {"ok": True, "workflows": wf_manager.list_all()}

@app.post("/api/workflows")
async def create_workflow(data: dict):
    """建立工作流"""
    name = data.get("name", "未命名工作流")
    steps = data.get("steps", [])
    category = data.get("category", "general")
    if not steps:
        return JSONResponse({"ok": False, "error": "至少需要一個步驟"}, status_code=400)
    wf = wf_manager.create(name, steps, category)
    return {"ok": True, "workflow": wf}

@app.get("/api/workflows/{wf_id}")
async def get_workflow(wf_id: str):
    """取得工作流詳情"""
    wf = wf_manager.get(wf_id)
    if not wf:
        return JSONResponse({"ok": False, "error": "工作流不存在"}, status_code=404)
    return {"ok": True, "workflow": wf}

@app.put("/api/workflows/{wf_id}/steps/{step_index}")
async def update_workflow_step(wf_id: str, step_index: int, data: dict):
    """更新工作流步驟狀態"""
    status = data.get("status", "done")
    wf = wf_manager.update_step(wf_id, step_index, status)
    if not wf:
        return JSONResponse({"ok": False, "error": "工作流或步驟不存在"}, status_code=404)
    return {"ok": True, "workflow": wf}

@app.delete("/api/workflows/{wf_id}")
async def delete_workflow(wf_id: str):
    """刪除工作流"""
    if wf_manager.delete(wf_id):
        return {"ok": True}
    return JSONResponse({"ok": False, "error": "工作流不存在"}, status_code=404)

@app.get("/manifest.json")
async def get_manifest():
    """返回 PWA manifest（動態注入版本號）"""
    manifest_path = PORTAL_DIR / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["version"] = PORTAL_VERSION
        manifest["build_time"] = PORTAL_BUILD_TIME
        return JSONResponse(manifest, media_type="application/json")
    return JSONResponse({"error": "Manifest not found"}, status_code=404)

@app.get("/sw.js")
async def get_service_worker():
    """返回 Service Worker"""
    sw_path = PORTAL_DIR / "sw.js"
    if sw_path.exists():
        return FileResponse(sw_path, media_type="application/javascript")
    return JSONResponse({"error": "Service Worker not found"}, status_code=404)

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket 對話端點"""
    session_id = await manager.connect(websocket)
    print(f"✅ WebSocket 連接: {session_id}")
    
    try:
        await manager.send_message(session_id, {
            "type": "system",
            "content": "歡迎使用築未科技 AI 助手！我可以幫你管理服務、執行任務和授權操作。\n\n支援功能：\n📎 上傳圖片/檔案\n📋 查詢服務狀態\n🔄 管理工作流\n🔐 授權操作"
        })
        
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "message":
                user_message = data.get("content", "")
                attachments = data.get("attachments", [])
                print(f"📨 收到訊息 [{session_id}]: {user_message} (附件: {len(attachments)}個)")
                
                response = await process_command(session_id, user_message, attachments)
                await manager.send_message(session_id, {
                    "type": "message",
                    "content": response
                })
            
            elif message_type == "auth_response":
                request_id = data.get("request_id")
                approved = data.get("approved", False)
                
                if request_id in manager.auth_requests:
                    manager.auth_requests[request_id]["approved"] = approved
                    print(f"{'✅' if approved else '❌'} 授權回應 [{request_id}]: {approved}")
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        print(f"❌ WebSocket 斷開: {session_id}")
    except Exception as e:
        print(f"❌ WebSocket 錯誤: {e}")
        manager.disconnect(session_id)

async def process_command(session_id: str, message: str, attachments: list = None) -> str:
    """處理用戶命令"""
    message_lower = message.lower()
    att_info = ""
    if attachments:
        att_info = f"\n\n📎 已收到 {len(attachments)} 個附件：\n"
        for a in attachments:
            att_info += f"  • {a.get('filename', '未知')} ({a.get('type', 'file')}, {_fmt_size(a.get('size', 0))})\n"
    
    # 服務狀態查詢（即時檢測）
    if "狀態" in message or "status" in message_lower:
        lines = ["正在檢查所有服務狀態...\n"]
        async with httpx.AsyncClient(timeout=5.0) as client:
            for sid, svc in SERVICES.items():
                try:
                    r = await client.get(svc["local"])
                    lines.append(f"✅ {svc['name']} — 運行中 ({int(r.elapsed.total_seconds()*1000)}ms)")
                except Exception:
                    try:
                        r = await client.get(svc["health"])
                        lines.append(f"✅ {svc['name']} — 外網可達 ({int(r.elapsed.total_seconds()*1000)}ms)")
                    except Exception:
                        lines.append(f"❌ {svc['name']} — 離線")
        return "\n".join(lines) + att_info
    
    # 工作流查詢
    elif "工作流" in message or "workflow" in message_lower:
        wfs = wf_manager.list_all()
        if not wfs:
            return "📋 目前沒有工作流。\n\n可以在工作流面板中建立新的工作流。" + att_info
        lines = [f"📋 共 {len(wfs)} 個工作流：\n"]
        for wf in wfs[:5]:
            icon = {"completed": "✅", "running": "🔄", "error": "❌", "pending": "⏳"}.get(wf["status"], "⏳")
            lines.append(f"{icon} {wf['name']} — {wf['progress']}% ({wf['status']})")
        return "\n".join(lines) + att_info
    
    # 重啟服務（需要授權）
    elif "重啟" in message or "restart" in message_lower:
        request_id = await manager.request_auth(
            session_id,
            "重啟服務",
            f"用戶請求重啟服務: {message}"
        )
        await asyncio.sleep(2)
        if manager.get_auth_result(request_id):
            return "✅ 授權已批准，正在重啟服務..." + att_info
        else:
            return "❌ 授權被拒絕，操作已取消" + att_info
    
    # MCP 工具
    elif "mcp" in message_lower or "工具" in message:
        return "📋 MCP 工具系統\n\n" + \
               "目前有 26 個 MCP 工具可用：\n" + \
               "• AI & 搜尋 (5個)\n" + \
               "• 資料庫 (5個)\n" + \
               "• 開發工具 (5個)\n" + \
               "• 地圖導航 (3個)\n" + \
               "• 其他專業工具 (8個)\n\n" + \
               "輸入 'mcp list' 查看詳細列表" + att_info
    
    # 預設回應
    else:
        return f"收到您的訊息：「{message}」{att_info}\n\n" + \
               "我可以幫你：\n" + \
               "• 📊 查詢服務狀態（輸入「狀態」）\n" + \
               "• 📋 查看工作流（輸入「工作流」）\n" + \
               "• 🔧 管理 MCP 工具（輸入「mcp」）\n" + \
               "• 🔐 執行授權操作（輸入「重啟」等）\n" + \
               "• 📎 上傳圖片/檔案（點擊附件按鈕）"

def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size/1024:.1f}KB"
    else:
        return f"{size/1024/1024:.1f}MB"

# ── 帳戶申請 API ──
@app.post("/api/auth/register")
async def register_account(data: dict):
    """帳戶申請（註冊）"""
    if not _auth_ok:
        return JSONResponse({"ok": False, "error": "認證模組未載入"}, status_code=500)
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    email = (data.get("email") or "").strip()
    if not username or not password:
        return JSONResponse({"ok": False, "error": "帳號和密碼為必填"}, status_code=400)
    result = _auth.register_user(username, password, email)
    if result.get("ok"):
        return {"ok": True, "message": "帳戶申請成功！請等待管理員審核啟用。", "username": username}
    return JSONResponse({"ok": False, "error": result.get("error", "註冊失敗")}, status_code=400)

@app.post("/api/auth/login")
async def login_account(data: dict):
    """帳戶登入"""
    if not _auth_ok:
        return JSONResponse({"ok": False, "error": "認證模組未載入"}, status_code=500)
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    result = _auth.login_user(username, password)
    if result.get("ok"):
        return result
    return JSONResponse({"ok": False, "error": result.get("error", "登入失敗")}, status_code=401)

@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """驗證 Token 並回傳當前用戶資訊"""
    if not _auth_ok:
        return JSONResponse({"ok": False, "error": "認證模組未載入"}, status_code=500)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse({"ok": False, "error": "未提供 Token"}, status_code=401)
    token = auth_header[7:]
    data = _auth.verify_token(token)
    if not data:
        return JSONResponse({"ok": False, "error": "Token 無效或已過期"}, status_code=401)
    return {
        "ok": True,
        "user": {
            "id": data.get("sub", ""),
            "username": data.get("usr", data.get("username", "")),
            "role": data.get("role", "pending"),
            "subscription": data.get("sub_status", "pending")
        }
    }

# 靜態文件掛載（必須放在所有路由之後）
STATIC_DIR = PORTAL_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if __name__ == "__main__":
    PORT = int(os.environ.get("PORTAL_PORT", "8888"))
    print(f"🌐 Portal PWA 啟動於 http://0.0.0.0:{PORT}")
    print(f"📱 PWA 功能：離線快取、WebSocket 對話、授權管理")
    uvicorn.run(app, host="0.0.0.0", port=PORT)

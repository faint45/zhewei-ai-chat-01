# -*- coding: utf-8 -*-
"""
築未科技 — 代碼模擬器主服務
FastAPI + WebSocket，提供代碼編輯、預覽、AI 對話、文件管理
Port: 8001
"""
import os
import sys
import json
import asyncio
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
import uvicorn

# 載入 .env
try:
    from dotenv import load_dotenv
    ROOT = Path(__file__).resolve().parent.parent
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from file_manager import FileManager
from ai_code_service import AICodeService

# 認證系統（複用主系統 auth_manager）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import auth_manager
    AUTH_AVAILABLE = True
    print("[CodeSimulator] ✅ 認證系統已載入")
except ImportError as e:
    AUTH_AVAILABLE = False
    print(f"[CodeSimulator] ⚠️ 認證系統不可用: {e}")

# ── Config ──────────────────────────────────────────────
PORT = int(os.environ.get("SIMULATOR_PORT", "8001"))
HOST = os.environ.get("SIMULATOR_HOST", "0.0.0.0")
PROJECTS_DIR = Path(__file__).resolve().parent / "projects"

# ── App ─────────────────────────────────────────────────
app = FastAPI(title="築未科技代碼模擬器", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fm = FileManager(str(PROJECTS_DIR))
ai = AICodeService()

# ── Static files ────────────────────────────────────────
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# ── WebSocket connections ───────────────────────────────
ws_connections: list[WebSocket] = []


async def broadcast(msg: dict):
    for ws in ws_connections[:]:
        try:
            await ws.send_json(msg)
        except Exception:
            ws_connections.remove(ws)


# ── Helper: Token ─────────────────────────────
def _extract_token(request: Request) -> dict | None:
    """從 Authorization header 提取並驗證 JWT"""
    if not AUTH_AVAILABLE:
        return None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth_manager.verify_token(auth[7:])
    return None


# ── Routes: Auth ───────────────────────────────
@app.post("/api/auth/login")
async def auth_login(body: dict):
    if not AUTH_AVAILABLE:
        raise HTTPException(503, "認證系統不可用")
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    if not username or not password:
        return {"ok": False, "error": "帳號和密碼為必填"}
    return auth_manager.login_user(username, password)


@app.post("/api/auth/register")
async def auth_register(body: dict):
    if not AUTH_AVAILABLE:
        raise HTTPException(503, "認證系統不可用")
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    email = body.get("email", "").strip()
    return auth_manager.register_user(username, password, email)


@app.get("/api/auth/me")
async def auth_me(request: Request):
    data = _extract_token(request)
    if not data:
        return {"ok": False, "error": "未登入或 Token 無效"}
    user = auth_manager.get_user_info(data.get("sub", ""))
    if not user:
        return {"ok": False, "error": "用戶不存在"}
    return {"ok": True, "user": user}


# ── Routes: Pages ──────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root_redirect():
    return RedirectResponse("/simulator-login", status_code=302)


@app.get("/simulator-login", response_class=HTMLResponse)
async def login_page():
    html_path = Path(__file__).resolve().parent / "templates" / "simulator-login.html"
    if not html_path.exists():
        raise HTTPException(404, "simulator-login.html not found")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/simulator", response_class=HTMLResponse)
async def simulator_page():
    """模擬器主頁（前端 JS 檢查 token，未登入自動跳轉 /simulator-login）"""
    html_path = Path(__file__).resolve().parent / "templates" / "simulator.html"
    if not html_path.exists():
        raise HTTPException(404, "simulator.html not found")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/health")
async def health():
    return {"status": "ok", "service": "code-simulator", "version": "1.0.0"}


# ── Routes: Projects ───────────────────────────────────
@app.get("/api/projects")
async def list_projects():
    return fm.list_projects()


@app.post("/api/projects")
async def create_project(body: dict):
    name = body.get("name", "").strip()
    template = body.get("template", "html")
    if not name:
        raise HTTPException(400, "Project name required")
    result = fm.create_project(name, template)
    if "error" in result:
        raise HTTPException(400, result["error"])
    await broadcast({"type": "project_created", "data": result})
    return result


@app.delete("/api/projects/{project}")
async def delete_project(project: str):
    result = fm.delete_project(project)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


# ── Routes: Files ───────────────────────────────────────
@app.get("/api/projects/{project}/files")
async def list_files(project: str):
    return fm.list_files(project)


@app.get("/api/projects/{project}/files/{file_path:path}")
async def read_file(project: str, file_path: str):
    result = fm.read_file(project, file_path)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@app.post("/api/projects/{project}/files/{file_path:path}")
async def save_file(project: str, file_path: str, body: dict):
    content = body.get("content", "")
    message = body.get("message", "")
    result = fm.save_file(project, file_path, content, message)
    await broadcast({"type": "file_saved", "data": {"project": project, "path": file_path}})
    return result


@app.delete("/api/projects/{project}/files/{file_path:path}")
async def delete_file(project: str, file_path: str):
    result = fm.delete_file(project, file_path)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@app.post("/api/projects/{project}/files/{file_path:path}/rename")
async def rename_file(project: str, file_path: str, body: dict):
    new_path = body.get("new_path", "").strip()
    if not new_path:
        raise HTTPException(400, "new_path required")
    return fm.rename_file(project, file_path, new_path)


# ── Routes: Version History ─────────────────────────────
@app.get("/api/projects/{project}/files/{file_path:path}/history")
async def file_history(project: str, file_path: str, limit: int = 20):
    return fm.get_file_history(project, file_path, limit)


@app.get("/api/versions/{version_id}")
async def get_version(version_id: int):
    result = fm.get_version_content(version_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@app.post("/api/versions/{version_id}/restore")
async def restore_version(version_id: int):
    result = fm.restore_version(version_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


# ── Routes: Preview ─────────────────────────────────────
@app.get("/preview/{project}/{file_path:path}")
async def preview_file(project: str, file_path: str):
    """直接返回項目文件用於 iframe 預覽"""
    fpath = PROJECTS_DIR / project / file_path
    if not fpath.exists():
        raise HTTPException(404, f"File not found: {file_path}")
    content_types = {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".jsx": "application/javascript",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".gif": "image/gif",
    }
    ext = fpath.suffix.lower()
    ct = content_types.get(ext, "text/plain")
    content = fpath.read_bytes()
    return HTMLResponse(content=content, media_type=ct)


# ── Routes: AI ──────────────────────────────────────────
@app.get("/api/ai/providers")
async def ai_providers():
    return {"providers": ai.get_available_providers()}


@app.post("/api/ai/chat")
async def ai_chat(body: dict):
    messages = body.get("messages", [])
    provider = body.get("provider", "auto")
    model = body.get("model", "")
    if not messages:
        raise HTTPException(400, "messages required")
    result = await ai.chat(messages, provider, model)
    return result


@app.post("/api/ai/chat/stream")
async def ai_chat_stream(body: dict):
    messages = body.get("messages", [])
    provider = body.get("provider", "auto")
    model = body.get("model", "")
    if not messages:
        raise HTTPException(400, "messages required")

    async def generate():
        async for chunk in ai.chat_stream(messages, provider, model):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/ai/analyze")
async def ai_analyze(body: dict):
    code = body.get("code", "")
    language = body.get("language", "javascript")
    provider = body.get("provider", "auto")
    if not code:
        raise HTTPException(400, "code required")
    return await ai.analyze_code(code, language, provider)


@app.post("/api/ai/optimize")
async def ai_optimize(body: dict):
    code = body.get("code", "")
    language = body.get("language", "javascript")
    instructions = body.get("instructions", "")
    provider = body.get("provider", "auto")
    if not code:
        raise HTTPException(400, "code required")
    return await ai.optimize_code(code, language, instructions, provider)


@app.post("/api/ai/fix")
async def ai_fix(body: dict):
    code = body.get("code", "")
    language = body.get("language", "javascript")
    error = body.get("error", "")
    provider = body.get("provider", "auto")
    if not code:
        raise HTTPException(400, "code required")
    return await ai.fix_code(code, language, error, provider)


@app.post("/api/ai/generate")
async def ai_generate(body: dict):
    description = body.get("description", "")
    language = body.get("language", "html")
    provider = body.get("provider", "auto")
    if not description:
        raise HTTPException(400, "description required")
    return await ai.generate_code(description, language, provider)


# ── Routes: Code Execution ─────────────────────────
EXEC_TIMEOUT = int(os.environ.get("EXEC_TIMEOUT", "30"))  # 秒
EXEC_RUNNERS = {
    "python": {"cmd": [sys.executable, "-u"], "ext": ".py"},
    "javascript": {"cmd": ["node"], "ext": ".js"},
    "typescript": {"cmd": ["npx", "ts-node"], "ext": ".ts"},
}


@app.post("/api/execute")
async def execute_code(body: dict):
    """執行代碼並返回 stdout/stderr（帶超時保護）"""
    code = body.get("code", "")
    language = body.get("language", "python")
    project = body.get("project", "")
    file_path = body.get("file_path", "")
    if not code.strip():
        raise HTTPException(400, "code required")

    runner = EXEC_RUNNERS.get(language)
    if not runner:
        return {"stdout": "", "stderr": f"不支援的語言: {language}\n支援: {', '.join(EXEC_RUNNERS.keys())}", "exit_code": 1, "duration": 0}

    # 寫入臨時檔案
    cwd = str(PROJECTS_DIR / project) if project and (PROJECTS_DIR / project).is_dir() else str(PROJECTS_DIR)
    try:
        result = await asyncio.to_thread(_run_code, code, runner, cwd)
        return result
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": 1, "duration": 0}


def _run_code(code: str, runner: dict, cwd: str) -> dict:
    """在子進程中執行代碼（同步，由 asyncio.to_thread 包裝）"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=runner["ext"], delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp_path = f.name
    try:
        start = time.time()
        proc = subprocess.run(
            runner["cmd"] + [tmp_path],
            capture_output=True,
            text=True,
            timeout=EXEC_TIMEOUT,
            cwd=cwd,
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"},
        )
        duration = round(time.time() - start, 2)
        return {
            "stdout": proc.stdout[-10000:] if len(proc.stdout) > 10000 else proc.stdout,
            "stderr": proc.stderr[-5000:] if len(proc.stderr) > 5000 else proc.stderr,
            "exit_code": proc.returncode,
            "duration": duration,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"⬛ 執行超時（上限 {EXEC_TIMEOUT} 秒）", "exit_code": 124, "duration": EXEC_TIMEOUT}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ── WebSocket: Real-time preview ────────────────────────
@app.websocket("/ws/preview")
async def ws_preview(ws: WebSocket):
    await ws.accept()
    ws_connections.append(ws)
    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "code_update":
                project = data.get("project", "")
                file_path = data.get("file_path", "")
                content = data.get("content", "")
                if project and file_path:
                    fm.save_file(project, file_path, content, "Auto-save")
                    await broadcast({
                        "type": "preview_update",
                        "data": {"project": project, "file_path": file_path},
                    })

            elif msg_type == "ping":
                await ws.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    finally:
        if ws in ws_connections:
            ws_connections.remove(ws)


# ── Startup / Shutdown ──────────────────────────────────
@app.on_event("startup")
async def startup():
    if not fm.list_projects():
        fm.create_project("demo", "html")
    print(f"[CodeSimulator] Running on http://{HOST}:{PORT}/simulator")


@app.on_event("shutdown")
async def shutdown():
    await ai.close()


# ── Main ────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("code_simulator:app", host=HOST, port=PORT, reload=True)

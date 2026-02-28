# -*- coding: utf-8 -*-
"""
築未科技 Brain Server v2.0 — 模組化架構
原始 brain_server.py (4435行) → 精簡主檔 + 13 Router 模組

Phase 1: 結構化日誌 + 全域錯誤追蹤
Phase 2: Pydantic 驗證 + 認證審計 + 安全中間件
Phase 3: Router 模組化拆分
"""
import asyncio
import json
import logging
import os
import signal
import traceback

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ── 初始化共用依賴 ──
from routers.deps import (
    setup_logging, global_exception_handler, logger,
    ROOT, STATIC_DIR, FALLBACK_STATIC, PROGRESS_FILE,
    ws_clients, agent_tasks, agent_task_queue,
    _load_agent_tasks, _save_agent_tasks, _now_iso,
    _enqueue_host_job, _read_host_job_result,
    _remote_chat_reply, _clean_model_output, _provider_alias,
    gemini_ai, ollama_ai, smart_ai, sec_mw,
    BRAIN_WORKSPACE,
)

# ── 初始化日誌 ──
setup_logging()

# ── FastAPI App ──
app = FastAPI(
    title="築未科技 Brain Server",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── 全域錯誤處理 (Phase 1) ──
app.add_exception_handler(Exception, global_exception_handler)

# ── CORS ──
ALLOWED_ORIGINS = [
    o.strip() for o in
    os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:8888,https://zhe-wei.net,https://jarvis.zhe-wei.net,https://www.zhe-wei.net").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 限流中間件（整合 security_middleware 工具函式）──
@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    path = request.url.path
    if path.startswith(("/docs", "/redoc", "/openapi", "/healthz", "/readyz", "/static", "/favicon")):
        return await call_next(request)
    if sec_mw:
        client_ip = sec_mw.get_client_ip(request)
        category = sec_mw.classify_route(path, request.method)
        allowed, info = sec_mw.rate_limiter.is_allowed(client_ip, category)
        if not allowed:
            from fastapi.responses import JSONResponse
            logger.warning("Rate limit exceeded for %s (%s)", client_ip, category)
            return JSONResponse({"ok": False, "error": "請求過於頻繁，請稍後再試"}, status_code=429)
    return await call_next(request)

# ── 靜態檔案 ──
@app.get("/static/index.html")
async def get_static_index():
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "index.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("index.html not found", status_code=404)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── PWA 男神拍拍 ──
PHOTO_APP_DIR = ROOT / "photo_app"
if PHOTO_APP_DIR.exists():
    app.mount("/photo_app", StaticFiles(directory=str(PHOTO_APP_DIR)), name="photo_app")
    from fastapi.responses import RedirectResponse

    @app.get("/photo-app")
    async def redirect_photo_app():
        return RedirectResponse(url="/photo_app/index.html", status_code=302)

    @app.get("/photo-app/")
    async def redirect_photo_app_slash():
        return RedirectResponse(url="/photo_app/index.html", status_code=302)

# ── 註冊所有 Router ──
from routers.auth import router as auth_router
from routers.pages import router as pages_router
from routers.system import router as system_router
from routers.commercial import router as commercial_router
from routers.usage import router as usage_router
from routers.proxy import router as proxy_router
from routers.asset import router as asset_router
from routers.host_phone import router as host_phone_router
from routers.smart_chat import router as smart_chat_router
from routers.agent import router as agent_router
from routers.jarvis import router as jarvis_router
from routers.extras import router as extras_router

app.include_router(auth_router)
app.include_router(pages_router)
app.include_router(system_router)
app.include_router(commercial_router)
app.include_router(usage_router)
app.include_router(proxy_router)
app.include_router(asset_router)
app.include_router(host_phone_router)
app.include_router(smart_chat_router)
app.include_router(agent_router)
app.include_router(jarvis_router)
app.include_router(extras_router)


# ── WebSocket（保留在主檔，因為需要 app 實例）──
from agent_logic import AgentManager

_last_progress: str = ""

async def broadcast_progress():
    """定期推播進度更新到所有 WebSocket 客戶端。"""
    global _last_progress
    while True:
        await asyncio.sleep(2)
        if not ws_clients:
            continue
        try:
            if PROGRESS_FILE.exists():
                data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8", errors="replace"))
                content = data.get("data", "")
                if content and content != _last_progress:
                    _last_progress = content
                    dead = set()
                    for ws in ws_clients:
                        try:
                            await ws.send_json({"type": "progress", "content": content})
                        except Exception:
                            dead.add(ws)
                    ws_clients.difference_update(dead)
        except Exception:
            pass


async def _agent_worker_loop():
    """背景 Agent 任務執行迴圈。"""
    while True:
        task_id = await agent_task_queue.get()
        t = agent_tasks.get(task_id)
        if not t or t.get("status") not in ("queued",):
            continue
        t["status"] = "running"
        t["updated_at"] = _now_iso()
        t.setdefault("logs", []).append(f"{_now_iso()} | task started")
        _save_agent_tasks()

        execution = t.get("execution", "llm")
        if execution == "host_script":
            job_type = t.get("job_type", "")
            args = t.get("args", {}) if isinstance(t.get("args"), dict) else {}
            _enqueue_host_job(task_id, job_type, args)
            t.setdefault("logs", []).append(f"{_now_iso()} | host job enqueued: {job_type}")
            _save_agent_tasks()
            for _ in range(180):
                await asyncio.sleep(2)
                result = _read_host_job_result(task_id)
                if result:
                    t["result"] = result.get("output", "") or json.dumps(result, ensure_ascii=False)[:2000]
                    t["status"] = "done" if result.get("ok") else "error"
                    if result.get("error"):
                        t["error"] = result["error"]
                    t["updated_at"] = _now_iso()
                    t.setdefault("logs", []).append(f"{_now_iso()} | host job completed: {t['status']}")
                    break
            else:
                t["status"] = "error"
                t["error"] = "host job timeout (6min)"
                t["updated_at"] = _now_iso()
                t.setdefault("logs", []).append(f"{_now_iso()} | host job timeout")
            _save_agent_tasks()
            continue

        try:
            provider_raw = t.get("provider", "cursor")
            provider_effective, _ = _provider_alias(provider_raw)
            objective = t.get("objective", "")
            context = t.get("context", "")
            messages = [
                {"role": "system", "content": "你是高效工程代理人。簡潔回答，先結論後步驟。"},
                {"role": "user", "content": f"任務：{objective}\n上下文：{context}" if context else f"任務：{objective}"},
            ]
            reply = await _remote_chat_reply(provider_effective, messages)
            result = _clean_model_output(reply) or "沒有產生有效輸出"
            t["result"] = result
            t["status"] = "done"
            t["updated_at"] = _now_iso()
            t.setdefault("logs", []).append(f"{_now_iso()} | task completed")
        except Exception as e:
            t["status"] = "error"
            t["error"] = str(e)
            t["updated_at"] = _now_iso()
            t.setdefault("logs", []).append(f"{_now_iso()} | task failed: {e}")
        finally:
            _save_agent_tasks()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.add(websocket)
    manager = AgentManager(gemini_service=gemini_ai, ollama_service=ollama_ai, max_turns=10)

    async def send_to_client(message):
        await websocket.send_json(message)

    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            user_input = request.get("text", "") or request.get("message", "")
            if not user_input:
                continue
            await manager.run(user_input, send_message=send_to_client)
    except WebSocketDisconnect:
        ws_clients.discard(websocket)
        logger.info("WebSocket client disconnected")
    except json.JSONDecodeError:
        try:
            await websocket.send_json({"type": "error", "content": "請傳送 JSON，含 text 或 message 欄位"})
        except Exception:
            pass
    except Exception as e:
        logger.error("WS error: %s\n%s", e, traceback.format_exc())
        try:
            await websocket.send_json({"type": "error", "content": f"系統異常: {str(e)}"})
        except Exception:
            pass


# ── 優雅關機 ──
def _graceful_shutdown(signum, frame):
    logger.info("Received shutdown signal, initiating graceful shutdown...")
    if sec_mw:
        sec_mw.request_shutdown()

signal.signal(signal.SIGTERM, _graceful_shutdown)
signal.signal(signal.SIGINT, _graceful_shutdown)


# ── 啟動任務 ──
@app.on_event("startup")
async def startup():
    logger.info("Brain Server v2.0 starting up (modular architecture)")
    _load_agent_tasks()
    asyncio.create_task(broadcast_progress())
    asyncio.create_task(_agent_worker_loop())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    PORT = int(os.environ.get("PORT", os.environ.get("BRAIN_WS_PORT", "8002")))
    uvicorn.run(app, host="0.0.0.0", port=PORT)

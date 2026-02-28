# -*- coding: utf-8 -*-
"""
築未科技 — Router 共用依賴
所有 Router 共用的狀態、工具函式、認證、AI 服務皆集中於此。
"""
import asyncio
import json
import logging
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse, PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field

# ── 結構化日誌 (Phase 1) ──
logger = logging.getLogger("zhewei.brain")

LOG_FORMAT = logging.Formatter(
    fmt='{"ts":"%(asctime)s","level":"%(levelname)s","module":"%(name)s","msg":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)


def setup_logging():
    """初始化結構化日誌。"""
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(LOG_FORMAT)
    if not root.handlers:
        root.addHandler(handler)


# ── 路徑 ──
ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

BRAIN_WORKSPACE = Path(os.environ.get("BRAIN_WORKSPACE", r"D:\brain_workspace"))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── 靜態檔案路徑 ──
STATIC_DIR = BRAIN_WORKSPACE / "static"
FALLBACK_STATIC = ROOT / "brain_workspace" / "static"
if (not STATIC_DIR.exists() or not (STATIC_DIR / "index.html").exists()) and FALLBACK_STATIC.exists():
    STATIC_DIR = FALLBACK_STATIC
STATIC_DIR.mkdir(parents=True, exist_ok=True)
if not (STATIC_DIR / "index.html").exists() and (FALLBACK_STATIC / "index.html").exists():
    shutil.copy2(str(FALLBACK_STATIC / "index.html"), str(STATIC_DIR / "index.html"))

# ── 重要路徑 ──
PROGRESS_FILE = BRAIN_WORKSPACE / "output" / "web_admin_progress.json"
if not PROGRESS_FILE.parent.exists():
    PROGRESS_FILE = ROOT / "brain_workspace" / "output" / "web_admin_progress.json"
AGENT_TASKS_FILE = ROOT / "reports" / "agent_tasks.json"
HOST_JOB_QUEUE_FILE = ROOT / "reports" / "agent_host_jobs.json"
HOST_JOB_RESULT_DIR = ROOT / "reports" / "agent_host_results"
PLAYBOOK_DIR = ROOT / "configs" / "business_playbooks"

# ── 認證 ──
ADMIN_USER = (os.environ.get("ADMIN_USER") or "").strip()
ADMIN_PASSWORD = (os.environ.get("ADMIN_PASSWORD") or "").strip()
SESSION_COOKIE = "zhewei_session"
_sessions: dict[str, str] = {}
REQUIRE_AUTH = os.environ.get("REQUIRE_AUTH", "false").lower() in ("true", "1", "yes")

import auth_manager


def _auth_configured() -> bool:
    return bool(ADMIN_USER and ADMIN_PASSWORD)


def _require_auth(request: Request):
    if not _auth_configured():
        return None
    sid = request.cookies.get(SESSION_COOKIE)
    if sid and sid in _sessions:
        return _sessions[sid]
    return RedirectResponse(url="/login", status_code=302)


def _extract_token(request: Request) -> dict | None:
    """從 Authorization header 或 cookie 提取並驗證 JWT token。"""
    auth_header = (request.headers.get("authorization") or "").strip()
    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.cookies.get("jarvis_token", "")
    if not token:
        return None
    return auth_manager.verify_token(token)


def _require_jwt(request: Request) -> dict:
    """驗證 JWT，未授權拋出 401。"""
    data = _extract_token(request)
    if not data:
        raise HTTPException(status_code=401, detail="未登入或 Token 已過期")
    if not auth_manager.is_authorized(data):
        raise HTTPException(status_code=403, detail="帳號尚未訂閱，請先完成訂閱")
    return data


def _require_admin(request: Request) -> dict:
    """要求 admin+ 權限。"""
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    return data


def _require_superadmin(request: Request) -> dict:
    """要求 superadmin 權限。"""
    data = _extract_token(request)
    if not data or data.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="僅超級管理員可執行此操作")
    return data


# ── AI 服務 ──
from ai_service import GeminiService, OllamaService, ClaudeService, SmartAIService

gemini_ai = GeminiService()
ollama_ai = OllamaService()
claude_ai = ClaudeService()
smart_ai = SmartAIService(gemini_service=gemini_ai, ollama_service=ollama_ai, claude_service=claude_ai)

# ── 共用狀態 ──
from fastapi import WebSocket
ws_clients: set[WebSocket] = set()
remote_sessions: dict[str, list[dict[str, str]]] = {}
agent_tasks: dict[str, dict] = {}
agent_task_queue: asyncio.Queue[str] = asyncio.Queue()
_last_progress: str = ""

# ── 安全中間件 ──
try:
    import security_middleware as sec_mw
except ImportError:
    sec_mw = None


# ── 工具函式 ──
def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _clean_model_output(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and obj.get("done") is True and "result" in obj:
            return str(obj.get("result") or "").strip()
    except Exception:
        pass
    return raw


def _provider_alias(provider: str) -> tuple[str, str]:
    p = (provider or "").strip().lower()
    if p == "cursor":
        return "gemini", "cursor->gemini"
    if p == "codebuddy":
        return "ollama", "codebuddy->ollama"
    if p in ("gemini", "claude", "ollama", "smart"):
        return p, p
    return "smart", "default->smart"


async def _remote_chat_reply(provider: str, messages: list[dict[str, str]]) -> str:
    if provider == "gemini":
        return await gemini_ai.chat(messages)
    if provider == "claude":
        text = await claude_ai.chat(messages)
        if "未設定 ANTHROPIC_API_KEY" in (text or "") or "Claude API 錯誤" in (text or ""):
            return await gemini_ai.chat(messages)
        return text
    if provider == "ollama":
        return await ollama_ai.chat(messages)
    return await smart_ai.chat(messages)


def _check_http_ok(url: str, timeout: int = 2) -> bool:
    try:
        import urllib.request
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= int(r.status) < 500
    except Exception:
        return False


def _check_tcp(host: str, port: int, timeout: int = 2) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def _check_any_tcp(candidates: list[tuple[str, int]], timeout: int = 2) -> bool:
    for host, port in candidates:
        if _check_tcp(host, port, timeout):
            return True
    return False


def _check_any_http(candidates: list[str], timeout: int = 2) -> bool:
    for url in candidates:
        if _check_http_ok(url, timeout):
            return True
    return False


# ── Agent Tasks 持久化 ──
def _save_agent_tasks() -> None:
    try:
        AGENT_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        AGENT_TASKS_FILE.write_text(
            json.dumps({"tasks": list(agent_tasks.values()), "updated": _now_iso()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        logger.exception("Failed to save agent tasks")


def _load_agent_tasks() -> None:
    if not AGENT_TASKS_FILE.exists():
        return
    try:
        raw = json.loads(AGENT_TASKS_FILE.read_text(encoding="utf-8", errors="ignore"))
        tasks = raw.get("tasks", [])
        if isinstance(tasks, list):
            for t in tasks:
                if isinstance(t, dict) and t.get("id"):
                    agent_tasks[str(t["id"])] = t
    except Exception:
        logger.exception("Failed to load agent tasks")


def _enqueue_host_job(task_id: str, job_type: str, args: dict | None = None) -> None:
    queue = []
    if HOST_JOB_QUEUE_FILE.exists():
        try:
            queue = json.loads(HOST_JOB_QUEUE_FILE.read_text(encoding="utf-8", errors="ignore")).get("jobs", [])
        except Exception:
            queue = []
    queue.append({
        "task_id": task_id, "job_type": job_type, "args": args or {},
        "status": "queued", "queued_at": _now_iso(),
    })
    HOST_JOB_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    HOST_JOB_QUEUE_FILE.write_text(
        json.dumps({"jobs": queue, "updated": _now_iso()}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _read_host_job_result(task_id: str) -> dict | None:
    p = HOST_JOB_RESULT_DIR / f"{task_id}.json"
    if not p.exists():
        return None
    try:
        obj = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


# ── 頁面輔助 ──
def serve_static_page(filename: str, require_login: bool = False, request: Request | None = None):
    """統一的靜態頁面服務函式。"""
    if require_login and request:
        auth = _require_auth(request)
        if isinstance(auth, RedirectResponse):
            return auth
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / filename
        if p.exists():
            return FileResponse(str(p))
    return PlainTextResponse(f"{filename} not found", status_code=404)


# ── Pydantic 請求模型 (Phase 2) ──
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    provider: str = Field(default="gemini", pattern=r"^(gemini|claude|ollama|smart|cursor|codebuddy|groq|deepseek)$")
    session_id: str = Field(default="default", max_length=100)
    max_turns: int = Field(default=10, ge=2, le=20)
    execute: bool = True


class TaskRequest(BaseModel):
    objective: str = Field(..., min_length=1, max_length=5000)
    provider: str = Field(default="cursor", max_length=50)
    context: str = Field(default="", max_length=10000)
    execution: str = Field(default="llm", pattern=r"^(llm|host_script)$")
    job_type: str = Field(default="", max_length=100)
    auto_run: bool = True


class AuthRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)
    email: str = Field(default="", max_length=200)


class ImageGenRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    filename: str = Field(default="jarvis_gen.png", max_length=200)


class LearnRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)
    answer: str = Field(default="", max_length=20000)
    source: str = Field(default="api", max_length=100)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    include_master: bool = True


# ── 全域錯誤處理中間件 (Phase 1) ──
async def global_exception_handler(request: Request, exc: Exception):
    """全域未捕獲錯誤 → 結構化日誌 + 安全回應。"""
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method, request.url.path, str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": "內部伺服器錯誤，請稍後重試"},
    )

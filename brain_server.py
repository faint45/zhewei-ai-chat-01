# -*- coding: utf-8 -*-
"""
築未科技 — 全功能伺服器大腦與管理網頁（預設端口 8002）
核心伺服器：調度所有 AI 代理人，即時將處理狀態推播至網頁。
靜態資源：D:\\brain_workspace\\static；根路由靜態對話頁；/ws 對話中樞。
認證：ADMIN_USER/ADMIN_PASSWORD 設定時，/admin、/chat 需登入；最高權限帳密存 .env。
web_admin_progress.json 定期讀取並經 WebSocket 廣播進度。
"""
import asyncio
import importlib.util
import json
import logging
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass
BRAIN_WORKSPACE = Path(os.environ.get("BRAIN_WORKSPACE", r"D:\brain_workspace"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from functools import wraps
from ai_service import GeminiService, OllamaService, ClaudeService, SmartAIService
from agent_logic import AgentManager
import auth_manager
import uvicorn

ADMIN_USER = (os.environ.get("ADMIN_USER") or "").strip()
ADMIN_PASSWORD = (os.environ.get("ADMIN_PASSWORD") or "").strip()
SESSION_COOKIE = "zhewei_session"
_sessions: dict[str, str] = {}

# 安全設置：是否強制認證（預設關閉以保持向後兼容）
REQUIRE_AUTH = os.environ.get("REQUIRE_AUTH", "false").lower() in ("true", "1", "yes")

app = FastAPI(title="Zhewei Brain Command Center", description="預設端口 8002，/admin、/chat 可選登入認證")

# 網域白名單（CORS）
origins = [
    "https://zhe-wei.net",
    "https://www.zhe-wei.net",
    "https://brain.zhe-wei.net",
    "https://jarvis.zhe-wei.net",
    "https://zhewei-ai-chat-01.pages.dev",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8002",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 安全中間件 ──
try:
    import security_middleware as sec_mw
except ImportError:
    sec_mw = None


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """全域限流 + 路由分類限流。"""
    if sec_mw:
        path = request.url.path
        # 靜態資源和健康檢查不限流
        if path.startswith("/static/") or path in ("/healthz", "/readyz", "/health"):
            return await call_next(request)
        client_ip = sec_mw.get_client_ip(request)
        category = sec_mw.classify_route(path, request.method)
        allowed, info = sec_mw.rate_limiter.is_allowed(client_ip, category)
        if not allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"error": "請求過於頻繁", "retry_after": info.get("retry_after", 60)},
                headers={"Retry-After": str(info.get("retry_after", 60))},
            )
    return await call_next(request)


@app.middleware("http")
async def auth_static_protected(request: Request, call_next):
    """保護 /static/index.html、/static/chat.html：需登入（若已設 ADMIN）。"""
    if _auth_configured() and request.url.path in ("/static/index.html", "/static/chat.html"):
        sid = request.cookies.get(SESSION_COOKIE)
        if not (sid and sid in _sessions):
            return RedirectResponse(url="/login", status_code=302)
    return await call_next(request)

# 三引擎 + 智慧路由
gemini_ai = GeminiService()
ollama_ai = OllamaService()  # 模型由 OLLAMA_MODEL / OLLAMA_CODER_MODEL 決定
claude_ai = ClaudeService()
smart_ai = SmartAIService(gemini_service=gemini_ai, ollama_service=ollama_ai, claude_service=claude_ai)

# WebSocket 連線集：供進度廣播
ws_clients: set[WebSocket] = set()
remote_sessions: dict[str, list[dict[str, str]]] = {}
agent_tasks: dict[str, dict] = {}
agent_task_queue: asyncio.Queue[str] = asyncio.Queue()
AGENT_TASKS_FILE = ROOT / "reports" / "agent_tasks.json"
HOST_JOB_QUEUE_FILE = ROOT / "reports" / "agent_host_jobs.json"
HOST_JOB_RESULT_DIR = ROOT / "reports" / "agent_host_results"
PLAYBOOK_DIR = ROOT / "configs" / "business_playbooks"
PROGRESS_FILE = BRAIN_WORKSPACE / "output" / "web_admin_progress.json"
if not PROGRESS_FILE.parent.exists():
    PROGRESS_FILE = ROOT / "brain_workspace" / "output" / "web_admin_progress.json"
_last_progress: str = ""


async def broadcast_progress():
    """定期讀取 web_admin_progress.json 並廣播至所有連線。"""
    global _last_progress
    while True:
        await asyncio.sleep(2)
        dead = set()
        try:
            if PROGRESS_FILE.exists():
                raw = PROGRESS_FILE.read_text(encoding="utf-8", errors="replace")
                data = json.loads(raw)
                content = data.get("data", "")
                if content and content != _last_progress:
                    _last_progress = content
                    msg = {"type": "progress", "content": content}
                    for ws in list(ws_clients):
                        try:
                            await ws.send_json(msg)
                        except Exception:
                            dead.add(ws)
        except (json.JSONDecodeError, OSError):
            pass
        for ws in dead:
            ws_clients.discard(ws)

# 掛載靜態檔案（D 槽 workspace）；本機開發時若專案內 brain_workspace/static 存在則優先使用
STATIC_DIR = BRAIN_WORKSPACE / "static"
FALLBACK_STATIC = ROOT / "brain_workspace" / "static"
if (not STATIC_DIR.exists() or not (STATIC_DIR / "index.html").exists()) and FALLBACK_STATIC.exists():
    STATIC_DIR = FALLBACK_STATIC
STATIC_DIR.mkdir(parents=True, exist_ok=True)
# 若 D 槽 static 無 index.html，從專案複製，避免 StaticFiles 回傳 404
if not (STATIC_DIR / "index.html").exists() and (FALLBACK_STATIC / "index.html").exists():
    import shutil
    shutil.copy2(str(FALLBACK_STATIC / "index.html"), str(STATIC_DIR / "index.html"))


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


def _resolve_voice_status() -> dict:
    whisper_bin = (os.environ.get("WHISPER_BIN") or "whisper").strip()
    piper_bin = (os.environ.get("PIPER_BIN") or "piper").strip()
    piper_model_path = (os.environ.get("PIPER_MODEL_PATH") or "").strip()
    if not piper_model_path:
        piper_model_path = str((Path(os.environ.get("ZHEWEI_MEMORY_ROOT", str(ROOT / "zhewei_memory"))) / "models" / "piper" / "zh_CN-huayan-medium.onnx").resolve())
    stt_provider = (os.environ.get("STT_PROVIDER") or "whisper").strip()
    whisper_cli_ok = bool(shutil.which(whisper_bin))
    faster_cli_ok = bool(shutil.which("faster-whisper"))
    whisper_module_ok = importlib.util.find_spec("whisper") is not None
    faster_module_ok = importlib.util.find_spec("faster_whisper") is not None
    whisper_required = stt_provider.lower() in {"whisper", "faster_whisper", "faster-whisper"}
    return {
        "stt_provider": stt_provider,
        "tts_provider": (os.environ.get("TTS_PROVIDER") or "piper").strip(),
        "whisper_bin": whisper_bin,
        "whisper_available": bool(whisper_cli_ok or whisper_module_ok or faster_cli_ok or faster_module_ok),
        "whisper_cli_available": whisper_cli_ok,
        "whisper_module_available": whisper_module_ok,
        "faster_whisper_available": bool(faster_cli_ok or faster_module_ok),
        "whisper_required": whisper_required,
        "piper_bin": piper_bin,
        "piper_available": bool(shutil.which(piper_bin)),
        "piper_model_path": piper_model_path,
        "piper_model_exists": Path(piper_model_path).exists(),
    }


def _check_any_tcp(candidates: list[tuple[str, int]], timeout: int = 2) -> bool:
    """嘗試多個 host:port 候選，任一成功即回傳 True。"""
    for host, port in candidates:
        if _check_tcp(host, port, timeout):
            return True
    return False


def _check_any_http(candidates: list[str], timeout: int = 2) -> bool:
    """嘗試多個 URL 候選，任一成功即回傳 True。"""
    for url in candidates:
        if _check_http_ok(url, timeout):
            return True
    return False


def _resolve_dependency_status() -> dict:
    qdrant_url = (os.environ.get("QDRANT_URL") or "").strip()
    weaviate_url = (os.environ.get("WEAVIATE_URL") or "").strip()
    n8n_url = (os.environ.get("N8N_URL") or "").strip()
    redis_host = (os.environ.get("REDIS_HOST") or "").strip()
    redis_port = int((os.environ.get("REDIS_PORT") or "6379").strip() or "6379")
    postgres_host = (os.environ.get("POSTGRES_HOST") or "").strip()
    postgres_port = int((os.environ.get("POSTGRES_PORT") or "5432").strip() or "5432")

    # Qdrant: 環境變數 > Docker 容器名 > host.docker.internal > localhost
    qdrant_candidates = [u for u in [
        qdrant_url,
        "http://zhewei-qdrant:6333/collections",
        "http://host.docker.internal:6333/collections",
        "http://localhost:6333/collections",
    ] if u]

    # Weaviate: 環境變數 > Docker 容器名 > host.docker.internal > localhost
    weaviate_candidates = [u for u in [
        weaviate_url,
        "http://weaviate:8080/v1/.well-known/ready",
        "http://host.docker.internal:8080/v1/.well-known/ready",
        "http://localhost:8080/v1/.well-known/ready",
    ] if u]

    # n8n: 環境變數 > host.docker.internal > localhost
    n8n_candidates = [u for u in [
        n8n_url,
        "http://host.docker.internal:5678",
        "http://localhost:5678",
    ] if u]

    # Redis: 環境變數 > Docker 容器名 > host.docker.internal > localhost
    redis_candidates = [
        (h, redis_port) for h in ([redis_host] if redis_host else []) +
        ["redis", "host.docker.internal", "localhost"]
        if h
    ]

    # PostgreSQL: 環境變數 > Docker 容器名 > host.docker.internal > localhost
    pg_candidates = [
        (h, postgres_port) for h in ([postgres_host] if postgres_host else []) +
        ["db_postgres", "db", "host.docker.internal", "localhost"]
        if h
    ]

    return {
        "qdrant": _check_any_http(qdrant_candidates),
        "weaviate": _check_any_http(weaviate_candidates),
        "n8n": _check_any_http(n8n_candidates),
        "redis": _check_any_tcp(redis_candidates),
        "postgres": _check_any_tcp(pg_candidates),
    }


def _mode_from_dependencies(deps: dict) -> str:
    # 只要有任一開發服務在線，就視為 dev
    dev_signals = ("n8n", "weaviate", "redis", "postgres")
    if any(bool(deps.get(k, False)) for k in dev_signals):
        return "dev"
    return "daily"


def _dependency_display(deps: dict, mode: str) -> dict:
    dev_only = {"n8n", "weaviate", "redis", "postgres"}
    out: dict[str, dict] = {}
    for k, v in deps.items():
        val = bool(v)
        if mode == "daily" and k in dev_only:
            out[k] = {"status": "skipped", "ok": True, "value": val}
        else:
            out[k] = {"status": "ok" if val else "fail", "ok": val, "value": val}
    return out


def _provider_alias(provider: str) -> tuple[str, str]:
    p = (provider or "").strip().lower()
    # cursor / codebuddy 為代理通道名稱，底層映射到目前可用引擎
    if p == "cursor":
        return "gemini", "cursor->gemini"
    if p == "codebuddy":
        return "ollama", "codebuddy->ollama"
    if p in ("gemini", "claude", "ollama", "smart"):
        return p, p
    return "smart", "default->smart"


def _clean_model_output(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    # 對齊 ai_service 的 JSON 錯誤回傳格式
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and obj.get("done") is True and "result" in obj:
            return str(obj.get("result") or "").strip()
    except Exception:
        pass
    return raw


async def _remote_chat_reply(provider: str, messages: list[dict[str, str]]) -> str:
    if provider == "gemini":
        return await gemini_ai.chat(messages)
    if provider == "claude":
        text = await claude_ai.chat(messages)
        # Claude key 未設或 API 異常時，自動 fallback，避免空回應
        if "未設定 ANTHROPIC_API_KEY" in (text or "") or "Claude API 錯誤" in (text or ""):
            return await gemini_ai.chat(messages)
        return text
    if provider == "ollama":
        return await ollama_ai.chat(messages)
    # 預設：智慧路由（根據任務複雜度自動選擇最佳引擎）
    return await smart_ai.chat(messages)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _save_agent_tasks() -> None:
    try:
        AGENT_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        AGENT_TASKS_FILE.write_text(
            json.dumps({"tasks": list(agent_tasks.values()), "updated": _now_iso()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


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
        pass


def _enqueue_host_job(task_id: str, job_type: str, args: dict | None = None) -> None:
    queue = []
    if HOST_JOB_QUEUE_FILE.exists():
        try:
            queue = json.loads(HOST_JOB_QUEUE_FILE.read_text(encoding="utf-8", errors="ignore")).get("jobs", [])
        except Exception:
            queue = []
    queue.append(
        {
            "task_id": task_id,
            "job_type": job_type,
            "args": args or {},
            "status": "queued",
            "queued_at": _now_iso(),
        }
    )
    HOST_JOB_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    HOST_JOB_QUEUE_FILE.write_text(json.dumps({"jobs": queue, "updated": _now_iso()}, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_host_job_result(task_id: str) -> dict | None:
    p = HOST_JOB_RESULT_DIR / f"{task_id}.json"
    if not p.exists():
        return None
    try:
        obj = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _semantic_route_plan(text: str) -> list[dict]:
    q = (text or "").strip().lower()
    plan: list[dict] = []
    if not q:
        return plan
    if "line" in q and any(k in q for k in ("開", "open", "啟動")):
        plan.append(
            {
                "title": "開啟 LINE",
                "execution": "host_script",
                "job_type": "line_open",
                "args": {},
            }
        )
    line_read_needed = any(k in q for k in ("最後一則", "最後一条", "urgent", "緊急", "修改", "message", "訊息", "消息", "念", "重點"))
    if "line" in q and line_read_needed:
        plan.append(
            {
                "title": "VLM 判讀 LINE 畫面",
                "execution": "host_script",
                "job_type": "line_read_vlm",
                "args": {
                    "question": "業主訊息重點、最後一則內容、是否有緊急或修改？請輸出 JSON。",
                    "keywords": ["緊急", "修改", "urgent", "change"],
                },
            }
        )
    # 僅當非「念 Line 訊息」類請求時，才加 Smart GUI（避免誤觸發）
    if "line" not in q or not line_read_needed:
        plan.append(
            {
                "title": "Smart GUI 自動操作",
                "execution": "host_script",
                "job_type": "smart_gui_agent",
                "args": {"instruction": text, "execute": True, "max_actions": 8, "retry_count": 3},
            }
        )
    return plan


def _list_business_playbooks() -> list[dict]:
    items: list[dict] = []
    if not PLAYBOOK_DIR.exists():
        return items
    for p in sorted(PLAYBOOK_DIR.glob("*.json")):
        if p.name.startswith("_"):
            continue
        try:
            obj = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        pid = str(obj.get("id") or p.stem).strip()
        name = str(obj.get("name") or pid).strip()
        desc = str(obj.get("description") or "").strip()
        steps = obj.get("steps", [])
        items.append(
            {
                "id": pid,
                "name": name,
                "description": desc,
                "step_count": len(steps) if isinstance(steps, list) else 0,
                "path": str(p),
            }
        )
    return items


def _load_business_playbook(playbook_id: str) -> dict | None:
    pid = str(playbook_id or "").strip()
    if not pid:
        return None
    direct = PLAYBOOK_DIR / f"{pid}.json"
    candidates = [direct] if direct.exists() else list(PLAYBOOK_DIR.glob("*.json"))
    for p in candidates:
        try:
            obj = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        rid = str(obj.get("id") or p.stem).strip()
        if rid == pid:
            return obj
    return None


def _build_task_from_step(route_id: str, idx: int, total: int, route_context: str, step: dict, auto_run: bool) -> dict:
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    title = str(step.get("title") or f"step-{idx}").strip()
    execution = str(step.get("execution") or "host_script").strip().lower()
    job_type = str(step.get("job_type") or "").strip().lower()
    provider = str(step.get("provider") or "desktop").strip().lower()
    context = str(step.get("context") or route_context).strip()
    args = step.get("args", {})
    if not isinstance(args, dict):
        args = {}
    return {
        "id": task_id,
        "route_id": route_id,
        "route_step": idx,
        "route_total": total,
        "objective": f"[{idx}/{total}] {title}",
        "provider": provider,
        "execution": execution if execution in {"llm", "host_script"} else "host_script",
        "job_type": job_type,
        "status": "queued" if auto_run else "pending",
        "context": context,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "result": "",
        "logs": [f"{_now_iso()} | playbook task created"],
        "args": args,
    }


async def _agent_worker_loop() -> None:
    while True:
        task_id = await agent_task_queue.get()
        t = agent_tasks.get(task_id)
        if not t:
            continue
        if t.get("status") not in {"queued", "pending"}:
            continue
        t["status"] = "running"
        t["updated_at"] = _now_iso()
        t.setdefault("logs", []).append(f"{_now_iso()} | task started")
        _save_agent_tasks()
        try:
            execution = str(t.get("execution") or "llm").strip().lower()
            if execution == "host_script":
                job_type = str(t.get("job_type") or "pyautogui_demo").strip().lower()
                job_args = {"objective": t.get("objective", "")}
                if isinstance(t.get("args"), dict):
                    job_args.update(t.get("args") or {})
                _enqueue_host_job(task_id, job_type, job_args)
                t.setdefault("logs", []).append(f"{_now_iso()} | host job queued: {job_type}")
                _save_agent_tasks()
                # 等待主機監控腳本回寫結果（最多 180 秒）
                found = None
                for _ in range(90):
                    await asyncio.sleep(2)
                    found = _read_host_job_result(task_id)
                    if found:
                        break
                if not found:
                    t["status"] = "error"
                    t["error"] = "host job timeout (請確認 scripts/start_runtime_monitor.bat 正在執行)"
                    t["updated_at"] = _now_iso()
                    t.setdefault("logs", []).append(f"{_now_iso()} | host job timeout")
                    _save_agent_tasks()
                    continue
                ok = bool(found.get("ok", False))
                t["status"] = "done" if ok else "error"
                t["result"] = str(found.get("result") or found.get("output") or "").strip()
                if not ok:
                    t["error"] = str(found.get("error") or "host job failed")
                t["updated_at"] = _now_iso()
                t.setdefault("logs", []).append(f"{_now_iso()} | host job finished: {'ok' if ok else 'error'}")
                _save_agent_tasks()
                continue

            provider_effective, provider_mapping = _provider_alias(str(t.get("provider", "cursor")))
            t["provider_effective"] = provider_effective
            t["provider_mapping"] = provider_mapping
            objective = str(t.get("objective") or "").strip()
            context = str(t.get("context") or "").strip()

            # 查詢統一知識庫注入上下文
            kb_context = ""
            try:
                import sys as _sys
                _sys.path.insert(0, str(ROOT / "Jarvis_Training"))
                from local_learning_system import search as _kb_search
                _hits = _kb_search(objective, top_k=5)
                if _hits:
                    _parts = []
                    for _h in _hits:
                        _d = _h.get("distance")
                        _sim = f"{1-_d:.2f}" if _d is not None else "?"
                        _parts.append(f"({_sim}) {_h.get('question','')[:80]}\n{_h.get('answer','')[:300]}")
                    kb_context = "\n\n".join(_parts)
            except Exception:
                pass

            system_prompt = "你是執行型工程代理人，輸出需包含：1) 結論 2) 依據 3) 行動建議。請優先根據【知識庫】內容回答。"
            user_content = f"任務目標：{objective}\n\n補充上下文：{context or '無'}"
            if kb_context:
                user_content = f"任務目標：{objective}\n\n【知識庫相關資料】\n{kb_context}\n\n補充上下文：{context or '無'}"
                t.setdefault("logs", []).append(f"{_now_iso()} | KB injected {len(kb_context)} chars")

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
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


@app.get("/static/index.html")
async def get_static_index():
    """優先回傳管理介面，避免 StaticFiles 路徑問題導致 404。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "index.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("index.html not found", status_code=404)


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── 男神拍拍 PWA 路由 ──
PHOTO_APP_DIR = ROOT / "photo_app"
if PHOTO_APP_DIR.exists():
    app.mount("/photo_app", StaticFiles(directory=str(PHOTO_APP_DIR)), name="photo_app")

    @app.get("/photo-app", response_class=RedirectResponse)
    async def redirect_photo_app():
        return RedirectResponse(url="/photo_app/index.html", status_code=302)

    @app.get("/photo-app/", response_class=RedirectResponse)
    async def redirect_photo_app_slash():
        return RedirectResponse(url="/photo_app/index.html", status_code=302)


def _auth_configured() -> bool:
    return bool(ADMIN_USER and ADMIN_PASSWORD)


def _require_auth(request: Request):
    """未登入時導向 /login；ADMIN_USER/ADMIN_PASSWORD 未設時不強制登入。"""
    if not _auth_configured():
        return None
    sid = request.cookies.get(SESSION_COOKIE)
    if sid and sid in _sessions:
        return _sessions[sid]
    return RedirectResponse(url="/login", status_code=302)


@app.get("/")
async def get_index():
    return RedirectResponse(url="/jarvis-login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request, err: str = ""):
    """登入頁；已登入則導向 /admin。"""
    if _auth_configured():
        sid = request.cookies.get(SESSION_COOKIE)
        if sid and sid in _sessions:
            return RedirectResponse(url="/admin", status_code=302)
    err_msg = '<p class="text-rose-400 text-sm text-center mb-2">帳號或密碼錯誤</p>' if err else ""
    html = f"""<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>築未科技 — 登入</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-900 text-slate-100 min-h-screen flex items-center justify-center p-4">
<div class="w-full max-w-sm rounded-2xl bg-slate-800/80 border border-slate-600 shadow-xl p-6">
<h1 class="text-xl font-bold text-center text-blue-400 mb-6">築未科技 系統登入</h1>
{err_msg}
<form method="post" action="/login" class="space-y-4">
<input type="text" name="username" placeholder="帳號" required class="w-full px-4 py-3 rounded-lg bg-slate-700 border border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-transparent">
<input type="password" name="password" placeholder="密碼" required class="w-full px-4 py-3 rounded-lg bg-slate-700 border border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-transparent">
<button type="submit" class="w-full py-3 rounded-lg bg-blue-600 hover:bg-blue-500 font-medium transition">登入</button>
</form>
<p class="text-xs text-slate-400 mt-4 text-center">最高權限帳密請存於 .env（ADMIN_USER / ADMIN_PASSWORD）</p>
</div></body></html>"""
    return HTMLResponse(html)


@app.post("/login")
async def post_login(request: Request, username: str = Form(""), password: str = Form("")):
    """驗證帳密後設 session cookie 並導向 /admin。"""
    if not _auth_configured():
        return RedirectResponse(url="/admin", status_code=302)
    if username == ADMIN_USER and password == ADMIN_PASSWORD:
        sid = secrets.token_urlsafe(32)
        _sessions[sid] = username
        r = RedirectResponse(url="/admin", status_code=302)
        r.set_cookie(key=SESSION_COOKIE, value=sid, max_age=24 * 3600, httponly=True, samesite="lax")
        return r
    return RedirectResponse(url="/login?err=1", status_code=302)


@app.get("/logout")
async def logout():
    """清除 session 並導向 /login。"""
    r = RedirectResponse(url="/login", status_code=302)
    r.delete_cookie(SESSION_COOKIE)
    return r


@app.get("/admin")
async def get_admin(request: Request):
    """管理介面入口：重導到 Jarvis 主介面。"""
    return RedirectResponse(url="/jarvis", status_code=302)


@app.get("/chat")
async def get_chat(request: Request):
    """手機版對話頁：/static/chat.html；需登入（若已設 ADMIN_USER/PASSWORD）。"""
    auth = _require_auth(request)
    if isinstance(auth, RedirectResponse):
        return auth
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "chat.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("chat.html not found", status_code=404)


@app.get("/jarvis")
async def get_jarvis(request: Request):
    """Jarvis AI 助理對話頁：需 JWT 授權，未登入導向登入頁。"""
    # 檢查 cookie 或 query 中的 token
    token = request.cookies.get("jarvis_token") or request.query_params.get("token") or ""
    if not token:
        # 前端用 localStorage，此處僅做 server-side fallback
        pass
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "jarvis.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("jarvis.html not found", status_code=404)


@app.get("/jarvis-login")
async def get_jarvis_login():
    """Jarvis 登入頁。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "jarvis-login.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("jarvis-login.html not found", status_code=404)


@app.get("/jarvis-register")
async def get_jarvis_register():
    """Jarvis 註冊 & 訂閱頁。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "jarvis-register.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("jarvis-register.html not found", status_code=404)


@app.get("/admin-commercial")
async def get_admin_commercial():
    """商用管理後台。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "admin_commercial.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("admin_commercial.html not found", status_code=404)


@app.get("/smart-remote")
async def get_smart_remote():
    """智慧遙控手機端頁面。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "smart-remote.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("smart-remote.html not found", status_code=404)


@app.get("/")
async def root_redirect():
    """首頁重新導向至對話遙控介面。"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/chat-remote", status_code=302)


@app.get("/chat-remote")
async def get_chat_remote():
    """對話遙控頁面。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "chat-remote.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("chat-remote.html not found", status_code=404)


# ── JWT 認證 API ──────────────────────────────────────────
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


@app.post("/api/auth/register")
async def api_auth_register(request: Request):
    """用戶註冊。"""
    payload = await request.json()
    username = str((payload or {}).get("username", "")).strip()
    password = str((payload or {}).get("password", "")).strip()
    email = str((payload or {}).get("email", "")).strip()
    return auth_manager.register_user(username, password, email)


@app.post("/api/auth/login")
async def api_auth_login(request: Request):
    """用戶登入，回傳 JWT Token。"""
    payload = await request.json()
    username = str((payload or {}).get("username", "")).strip()
    password = str((payload or {}).get("password", "")).strip()
    result = auth_manager.login_user(username, password)
    return result


@app.post("/api/auth/subscribe")
async def api_auth_subscribe(request: Request):
    """確認訂閱（註冊後需訂閱才能使用系統）。"""
    payload = await request.json()
    username = str((payload or {}).get("username", "")).strip()
    plan = str((payload or {}).get("plan", "basic")).strip()
    if not username:
        raise HTTPException(status_code=400, detail="username is required")
    return auth_manager.confirm_subscription(username, plan)


@app.get("/api/auth/me")
async def api_auth_me(request: Request):
    """取得當前登入用戶資訊。"""
    data = _extract_token(request)
    if not data:
        return {"ok": False, "error": "未登入"}
    user = auth_manager.get_user_info(data.get("sub", ""))
    if not user:
        return {"ok": False, "error": "用戶不存在"}
    return {"ok": True, "user": user}


@app.get("/api/auth/users")
async def api_auth_users(request: Request):
    """列出所有用戶（僅 superadmin/admin）。"""
    data = _extract_token(request)
    if not data:
        raise HTTPException(status_code=401, detail="未登入")
    role = data.get("role", "")
    if role not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    users = auth_manager.list_users(role)
    return {"ok": True, "users": users}


@app.post("/api/auth/activate")
async def api_auth_activate(request: Request):
    """管理員手動啟用用戶訂閱。"""
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    payload = await request.json()
    user_id = str((payload or {}).get("user_id", "")).strip()
    plan = str((payload or {}).get("plan", "basic")).strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    return auth_manager.activate_subscription(user_id, plan)


@app.get("/api/auth/logout")
async def api_auth_logout():
    """登出（前端清除 token 即可，此端點僅供語義完整性）。"""
    return {"ok": True, "message": "已登出，請清除本地 Token"}


# ── 用量計量 API ──────────────────────────────────────────────
try:
    import usage_metering
except ImportError:
    usage_metering = None


@app.get("/api/usage/today")
async def api_usage_today():
    """今日用量摘要（快速概覽）。"""
    if not usage_metering:
        return {"ok": False, "error": "用量計量模組未安裝"}
    return {"ok": True, **usage_metering.get_today_summary()}


@app.get("/api/usage/me")
async def api_usage_me(request: Request, days: int = 30):
    """查詢當前用戶近 N 天用量。"""
    if not usage_metering:
        return {"ok": False, "error": "用量計量模組未安裝"}
    data = _extract_token(request)
    uid = (data or {}).get("sub", "anonymous")
    return {"ok": True, **usage_metering.get_user_usage(uid, days)}


@app.get("/api/usage/quota")
async def api_usage_quota(request: Request):
    """檢查當前用戶本月配額。"""
    if not usage_metering:
        return {"ok": False, "error": "用量計量模組未安裝"}
    data = _extract_token(request)
    uid = (data or {}).get("sub", "anonymous")
    plan = (data or {}).get("sub_status", "free")
    # 從用戶資料取得訂閱方案
    user_info = auth_manager.get_user_info(uid) if uid != "anonymous" else None
    if user_info:
        plan = user_info.get("subscription_plan", "") or "free"
    return {"ok": True, **usage_metering.check_quota(uid, plan)}


@app.get("/api/usage/system")
async def api_usage_system(request: Request, days: int = 30):
    """系統整體用量（僅 superadmin/admin）。"""
    if not usage_metering:
        return {"ok": False, "error": "用量計量模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    return {"ok": True, **usage_metering.get_system_usage(days)}


# ── AI 用量追蹤 API ──
try:
    from ai_usage_tracker import usage_tracker
    USAGE_TRACKER_AVAILABLE = True
except ImportError:
    USAGE_TRACKER_AVAILABLE = False


@app.get("/api/usage/today")
async def api_usage_today_v2():
    """今日 AI 用量摘要（新版）。"""
    if not USAGE_TRACKER_AVAILABLE:
        return {"ok": False, "error": "用量追蹤模組未安裝"}
    stats = usage_tracker.get_today_stats()
    return {"ok": True, **stats}


@app.get("/api/usage/weekly")
async def api_usage_weekly():
    """本週 AI 用量統計。"""
    if not USAGE_TRACKER_AVAILABLE:
        return {"ok": False, "error": "用量追蹤模組未安裝"}
    stats = usage_tracker.get_weekly_stats()
    return {"ok": True, **stats}


@app.get("/api/usage/report")
async def api_usage_report():
    """取得今日用量報告。"""
    if not USAGE_TRACKER_AVAILABLE:
        return {"ok": False, "error": "用量追蹤模組未安裝"}
    report = usage_tracker.export_report()
    return {"ok": True, "report": report}


# ── 商用 API：License 管理 + 知識庫同步 + 遠端加強 ─────────────
try:
    import license_manager
except ImportError:
    license_manager = None

try:
    import kb_snapshot
except ImportError:
    kb_snapshot = None


# ── License 管理 API ──

@app.get("/api/commercial/license/validate")
async def api_license_validate():
    """驗證當前 License 狀態。"""
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    return {"ok": True, **license_manager.validate_license()}


@app.post("/api/commercial/license/activate")
async def api_license_activate(body: dict):
    """啟用 License（客戶端安裝時呼叫）。"""
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    data = body.get("license_data", "")
    if not data:
        raise HTTPException(400, "license_data is required")
    return license_manager.activate_license(data, bind_device=body.get("bind_device", True))


@app.get("/api/commercial/license/offline-check")
async def api_license_offline_check():
    """檢查離線寬限期。"""
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    return license_manager.check_offline_grace()


@app.post("/api/commercial/license/online-verify")
async def api_license_online_verify():
    """連線驗證（更新離線計時器）。"""
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    result = license_manager.validate_license()
    if result.get("valid"):
        license_manager.update_online_check()
        return {"ok": True, "message": "連線驗證成功", **result}
    return {"ok": False, **result}


@app.post("/api/commercial/license/generate")
async def api_license_generate(request: Request, body: dict):
    """生成 License（僅 superadmin）。"""
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") != "superadmin":
        raise HTTPException(403, "僅超級管理員可生成 License")
    return license_manager.generate_license(
        customer_name=body.get("customer_name", ""),
        tier=body.get("tier", "professional"),
        duration_days=body.get("duration_days", 365),
        device_fingerprint=body.get("device_fingerprint", ""),
        max_devices=body.get("max_devices", 1),
        notes=body.get("notes", ""),
    )


@app.get("/api/commercial/license/list")
async def api_license_list(request: Request):
    """列出所有 License（僅 admin+）。"""
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(403, "權限不足")
    return {"ok": True, "licenses": license_manager.list_licenses()}


@app.post("/api/commercial/license/revoke")
async def api_license_revoke(request: Request, body: dict):
    """撤銷 License（僅 superadmin）。"""
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") != "superadmin":
        raise HTTPException(403, "僅超級管理員可撤銷 License")
    lid = body.get("license_id", "")
    if not lid:
        raise HTTPException(400, "license_id is required")
    return license_manager.revoke_license(lid)


@app.get("/api/commercial/device-info")
async def api_device_info():
    """取得裝置指紋資訊。"""
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    import platform
    return {
        "ok": True,
        "fingerprint": license_manager.get_device_fingerprint(),
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
    }


@app.get("/api/commercial/features")
async def api_commercial_features(request: Request):
    """取得當前用戶可用功能（根據 License + 角色）。"""
    if not license_manager:
        return {"ok": False, "error": "License 模組未安裝"}
    data = _extract_token(request)
    return {"ok": True, **license_manager.get_user_features(data or {})}


# ── 知識庫同步 API ──

@app.get("/api/commercial/kb/snapshot-info")
async def api_kb_snapshot_info():
    """取得知識庫快照版本資訊。"""
    if not kb_snapshot:
        return {"ok": False, "error": "知識庫快照模組未安裝"}
    return {"ok": True, **kb_snapshot.get_snapshot_info()}


@app.get("/api/commercial/kb/snapshots")
async def api_kb_snapshots():
    """列出所有快照檔案。"""
    if not kb_snapshot:
        return {"ok": False, "error": "知識庫快照模組未安裝"}
    return {"ok": True, "snapshots": kb_snapshot.list_snapshots()}


@app.post("/api/commercial/kb/export")
async def api_kb_export(request: Request, body: dict):
    """匯出知識庫快照（僅 admin+）。"""
    if not kb_snapshot:
        return {"ok": False, "error": "知識庫快照模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(403, "權限不足")
    return kb_snapshot.export_snapshot(
        collection_name=body.get("collection", ""),
        include_embeddings=body.get("include_embeddings", True),
        compress=body.get("compress", True),
        max_items=body.get("max_items", -1),
    )


@app.post("/api/commercial/kb/export-delta")
async def api_kb_export_delta(request: Request, body: dict):
    """差量匯出（僅 admin+）。"""
    if not kb_snapshot:
        return {"ok": False, "error": "知識庫快照模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(403, "權限不足")
    since = body.get("since_version", 0)
    if not since:
        raise HTTPException(400, "since_version is required")
    return kb_snapshot.export_delta(
        since_version=since,
        collection_name=body.get("collection", ""),
    )


@app.post("/api/commercial/kb/import")
async def api_kb_import(body: dict):
    """匯入知識庫快照（客戶端呼叫）。"""
    if not kb_snapshot:
        return {"ok": False, "error": "知識庫快照模組未安裝"}
    snapshot_file = body.get("snapshot_file", "")
    if not snapshot_file:
        raise HTTPException(400, "snapshot_file is required")
    return kb_snapshot.import_snapshot(
        snapshot_file=snapshot_file,
        collection_name=body.get("collection", ""),
        skip_existing=body.get("skip_existing", True),
    )


@app.get("/api/commercial/kb/check-update")
async def api_kb_check_update(client_version: int = 0):
    """客戶端檢查是否有知識庫更新。"""
    if not kb_snapshot:
        return {"ok": False, "error": "知識庫快照模組未安裝"}
    info = kb_snapshot.get_snapshot_info()
    server_version = info.get("current_version", 0)
    has_update = server_version > client_version
    return {
        "ok": True,
        "has_update": has_update,
        "server_version": server_version,
        "client_version": client_version,
        "versions_behind": server_version - client_version if has_update else 0,
    }


# ── 遠端加強 API（客戶端呼叫，帶 License 驗證 + 配額檢查）──

@app.post("/api/commercial/remote-enhance")
async def api_remote_enhance(request: Request, body: dict):
    """
    遠端加強推理（客戶端本地不夠時呼叫）。
    - 驗證 License
    - 檢查配額
    - 使用伺服器端 AI（Gemini/Claude）推理
    - 記錄用量
    """
    # 1. 驗證 License
    if license_manager:
        lic = license_manager.validate_license()
        if not lic.get("valid"):
            return {"ok": False, "error": "License 無效或已過期", "need_license": True}
        if lic.get("remote_calls_per_month", 0) == 0:
            return {"ok": False, "error": "免費版不支援遠端加強，請升級方案"}

    # 2. 檢查配額
    token_data = _extract_token(request)
    uid = (token_data or {}).get("sub", "anonymous")
    if usage_metering:
        plan = "free"
        if token_data:
            user_info = auth_manager.get_user_info(uid) if uid != "anonymous" else None
            if user_info:
                plan = user_info.get("subscription_plan", "") or "free"
        quota = usage_metering.check_quota(uid, plan)
        if not quota.get("allowed", True):
            return {"ok": False, "error": "本月配額已用完", "quota": quota}

    # 3. 執行遠端推理
    messages = body.get("messages", [])
    task_type = body.get("task_type", "think")
    if not messages:
        raise HTTPException(400, "messages is required")

    import time as _time
    start = _time.time()
    try:
        result = await smart_ai.generate(
            messages[-1].get("content", "") if messages else "",
            context="\n".join(m.get("content", "") for m in messages[:-1]) if len(messages) > 1 else "",
        )
        duration_ms = int((_time.time() - start) * 1000)

        # 4. 記錄用量
        if usage_metering:
            usage_metering.record_usage(
                provider=result.get("provider", "unknown"),
                model=result.get("model", "unknown"),
                input_tokens=usage_metering.estimate_tokens(str(messages)),
                output_tokens=usage_metering.estimate_tokens(result.get("text", "")),
                duration_ms=duration_ms,
                user_id=uid,
                task_type=task_type,
            )

        return {
            "ok": True,
            "text": result.get("text", ""),
            "provider": result.get("provider", ""),
            "model": result.get("model", ""),
            "duration_ms": duration_ms,
        }
    except Exception as e:
        if usage_metering:
            usage_metering.record_usage(
                provider="error", model="", duration_ms=int((_time.time() - start) * 1000),
                success=False, error_msg=str(e)[:200], user_id=uid, task_type=task_type,
            )
        return {"ok": False, "error": str(e)[:300]}


@app.get("/api/ai/task-planner-test")
async def api_ai_task_planner_test(request: Request, q: str = "你好"):
    """測試 TaskPlanner 分類結果（不實際呼叫模型）。"""
    try:
        from ai_modules.task_planner import planner
        plan = planner.plan([{"role": "user", "content": q}])
        return {
            "query": q, "level": plan.level, "label": plan.label,
            "domain": plan.domain, "model_chain": plan.model_chain,
            "quality_gate": plan.quality_gate, "escalation": plan.escalation,
            "thinking": plan.thinking, "system_prompt": plan.system_prompt[:100] if plan.system_prompt else "",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


@app.get("/api/ai/training-analysis")
async def api_ai_training_analysis(request: Request):
    """分析任務日誌，找出適合微調的高頻領域。"""
    try:
        from ai_modules.task_planner import training_analyzer
        return training_analyzer.analyze()
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


@app.get("/api/commercial/system-status")
async def api_commercial_system_status(request: Request):
    """商用系統完整狀態（License + 用量 + 同步 + 裝置）。"""
    status = {}

    # License
    if license_manager:
        lic = license_manager.validate_license()
        offline = license_manager.check_offline_grace()
        status["license"] = {
            "valid": lic.get("valid", False),
            "tier": lic.get("tier", "free"),
            "tier_name": lic.get("tier_name", ""),
            "customer_name": lic.get("customer_name", ""),
            "days_remaining": lic.get("days_remaining", 0),
            "expires_at": lic.get("expires_at", ""),
        }
        status["offline"] = {
            "ok": offline.get("ok", False),
            "days_offline": offline.get("days_offline", 0),
            "grace_remaining": offline.get("days_remaining_offline", 0),
        }
    else:
        status["license"] = {"valid": False, "tier": "free"}
        status["offline"] = {"ok": False}

    # 用量
    if usage_metering:
        status["usage_today"] = usage_metering.get_today_summary()
        token_data = _extract_token(request)
        uid = (token_data or {}).get("sub", "anonymous")
        plan = "free"
        if token_data and uid != "anonymous":
            user_info = auth_manager.get_user_info(uid)
            if user_info:
                plan = user_info.get("subscription_plan", "") or "free"
        status["quota"] = usage_metering.check_quota(uid, plan)
    else:
        status["usage_today"] = {}
        status["quota"] = {}

    # KB 同步
    if kb_snapshot:
        status["kb_version"] = kb_snapshot.get_snapshot_info()
    else:
        status["kb_version"] = {"current_version": 0}

    return {"ok": True, **status}


# ── 多租戶管理 API ────────────────────────────────────────────
try:
    import tenant_manager
except ImportError:
    tenant_manager = None


@app.get("/api/tenants")
async def api_list_tenants(request: Request):
    """列出所有租戶（僅 superadmin/admin）。"""
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    try:
        import db_postgres
        tenants = db_postgres.list_tenants()
        return {"ok": True, "tenants": tenants, "count": len(tenants)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/tenants")
async def api_create_tenant(request: Request):
    """建立租戶（僅 superadmin/admin）。"""
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    payload = await request.json()
    name = str((payload or {}).get("name", "")).strip()
    slug = str((payload or {}).get("slug", "")).strip()
    plan = str((payload or {}).get("plan", "free")).strip()
    if not name or not slug:
        raise HTTPException(status_code=400, detail="name and slug are required")
    try:
        import db_postgres
        result = db_postgres.create_tenant(name, slug, plan)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/tenants/{tenant_slug}/stats")
async def api_tenant_stats(tenant_slug: str, request: Request):
    """取得租戶知識庫統計。"""
    if not tenant_manager:
        return {"ok": False, "error": "租戶模組未安裝"}
    try:
        return tenant_manager.tenant_stats(tenant_slug)
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/tenants/{tenant_slug}/kb-quota")
async def api_tenant_kb_quota(tenant_slug: str, request: Request):
    """檢查租戶知識庫配額。"""
    if not tenant_manager:
        return {"ok": False, "error": "租戶模組未安裝"}
    try:
        import db_postgres
        t = db_postgres.get_tenant_by_slug(tenant_slug)
        plan = t.get("plan", "free") if t else "free"
        return {"ok": True, **tenant_manager.check_kb_quota(tenant_slug, plan)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/tenants/{tenant_slug}/roles/{role_id}/learn")
async def api_tenant_role_learn(tenant_slug: str, role_id: str, request: Request):
    """將知識寫入租戶專屬角色知識庫。"""
    if not tenant_manager:
        return {"ok": False, "error": "租戶模組未安裝"}
    payload = await request.json()
    question = str((payload or {}).get("question", "")).strip()
    answer = str((payload or {}).get("answer", "")).strip()
    source = str((payload or {}).get("source", "api")).strip()
    if not question or not answer:
        raise HTTPException(status_code=400, detail="question and answer are required")
    try:
        return await asyncio.to_thread(
            tenant_manager.tenant_role_learn, tenant_slug, role_id, question, answer, source
        )
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/tenants/{tenant_slug}/roles/{role_id}/search")
async def api_tenant_role_search(tenant_slug: str, role_id: str, request: Request):
    """搜尋租戶角色知識庫（含共用大智庫）。"""
    if not tenant_manager:
        return {"ok": False, "error": "租戶模組未安裝"}
    payload = await request.json()
    query = str((payload or {}).get("query", "")).strip()
    top_k = int((payload or {}).get("top_k", 5) or 5)
    include_master = bool((payload or {}).get("include_master", True))
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    try:
        hits = await asyncio.to_thread(
            tenant_manager.tenant_role_search, tenant_slug, role_id, query, top_k, include_master
        )
        return {"ok": True, "hits": hits, "count": len(hits)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── 付款整合 API（綠界 ECPay）─────────────────────────────────
try:
    import payment_ecpay
except ImportError:
    payment_ecpay = None


@app.post("/api/payment/create")
async def api_payment_create(request: Request):
    """建立付款訂單，回傳綠界表單 HTML。"""
    if not payment_ecpay:
        return {"ok": False, "error": "付款模組未安裝"}
    data = _extract_token(request)
    uid = (data or {}).get("sub", "anonymous")
    payload = await request.json()
    plan = str((payload or {}).get("plan", "basic")).strip()
    return payment_ecpay.create_payment_order(uid, plan)


@app.post("/api/payment/subscribe")
async def api_payment_subscribe(request: Request):
    """建立定期定額訂閱訂單。"""
    if not payment_ecpay:
        return {"ok": False, "error": "付款模組未安裝"}
    data = _extract_token(request)
    uid = (data or {}).get("sub", "anonymous")
    payload = await request.json()
    plan = str((payload or {}).get("plan", "pro")).strip()
    return payment_ecpay.create_subscription_order(uid, plan)


@app.post("/api/payment/callback")
async def api_payment_callback(request: Request):
    """綠界付款結果回調（ReturnURL）。綠界 POST 付款結果到此端點。"""
    if not payment_ecpay:
        return "0|ERROR"
    # ECPay IP 白名單檢查
    if sec_mw:
        client_ip = sec_mw.get_client_ip(request)
        if not sec_mw.is_ecpay_ip_allowed(client_ip):
            print(f"⚠️ ECPay callback 被拒：IP {client_ip} 不在白名單")
            return "0|ERROR"
    try:
        form = await request.form()
        params = {k: v for k, v in form.items()}
        result = payment_ecpay.verify_callback(params)
        if result.get("paid"):
            print(f"💰 付款成功: order={result.get('order_id')} user={result.get('user_id')} plan={result.get('plan')}")
        # 綠界要求回傳 "1|OK" 表示收到
        return "1|OK" if result.get("ok") else "0|ERROR"
    except Exception as e:
        print(f"⚠️ 付款回調錯誤: {e}")
        return "0|ERROR"


@app.get("/api/payment/query/{order_id}")
async def api_payment_query(order_id: str, request: Request):
    """查詢訂單狀態。"""
    if not payment_ecpay:
        return {"ok": False, "error": "付款模組未安裝"}
    return payment_ecpay.query_trade(order_id)


@app.get("/api/payment/plans")
async def api_payment_plans():
    """列出所有可購買方案。"""
    if not payment_ecpay:
        return {"ok": False, "error": "付款模組未安裝"}
    plans = []
    for pid, p in payment_ecpay.PLANS.items():
        plans.append({"id": pid, "name": p["name"], "price_ntd": p["price"], "period": p["period"]})
    return {"ok": True, "plans": plans, "sandbox": payment_ecpay.ECPAY_SANDBOX}


# ── 統一金流閘道 API（ECPay + Alipay + JKoPay）──────────────
try:
    import payment_gateway
except ImportError:
    payment_gateway = None


@app.get("/api/gateway/methods")
async def api_gateway_methods():
    """列出所有可用支付方式。"""
    if not payment_gateway:
        return {"ok": False, "error": "統一金流模組未安裝"}
    return {"ok": True, "methods": payment_gateway.list_methods()}


@app.get("/api/gateway/plans")
async def api_gateway_plans():
    """列出所有訂閱方案。"""
    if not payment_gateway:
        return {"ok": False, "error": "統一金流模組未安裝"}
    return {"ok": True, "plans": payment_gateway.list_plans()}


@app.post("/api/gateway/create")
async def api_gateway_create(request: Request):
    """統一建立訂單（支援 ecpay / alipay / jkopay）。"""
    if not payment_gateway:
        return {"ok": False, "error": "統一金流模組未安裝"}
    data = _extract_token(request)
    uid = (data or {}).get("sub", "anonymous")
    payload = await request.json()
    method = str((payload or {}).get("method", "ecpay")).strip()
    plan = str((payload or {}).get("plan", "pro")).strip()
    custom_amount = int((payload or {}).get("custom_amount", 0) or 0)
    item_name = str((payload or {}).get("item_name", "")).strip()
    return payment_gateway.create_order(method, uid, plan, custom_amount, item_name)


@app.post("/api/gateway/callback/{method}")
async def api_gateway_callback(method: str, request: Request):
    """統一付款回調（各金流 POST 結果到此端點）。"""
    if not payment_gateway:
        return "0|ERROR"
    try:
        content_type = request.headers.get("content-type", "")
        if "json" in content_type:
            raw_body = await request.body()
            params = json.loads(raw_body)
            params["_raw_body"] = raw_body.decode("utf-8", errors="ignore")
        else:
            form = await request.form()
            params = {k: v for k, v in form.items()}

        # 傳入 header 簽章（街口用）
        sig = request.headers.get("X-Signature", "")
        if sig:
            params["X-Signature"] = sig

        result = payment_gateway.verify_callback(method, params)
        if result.get("paid"):
            print(f"💰 [{method}] 付款成功: order={result.get('order_id')} user={result.get('user_id')} plan={result.get('plan')}")

        # ECPay 要求回傳 "1|OK"
        if method == "ecpay":
            return "1|OK" if result.get("ok") else "0|ERROR"
        # Alipay 要求回傳 "success"
        if method == "alipay":
            return "success" if result.get("ok") else "fail"
        # JKoPay 回傳 JSON
        return result
    except Exception as e:
        print(f"⚠️ [{method}] 付款回調錯誤: {e}")
        if method == "ecpay":
            return "0|ERROR"
        return {"ok": False, "error": str(e)}


@app.get("/api/gateway/return/{method}")
async def api_gateway_return(method: str, request: Request):
    """付款完成後用戶導向頁面（前端跳轉）。"""
    params = dict(request.query_params)
    # 導向付款結果頁
    order_id = params.get("MerchantTradeNo") or params.get("out_trade_no") or params.get("platform_order_id", "")
    return HTMLResponse(f"""
    <html><head><meta charset="utf-8"><title>付款處理中</title></head>
    <body style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;background:#0f172a;color:#e2e8f0">
    <div style="text-align:center">
      <h2>✅ 付款處理中</h2>
      <p>訂單編號: {order_id}</p>
      <p>系統正在確認付款結果，請稍候...</p>
      <p><a href="/jarvis" style="color:#0ea5e9">← 返回系統</a></p>
    </div></body></html>
    """)


@app.get("/api/gateway/query/{order_id}")
async def api_gateway_query(order_id: str, method: str = ""):
    """查詢訂單狀態。"""
    if not payment_gateway:
        return {"ok": False, "error": "統一金流模組未安裝"}
    # 自動偵測 method
    if not method:
        if order_id.startswith("ZWA"):
            method = "alipay"
        elif order_id.startswith("ZWJ"):
            method = "jkopay"
        else:
            method = "ecpay"
    return payment_gateway.query_order(method, order_id)


@app.get("/api/gateway/orders")
async def api_gateway_orders(request: Request, status: str = "", limit: int = 50):
    """列出訂單（僅 admin+）。"""
    if not payment_gateway:
        return {"ok": False, "error": "統一金流模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(403, "權限不足")
    orders = payment_gateway.list_orders(status=status, limit=limit)
    return {"ok": True, "orders": orders, "count": len(orders)}


@app.get("/payment")
async def get_payment_page():
    """付款選擇頁面。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "payment.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("payment.html not found", status_code=404)


@app.get("/construction-ai")
async def get_construction_ai_page():
    """營建 AI 助手產品頁。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "construction-ai.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("construction-ai.html not found", status_code=404)


@app.get("/llm-api")
async def get_llm_api_page():
    """大模型 API 產品頁。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "llm-api.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("llm-api.html not found", status_code=404)


@app.get("/asset-commander")
async def get_asset_commander_page():
    """Asset Commander 頁面。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "asset_commander.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("asset_commander.html not found", status_code=404)


# ── 監控儀表板 API ────────────────────────────────────────────
try:
    import structured_logger
except ImportError:
    structured_logger = None


@app.get("/api/monitor/dashboard")
async def api_monitor_dashboard(request: Request):
    """系統監控儀表板資料（僅 superadmin/admin）。"""
    if not structured_logger:
        return {"ok": False, "error": "監控模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    return {"ok": True, **structured_logger.get_dashboard_data()}


@app.get("/api/monitor/logs")
async def api_monitor_logs(request: Request, level: str = "", limit: int = 50):
    """查詢結構化日誌（僅 superadmin/admin）。"""
    if not structured_logger:
        return {"ok": False, "error": "監控模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    try:
        log_file = structured_logger.LOG_FILE
        if not log_file.exists():
            return {"ok": True, "logs": [], "count": 0}
        entries = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if level and entry.get("level", "") != level.upper():
                        continue
                    entries.append(entry)
                except Exception:
                    pass
        entries = entries[-limit:]
        entries.reverse()
        return {"ok": True, "logs": entries, "count": len(entries)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── 營運通知 API ──────────────────────────────────────────────
try:
    import ops_notify
except ImportError:
    ops_notify = None


@app.post("/api/ops/send-email")
async def api_ops_send_email(request: Request):
    """手動發送 Email（僅 admin+）。"""
    if not ops_notify:
        return {"ok": False, "error": "營運模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    payload = await request.json()
    to = str((payload or {}).get("to", "")).strip()
    subject = str((payload or {}).get("subject", "")).strip()
    body = str((payload or {}).get("body", "")).strip()
    if not to or not subject or not body:
        raise HTTPException(status_code=400, detail="to, subject, body are required")
    return ops_notify.send_email(to, subject, ops_notify._email_wrapper(subject, f"<p>{body}</p>"))


@app.post("/api/ops/check-expiring")
async def api_ops_check_expiring(request: Request):
    """手動檢查即將到期的訂閱（僅 admin+）。"""
    if not ops_notify:
        return {"ok": False, "error": "營運模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    payload = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    days = int((payload or {}).get("days", 7))
    results = ops_notify.check_expiring_subscriptions(days)
    return {"ok": True, "results": results, "count": len(results)}


@app.post("/api/ops/check-quota-alerts")
async def api_ops_check_quota(request: Request):
    """手動檢查配額告警（僅 admin+）。"""
    if not ops_notify:
        return {"ok": False, "error": "營運模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    alerts = ops_notify.check_quota_alerts()
    return {"ok": True, "alerts": alerts, "count": len(alerts)}


@app.get("/api/ops/smtp-status")
async def api_ops_smtp_status(request: Request):
    """檢查 SMTP 設定狀態（僅 admin+）。"""
    if not ops_notify:
        return {"ok": False, "error": "營運模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    return {
        "ok": True,
        "smtp_enabled": ops_notify.SMTP_ENABLED,
        "smtp_host": ops_notify.SMTP_HOST,
        "smtp_port": ops_notify.SMTP_PORT,
        "smtp_from": ops_notify.SMTP_FROM,
        "smtp_user_set": bool(ops_notify.SMTP_USER),
    }


# ── AI API 代理服務（對外收費 API）──────────────────────────────
try:
    import ai_api_proxy
    AI_API_PROXY_AVAILABLE = True
except ImportError:
    ai_api_proxy = None
    AI_API_PROXY_AVAILABLE = False


def _extract_api_key(request: Request) -> str:
    """從 Authorization header 提取 API Key (Bearer zw-xxx)"""
    auth = (request.headers.get("authorization") or "").strip()
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return request.query_params.get("api_key", "")


@app.post("/v1/chat/completions")
async def api_proxy_chat(request: Request):
    """OpenAI 相容 Chat Completion API（對外收費）。"""
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    api_key = _extract_api_key(request)
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API Key")
    body = await request.json()
    model = body.get("model", "qwen3:8b")
    messages = body.get("messages", [])
    return await ai_api_proxy.proxy_chat_completion(
        api_key=api_key, model=model, messages=messages,
        temperature=body.get("temperature"), top_p=body.get("top_p"),
        max_tokens=body.get("max_tokens")
    )


@app.post("/v1/embeddings")
async def api_proxy_embeddings(request: Request):
    """OpenAI 相容 Embeddings API（對外收費）。"""
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    api_key = _extract_api_key(request)
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API Key")
    body = await request.json()
    model = body.get("model", "nomic-embed-text")
    input_text = body.get("input", "")
    return await ai_api_proxy.proxy_embeddings(api_key=api_key, model=model, input_text=input_text)


@app.get("/v1/models")
async def api_proxy_models(request: Request):
    """列出可用模型與定價。"""
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    return {"ok": True, "models": ai_api_proxy.get_available_models(), "plans": ai_api_proxy.PLANS}


@app.post("/api/proxy/keys/generate")
async def api_proxy_generate_key(request: Request):
    """生成 API Key（僅 superadmin/admin）。"""
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    body = await request.json()
    return ai_api_proxy.generate_api_key(
        owner=body.get("owner", ""),
        email=body.get("email", ""),
        plan=body.get("plan", "free"),
        expires_days=body.get("expires_days", 365),
        note=body.get("note", "")
    )


@app.get("/api/proxy/keys")
async def api_proxy_list_keys(request: Request):
    """列出所有 API Keys（僅 admin+）。"""
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    keys = ai_api_proxy.list_api_keys(active_only=request.query_params.get("all") != "1")
    return {"ok": True, "keys": keys, "count": len(keys)}


@app.post("/api/proxy/keys/revoke")
async def api_proxy_revoke_key(request: Request):
    """撤銷 API Key（僅 superadmin）。"""
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="權限不足")
    body = await request.json()
    return ai_api_proxy.revoke_api_key(body.get("key_id", ""))


@app.post("/api/proxy/keys/upgrade")
async def api_proxy_upgrade_key(request: Request):
    """升級 API Key 方案（僅 admin+）。"""
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    body = await request.json()
    return ai_api_proxy.update_key_plan(body.get("key_id", ""), body.get("plan", ""))


@app.get("/api/proxy/usage")
async def api_proxy_usage(request: Request, days: int = 30):
    """取得用量統計（admin 看全部，用戶看自己）。"""
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    api_key = _extract_api_key(request)
    if api_key:
        key_info = ai_api_proxy.validate_api_key(api_key)
        if key_info["ok"]:
            return {"ok": True, **ai_api_proxy.get_usage_stats(key_info["id"], days)}
    data = _extract_token(request)
    if data and data.get("role") in ("superadmin", "admin"):
        return {"ok": True, **ai_api_proxy.get_usage_stats("", days)}
    raise HTTPException(status_code=401, detail="需要認證")


@app.get("/api/proxy/revenue")
async def api_proxy_revenue(request: Request):
    """取得收入摘要（僅 admin+）。"""
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    return {"ok": True, **ai_api_proxy.get_revenue_summary()}


# ── Revenue Platform API ─────────────────────────────────────────
try:
    from revenue_platform import get_platform as get_revenue_platform, PRODUCTS
    REVENUE_PLATFORM_AVAILABLE = True
except ImportError:
    REVENUE_PLATFORM_AVAILABLE = False


@app.get("/api/revenue/summary")
async def api_revenue_summary():
    if not REVENUE_PLATFORM_AVAILABLE:
        return {"ok": False, "error": "Revenue Platform 未安裝"}
    return get_revenue_platform().get_revenue_summary()


@app.get("/api/revenue/products")
async def api_revenue_products():
    if not REVENUE_PLATFORM_AVAILABLE:
        return {"ok": False, "error": "Revenue Platform 未安裝"}
    return get_revenue_platform().get_products()


@app.get("/api/revenue/products/{product}/plans")
async def api_revenue_product_plans(product: str):
    if not REVENUE_PLATFORM_AVAILABLE:
        return {"ok": False, "error": "Revenue Platform 未安裝"}
    return get_revenue_platform().get_product_plans(product)


@app.post("/api/revenue/subscribe")
async def api_revenue_subscribe(request: Request):
    if not REVENUE_PLATFORM_AVAILABLE:
        return {"ok": False, "error": "Revenue Platform 未安裝"}
    data = await request.json()
    user_id = data.get("user_id", "anonymous")
    product = data.get("product", "")
    plan = data.get("plan", "")
    return get_revenue_platform().create_subscription(user_id, product, plan)


@app.get("/api/revenue/subscriptions")
async def api_revenue_subscriptions(product: str = None):
    if not REVENUE_PLATFORM_AVAILABLE:
        return {"ok": False, "error": "Revenue Platform 未安裝"}
    subs = get_revenue_platform().get_active_subscriptions(product)
    return {"ok": True, "subscriptions": subs}


@app.get("/api/revenue/usage")
async def api_revenue_usage(product: str = None, days: int = 30):
    if not REVENUE_PLATFORM_AVAILABLE:
        return {"ok": False, "error": "Revenue Platform 未安裝"}
    return get_revenue_platform().get_usage_stats(product, days)


@app.get("/api/revenue/suggestions")
async def api_revenue_suggestions():
    if not REVENUE_PLATFORM_AVAILABLE:
        return {"ok": False, "error": "Revenue Platform 未安裝"}
    return {"ok": True, "suggestions": get_revenue_platform().get_growth_suggestions()}


# ── Asset Commander API ──────────────────────────────────────────
try:
    import asset_commander
    ASSET_COMMANDER_AVAILABLE = True
except ImportError:
    asset_commander = None
    ASSET_COMMANDER_AVAILABLE = False


@app.get("/api/asset/state")
async def api_asset_state():
    """取得 Asset Commander 系統狀態。"""
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    commander = asset_commander.get_commander()
    return {"ok": True, **commander.get_state()}


@app.get("/api/asset/health")
async def api_asset_health():
    """取得 Asset Commander 健康檢查。"""
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    commander = asset_commander.get_commander()
    state = commander.get_state()
    gpu_info = commander.get_gpu_info()
    return {
        "ok": True,
        "running": state["running"],
        "current_platform": state["current_platform"],
        "net_profit_day": state["net_profit_day"],
        "should_pause": state["should_pause"],
        "best_platform": state["best_platform"],
        "gpu_available": gpu_info["available"],
        "gpu_power_watts": state["gpu_power_watts"],
        "gpu_utilization": state["gpu_utilization"]
    }


@app.get("/api/asset/config")
async def api_asset_config():
    """取得 Asset Commander 配置（隱藏敏感資訊）。"""
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    commander = asset_commander.get_commander()
    return {"ok": True, **commander.get_config()}


@app.post("/api/asset/config")
async def api_asset_config_update(request: Request):
    """更新 Asset Commander 配置（僅 admin+）。"""
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    payload = await request.json()
    commander = asset_commander.get_commander()
    commander.update_config(payload)
    return {"ok": True, "message": "配置已更新"}


@app.post("/api/asset/start")
async def api_asset_start():
    """啟動 Asset Commander。"""
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    commander = asset_commander.get_commander()
    commander.start()
    return {"ok": True, "message": "Asset Commander 已啟動"}


@app.post("/api/asset/stop")
async def api_asset_stop():
    """停止 Asset Commander。"""
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    commander = asset_commander.get_commander()
    commander.stop()
    return {"ok": True, "message": "Asset Commander 已停止"}


@app.post("/api/asset/switch")
async def api_asset_switch(request: Request):
    """切換到指定平台（僅 admin+）。"""
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    payload = await request.json()
    platform = payload.get("platform", "")
    commander = asset_commander.get_commander()
    success = await commander.switch_to_platform(platform)
    if success:
        return {"ok": True, "message": f"已切換到 {platform}"}
    return {"ok": False, "error": "切換失敗，平臺不存在"}


@app.get("/api/asset/report")
async def api_asset_report():
    """取得每日收益報告。"""
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    commander = asset_commander.get_commander()
    return {"ok": True, **commander.get_daily_report()}


@app.get("/api/asset/earnings")
async def api_asset_earnings(days: int = 7):
    """取得收益歷史。"""
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    commander = asset_commander.get_commander()
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=days)
    history = [
        r for r in commander.earnings_history
        if datetime.fromisoformat(r["timestamp"]) > cutoff
    ]
    return {"ok": True, "history": history, "count": len(history)}


@app.post("/api/asset/refresh")
async def api_asset_refresh():
    """手動刷新所有平臺收益數據。"""
    if not asset_commander:
        return {"ok": False, "error": "Asset Commander 未安裝"}
    commander = asset_commander.get_commander()
    await commander.update_all_platforms()
    return {"ok": True, "message": "已刷新", **commander.get_state()}


# ── 健康檢查 & 安全管理 API ───────────────────────────────────

@app.get("/healthz")
async def api_healthz():
    """存活檢查（Liveness）— K8s / Docker 用。"""
    if sec_mw:
        return sec_mw.health_check()
    return {"status": "ok"}


@app.get("/readyz")
async def api_readyz():
    """就緒檢查（Readiness）— 確認 PG + ChromaDB 可用。"""
    if sec_mw:
        result = sec_mw.readiness_check()
        if result["status"] != "ready":
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=503, content=result)
        return result
    return {"status": "ready"}


@app.post("/api/security/api-keys")
async def api_create_api_key(request: Request):
    """為租戶生成 API Key（僅 superadmin/admin）。"""
    if not sec_mw:
        return {"ok": False, "error": "安全模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    payload = await request.json()
    tenant_slug = str((payload or {}).get("tenant_slug", "")).strip()
    description = str((payload or {}).get("description", "")).strip()
    if not tenant_slug:
        raise HTTPException(status_code=400, detail="tenant_slug is required")
    return sec_mw.generate_api_key(tenant_slug, description)


@app.get("/api/security/api-keys")
async def api_list_api_keys(request: Request, tenant_slug: str = ""):
    """列出 API Keys（僅 superadmin/admin）。"""
    if not sec_mw:
        return {"ok": False, "error": "安全模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    keys = sec_mw.list_api_keys(tenant_slug)
    return {"ok": True, "keys": keys, "count": len(keys)}


@app.post("/api/security/api-keys/revoke")
async def api_revoke_api_key(request: Request):
    """撤銷 API Key（僅 superadmin）。"""
    if not sec_mw:
        return {"ok": False, "error": "安全模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="權限不足")
    payload = await request.json()
    key_prefix = str((payload or {}).get("key_prefix", "")).strip()
    if not key_prefix:
        raise HTTPException(status_code=400, detail="key_prefix is required")
    return sec_mw.revoke_api_key(key_prefix)


@app.get("/api/security/rate-limits")
async def api_rate_limit_stats(request: Request):
    """查看限流統計（僅 admin+）。"""
    if not sec_mw:
        return {"ok": False, "error": "安全模組未安裝"}
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    return {"ok": True, **sec_mw.rate_limiter.get_stats()}


# ── 優雅關機 ──
import signal

def _graceful_shutdown(signum, frame):
    """收到 SIGTERM/SIGINT 時標記關機。"""
    print("🛑 收到關機信號，開始優雅關機...")
    if sec_mw:
        sec_mw.request_shutdown()

signal.signal(signal.SIGTERM, _graceful_shutdown)
signal.signal(signal.SIGINT, _graceful_shutdown)


# ── Host API 代理（截圖、系統資訊等）──────────────────────────
HOST_API = os.environ.get("HOST_API_URL", "http://host.docker.internal:8010").rstrip("/")


def _proxy_host(path: str, params: dict | None = None, method: str = "GET", json_body: dict | None = None) -> dict:
    """轉發請求到主機端 Host API。"""
    import urllib.request, urllib.parse
    url = f"{HOST_API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        if method == "POST" and json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        else:
            req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": f"Host API 不可達: {e}"}


@app.get("/api/host/screenshot")
async def api_host_screenshot(format: str = "base64"):
    """代理主機截圖（base64 或 file 模式）。"""
    return _proxy_host("/screenshot", {"format": format})


@app.get("/api/host/screenshot/png")
async def api_host_screenshot_png():
    """代理主機截圖，直接回傳 PNG 圖片。"""
    import urllib.request
    url = f"{HOST_API}/screenshot?format=png"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            return Response(content=data, media_type="image/png")
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)


@app.get("/api/host/sysinfo")
async def api_host_sysinfo():
    """代理主機系統資訊。"""
    return _proxy_host("/sysinfo")


@app.get("/api/host/windows")
async def api_host_windows():
    """代理主機視窗列表。"""
    return _proxy_host("/windows")


@app.get("/api/host/processes")
async def api_host_processes(top: int = 20):
    """代理主機程序列表。"""
    return _proxy_host("/processes", {"top": top})


@app.post("/api/host/execute")
async def api_host_execute(request: Request):
    """代理主機執行命令或開啟軟體。"""
    body = await request.json()
    return _proxy_host("/execute", method="POST", json_body=body)


@app.post("/api/host/search")
async def api_host_search(request: Request):
    """代理主機搜尋檔案。"""
    body = await request.json()
    return _proxy_host("/search", method="POST", json_body=body)


@app.post("/api/host/open_terminal")
async def api_host_open_terminal(request: Request):
    """代理主機開啟終端機。"""
    body = await request.json()
    return _proxy_host("/open_terminal", method="POST", json_body=body)


@app.post("/api/host/keystroke")
async def api_host_keystroke(request: Request):
    """代理主機傳送鍵盤輸入。"""
    body = await request.json()
    return _proxy_host("/keystroke", method="POST", json_body=body)


@app.post("/api/host/mouse")
async def api_host_mouse(request: Request):
    """代理主機滑鼠操作。"""
    body = await request.json()
    return _proxy_host("/mouse", method="POST", json_body=body)


# ===== Phone Agent（手機代理人）=====

@app.get("/api/phone/status")
async def api_phone_status():
    """檢查手機連線狀態和 DroidRun 可用性。"""
    try:
        from phone_agent import ADBController, droidrun_available, PHONE_ADB_HOST, PHONE_ADB_PORT
        adb = ADBController()
        connected = adb.is_connected()
        return {
            "ok": True,
            "connected": connected,
            "device": f"{PHONE_ADB_HOST}:{PHONE_ADB_PORT}",
            "droidrun_available": droidrun_available(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/phone/connect")
async def api_phone_connect(request: Request):
    """連接手機。可選 {"host": "192.168.1.100", "port": "5555"}"""
    try:
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    except Exception:
        body = {}
    try:
        from phone_agent import phone_connect
        result = phone_connect(body.get("host", ""), body.get("port", ""))
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/phone/disconnect")
async def api_phone_disconnect():
    """斷開手機。"""
    try:
        from phone_agent import phone_disconnect
        return phone_disconnect()
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/api/phone/screenshot")
async def api_phone_screenshot():
    """手機截圖 + AI 視覺分析。"""
    try:
        from phone_agent import phone_screenshot
        return phone_screenshot()
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/phone/task")
async def api_phone_task(request: Request):
    """
    執行手機自然語言任務。
    {"task": "打開 LINE 回覆最新訊息：收到"}
    """
    body = await request.json()
    task = body.get("task", "").strip()
    if not task:
        return {"success": False, "message": "task 必填"}
    try:
        from phone_agent import phone_task_async
        result = await phone_task_async(task, body.get("host", ""), body.get("port", ""))
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/phone/line/reply")
async def api_phone_line_reply(request: Request):
    """
    LINE 回覆訊息。
    {"message": "收到，明天處理", "contact": "王經理"}
    """
    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        return {"success": False, "message": "message 必填"}
    try:
        from phone_agent import line_reply
        return line_reply(message, body.get("contact", ""))
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/api/phone/line/read")
async def api_phone_line_read():
    """讀取 LINE 最新訊息（截圖 + AI 辨識）。"""
    try:
        from phone_agent import line_read_latest
        return line_read_latest()
    except Exception as e:
        return {"success": False, "message": str(e)}


# ===== Smart Remote Agent（智慧遙控）=====
SMART_REMOTE_LOCK = asyncio.Lock()


@app.post("/api/smart/execute")
async def api_smart_execute(request: Request):
    """
    智慧遙控執行（自然語言 → 動作規劃 → 執行）
    {
      "instruction": "開啟記事本並輸入 Hello World",
      "execute": true,
      "provider": "gemini"
    }
    """
    body = await request.json()
    instruction = body.get("instruction", "").strip()
    execute = body.get("execute", True)
    provider = body.get("provider", "gemini")

    if not instruction:
        return {"ok": False, "error": "instruction 必填"}

    try:
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from smart_remote_agent import SmartRemoteAgent

        async with SMART_REMOTE_LOCK:
            agent = SmartRemoteAgent(llm_provider=provider)
            result = agent.run(instruction, execute=execute)

        return {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/smart/analyze")
async def api_smart_analyze(request: Request):
    """
    分析當前螢幕（VLM）
    {
      "focus_area": "全螢幕"
    }
    """
    body = await request.json()
    focus_area = body.get("focus_area", "全螢幕")

    try:
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from smart_remote_agent import SmartRemoteAgent

        agent = SmartRemoteAgent()
        result = agent.analyze_screen(focus_area)

        return {"ok": True, "analysis": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/smart/ask")
async def api_smart_ask(request: Request):
    """
    智慧遙控問答（不執行）
    {
      "question": "如何在 VS Code 中開啟終端機？"
    }
    """
    body = await request.json()
    question = body.get("question", "").strip()

    if not question:
        return {"ok": False, "error": "question 必填"}

    try:
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from smart_remote_agent import SmartRemoteAgent

        agent = SmartRemoteAgent()
        answer = agent.ask(question)

        return {"ok": True, "answer": answer}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/smart/status")
async def api_smart_status():
    """取得智慧遙控狀態。"""
    return {
        "ok": True,
        "features": [
            "自然語言理解",
            "多步驟任務規劃",
            "VLM 視覺分析",
            "智慧檔案搜尋",
            "GUI 自動化"
        ],
        "providers": ["gemini", "claude", "ollama", "deepseek", "groq"],
        "endpoints": [
            "POST /api/smart/execute",
            "POST /api/smart/analyze",
            "POST /api/smart/ask",
            "GET /api/smart/status"
        ]
    }


# ===== Conversational Remote（對話式遙控）=====
CONVERSATION_LOCK = asyncio.Lock()


@app.post("/api/chat/remote")
async def api_chat_remote(request: Request):
    """
    對話式遙控（像聊天一樣控制電腦）
    {
      "message": "開啟記事本並輸入 Hello",
      "execute": true,
      "provider": "gemini"
    }
    """
    body = await request.json()
    message = body.get("message", "").strip()
    execute = body.get("execute", True)
    provider = body.get("provider", "gemini")

    if not message:
        return {"ok": False, "error": "message 必填"}

    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from conversational_remote import ConversationalRemote

        async with CONVERSATION_LOCK:
            remote = ConversationalRemote(llm_provider=provider)
            result = remote.chat(message, execute=execute)

        return {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/chat/remote/history")
async def api_chat_remote_history(limit: int = 20):
    """取得對話歷史。"""
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from conversational_remote import ConversationalRemote

        remote = ConversationalRemote()
        history = remote.get_conversation_history(limit)

        return {"ok": True, "history": history}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/chat/remote/clear")
async def api_chat_remote_clear():
    """清除對話歷史。"""
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from conversational_remote import ConversationalRemote

        remote = ConversationalRemote()
        remote.clear_history()

        return {"ok": True, "message": "對話歷史已清除"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/chat/remote/status")
async def api_chat_remote_status():
    """取得對話遙控系統狀態。"""
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from conversational_remote import ConversationalRemote

        remote = ConversationalRemote()
        status = remote.get_system_status()

        return {
            "ok": True,
            "features": [
                "自然語言對話",
                "意圖理解",
                "動作規劃",
                "執行回覆",
                "對話歷史"
            ],
            "system_status": status,
            "endpoints": [
                "POST /api/chat/remote",
                "GET /api/chat/remote/history",
                "POST /api/chat/remote/clear",
                "GET /api/chat/remote/status"
            ]
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ===== Vision Edge Service 代理（port 8015）=====
VISION_EDGE_URL = os.environ.get("VISION_EDGE_URL", "http://localhost:8015")


def _proxy_vision(path: str, method: str = "GET", params: dict = None, json_body: dict = None):
    """代理 Vision Edge Service 請求。"""
    import urllib.request, urllib.parse
    url = f"{VISION_EDGE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        if method == "POST" and json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        return {"ok": False, "error": f"Vision Edge 不可達: {e}"}


@app.get("/api/vision/health")
async def api_vision_health():
    """Vision Edge 健康檢查。"""
    return _proxy_vision("/health")


@app.get("/api/vision/stats")
async def api_vision_stats():
    """Vision Edge 推理統計。"""
    return _proxy_vision("/api/vision/stats")


@app.get("/api/vision/history")
async def api_vision_history(limit: int = 20):
    """Vision Edge 推理歷史。"""
    return _proxy_vision("/api/vision/history", params={"limit": limit})


@app.get("/api/vision/monitor/status")
async def api_vision_monitor_status():
    """Vision Edge 監控狀態。"""
    return _proxy_vision("/api/monitor/status")


@app.get("/api/vision/monitor/alerts")
async def api_vision_monitor_alerts(limit: int = 50, level: str = ""):
    """Vision Edge 告警列表。"""
    return _proxy_vision("/api/monitor/alerts", params={"limit": limit, "level": level})


@app.get("/api/vision/knowledge/search")
async def api_vision_kb_search(q: str = "", limit: int = 10):
    """Vision Edge 知識庫搜尋。"""
    return _proxy_vision("/api/vision/knowledge/search", params={"q": q, "limit": limit})


@app.get("/vision-edge")
async def get_vision_edge_dashboard(request: Request):
    """視覺邊緣計算儀表板（代理到 Vision Edge Service）。"""
    auth = _require_auth(request)
    if isinstance(auth, RedirectResponse):
        return auth
    try:
        import urllib.request
        with urllib.request.urlopen(f"{VISION_EDGE_URL}/", timeout=5) as r:
            html = r.read().decode("utf-8", errors="ignore")
        return HTMLResponse(html)
    except Exception:
        return HTMLResponse("<h1>Vision Edge Service 未啟動</h1><p>請先執行 scripts/start_vision_edge.bat</p>", status_code=503)


@app.get("/agent-hub")
async def get_agent_hub(request: Request):
    """獨立遠端窗口：可切 provider（cursor/gemini/claude/codebuddy）與模式切換。"""
    auth = _require_auth(request)
    if isinstance(auth, RedirectResponse):
        return auth
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "agent_hub.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("agent_hub.html not found", status_code=404)


@app.get("/push-demo")
async def get_push_demo(request: Request):
    """Ntfy 推播測試台。"""
    auth = _require_auth(request)
    if isinstance(auth, RedirectResponse):
        return auth
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "push-demo.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("push-demo.html not found", status_code=404)


@app.get("/health-dashboard")
async def get_health_dashboard(request: Request):
    """健康儀表板：單頁顯示核心狀態、語音與外部依賴。"""
    auth = _require_auth(request)
    if isinstance(auth, RedirectResponse):
        return auth
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "health_dashboard.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("health_dashboard.html not found", status_code=404)


@app.get("/usage-dashboard")
async def get_usage_dashboard():
    """AI 用量監控儀表板（無需認證）。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "usage-dashboard.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("usage-dashboard.html not found", status_code=404)


@app.get("/favicon.ico")
async def favicon():
    """Favicon — 避免瀏覽器 404。"""
    fav = STATIC_DIR / "favicon.svg"
    if fav.exists():
        return FileResponse(str(fav), media_type="image/svg+xml")
    from starlette.responses import Response as RawResponse
    return RawResponse(status_code=204)


@app.get("/health")
def health_check():
    """健康檢查：含依賴狀態（Ollama、venv_vision、靜態目錄）。"""
    ollama_ok = False
    try:
        import urllib.request
        url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/tags"
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=2) as r:
            ollama_ok = r.status == 200
    except Exception:
        pass
    venv_vision = BRAIN_WORKSPACE / "venv_vision" / "Scripts" / "python.exe"
    if not venv_vision.exists():
        venv_vision = BRAIN_WORKSPACE / "venv_vision" / "bin" / "python"
    voice = _resolve_voice_status()
    deps = _resolve_dependency_status()
    mode = (os.environ.get("STACK_MODE") or "").strip().lower()
    if mode not in {"daily", "dev"}:
        mode = _mode_from_dependencies(deps)
    return {
        "status": "healthy",
        "engine": os.environ.get("BRAIN_ENGINE", "i7-14700-Core"),
        "mode": mode,
        "ollama": ollama_ok,
        "venv_vision": venv_vision.exists(),
        "static_dir": (STATIC_DIR / "index.html").exists(),
        "progress_dir": PROGRESS_FILE.parent.exists(),
        "voice": voice,
        "dependencies": _dependency_display(deps, mode),
        "dependencies_raw": deps,
    }


@app.get("/api/health/summary")
def api_health_summary():
    """前端儀表板專用健康摘要。"""
    return health_check()


@app.get("/api/system/mode/status")
def api_mode_status():
    deps = _resolve_dependency_status()
    return {"ok": True, "mode": _mode_from_dependencies(deps), "dependencies": deps}


@app.post("/api/system/mode/switch")
async def api_mode_switch(request: Request):
    payload = await request.json()
    mode = str((payload or {}).get("mode", "")).strip().lower()
    if mode not in {"daily", "dev"}:
        raise HTTPException(status_code=400, detail="mode must be daily or dev")

    script_ps1 = ROOT / "scripts" / "switch_stack_mode.ps1"
    if not script_ps1.exists():
        return {"ok": False, "error": f"script not found: {script_ps1}"}

    powershell_cmd = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell_cmd:
        # 容器模式：改走主機代理請求檔，交給 host watcher 執行（點擊式仍可用）
        req_file = ROOT / "reports" / "mode_switch_request.json"
        req_file.parent.mkdir(parents=True, exist_ok=True)
        req = {
            "mode": mode,
            "requested_at": int(time.time()),
            "source": "brain_server_container",
        }
        req_file.write_text(json.dumps(req, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "queued": True,
            "mode": mode,
            "hint": "已排入主機切換佇列，請確認 scripts/start_runtime_monitor.bat 正在執行。",
        }

    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            [powershell_cmd, "-ExecutionPolicy", "Bypass", "-File", str(script_ps1), "-Mode", mode],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=180,
        )
        out = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()[-3000:]
        return {
            "ok": proc.returncode == 0,
            "mode": mode,
            "exit_code": int(proc.returncode),
            "output": out,
        }
    except Exception as e:
        return {"ok": False, "mode": mode, "error": str(e)}


@app.get("/api/system/mode/result")
def api_mode_result():
    res_file = ROOT / "reports" / "mode_switch_result.json"
    if not res_file.exists():
        return {"ok": False, "pending": True, "message": "no result yet"}
    try:
        return json.loads(res_file.read_text(encoding="utf-8", errors="ignore"))
    except Exception as e:
        return {"ok": False, "pending": True, "message": str(e)}


@app.post("/api/remote/chat")
async def api_remote_chat(request: Request):
    """
    遠端代理對話 API：
    provider: cursor / gemini / claude / codebuddy
    （cursor、codebuddy 為代理通道名稱，底層映射到現有模型）
    """
    payload = await request.json()
    provider_raw = str((payload or {}).get("provider", "ollama"))
    message = str((payload or {}).get("message", "")).strip()
    session_id = str((payload or {}).get("session_id", "default")).strip() or "default"
    max_turns = max(2, min(20, int((payload or {}).get("max_turns", 10) or 10)))
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    provider_effective, provider_mapping = _provider_alias(provider_raw)
    # 用量計量：從 JWT 取得用戶 ID
    token_data = _extract_token(request)
    uid = (token_data or {}).get("sub", "") or "anonymous"
    smart_ai._current_user_id = uid

    history = remote_sessions.get(session_id, [])
    history.append({"role": "user", "content": message})
    history = history[-(max_turns * 2):]
    remote_sessions[session_id] = history

    messages = [{"role": "system", "content": "你是遠端工程代理人，回答簡潔、先結論後步驟。"}]
    messages.extend(history)
    reply = await _remote_chat_reply(provider_effective, messages)
    reply_clean = _clean_model_output(reply) or "目前沒有可用回應，請稍後再試。"

    history.append({"role": "assistant", "content": reply_clean})
    remote_sessions[session_id] = history[-(max_turns * 2):]
    return {
        "ok": True,
        "session_id": session_id,
        "provider_requested": provider_raw,
        "provider_effective": provider_effective,
        "provider_mapping": provider_mapping,
        "reply": reply_clean,
    }


@app.get("/api/agent/tasks")
def api_agent_tasks():
    items = sorted(agent_tasks.values(), key=lambda x: str(x.get("created_at", "")), reverse=True)
    return {"ok": True, "count": len(items), "tasks": items[:200]}


@app.post("/api/agent/tasks")
async def api_agent_create_task(request: Request):
    payload = await request.json()
    objective = str((payload or {}).get("objective", "")).strip()
    provider = str((payload or {}).get("provider", "cursor")).strip().lower()
    context = str((payload or {}).get("context", "")).strip()
    execution = str((payload or {}).get("execution", "llm")).strip().lower()
    job_type = str((payload or {}).get("job_type", "")).strip().lower()
    auto_run = bool((payload or {}).get("auto_run", True))
    if not objective:
        raise HTTPException(status_code=400, detail="objective is required")

    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {
        "id": task_id,
        "objective": objective,
        "provider": provider,
        "execution": execution if execution in {"llm", "host_script"} else "llm",
        "job_type": job_type or "",
        "status": "queued" if auto_run else "pending",
        "context": context,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "result": "",
        "logs": [f"{_now_iso()} | task created"],
    }
    agent_tasks[task_id] = task
    _save_agent_tasks()
    if auto_run:
        await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@app.post("/api/agent/tasks/{task_id}/run")
async def api_agent_run_task(task_id: str):
    tid = str(task_id or "").strip()
    task = agent_tasks.get(tid)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    if task.get("status") in {"running"}:
        return {"ok": True, "queued": False, "task": task}
    task["status"] = "queued"
    task["updated_at"] = _now_iso()
    task.setdefault("logs", []).append(f"{_now_iso()} | queued by user")
    _save_agent_tasks()
    await agent_task_queue.put(tid)
    return {"ok": True, "queued": True, "task": task}


@app.get("/api/agent/tasks/{task_id}")
def api_agent_task_detail(task_id: str):
    tid = str(task_id or "").strip()
    task = agent_tasks.get(tid)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return {"ok": True, "task": task}


@app.post("/api/agent/tasks/desktop-demo")
async def api_agent_desktop_demo():
    """建立桌面示範任務（會移動滑鼠與輸入文字）。"""
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {
        "id": task_id,
        "objective": "執行 PyAutoGUI 桌面示範腳本（my_agent.py）",
        "provider": "desktop",
        "execution": "host_script",
        "job_type": "pyautogui_demo",
        "status": "queued",
        "context": "此任務會控制滑鼠與鍵盤，請先把焦點切到安全視窗。",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "result": "",
        "logs": [f"{_now_iso()} | desktop demo task created"],
    }
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@app.post("/api/agent/tasks/line-open")
async def api_agent_line_open():
    """建立 LINE 開啟任務（主機端）。"""
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {
        "id": task_id,
        "objective": "開啟 LINE 桌面版",
        "provider": "desktop",
        "execution": "host_script",
        "job_type": "line_open",
        "status": "queued",
        "context": "若找不到執行檔，請確認 LINE 安裝路徑。",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "result": "",
        "logs": [f"{_now_iso()} | line-open task created"],
    }
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@app.post("/api/agent/tasks/line-read")
async def api_agent_line_read():
    """建立 LINE OCR 讀取任務（不保證穩定）。"""
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {
        "id": task_id,
        "objective": "OCR 讀取目前 LINE 視窗訊息（估測）",
        "provider": "desktop",
        "execution": "host_script",
        "job_type": "line_read_ocr",
        "status": "queued",
        "context": "LINE 無官方讀訊 API，此任務依賴截圖+OCR，可能不準確。",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "result": "",
        "logs": [f"{_now_iso()} | line-read task created"],
    }
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@app.post("/api/agent/tasks/line-read-vlm")
async def api_agent_line_read_vlm(request: Request):
    """建立 LINE VLM 判讀任務（以視覺語言模型取代純 OCR）。"""
    payload = await request.json() if request else {}
    question = str((payload or {}).get("question", "")).strip() or "最後一則訊息是誰發的？內容是什麼？有沒有提到『緊急』或『修改』？"
    keywords = (payload or {}).get("keywords", ["緊急", "修改", "urgent", "change"])
    if not isinstance(keywords, list):
        keywords = ["緊急", "修改", "urgent", "change"]
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {
        "id": task_id,
        "objective": "VLM 判讀目前 LINE 視窗內容",
        "provider": "desktop",
        "execution": "host_script",
        "job_type": "line_read_vlm",
        "status": "queued",
        "context": "透過截圖 + VLM 判讀最後訊息與關鍵字。",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "result": "",
        "logs": [f"{_now_iso()} | line-read-vlm task created"],
        "args": {"question": question, "keywords": keywords},
    }
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@app.post("/api/agent/tasks/screen-vlm")
async def api_agent_screen_vlm(request: Request):
    """建立全螢幕 VLM 判讀任務。"""
    payload = await request.json() if request else {}
    question = str((payload or {}).get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {
        "id": task_id,
        "objective": f"VLM 判讀全螢幕：{question}",
        "provider": "desktop",
        "execution": "host_script",
        "job_type": "screen_vlm_query",
        "status": "queued",
        "context": "全螢幕截圖 + VLM 問答。",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "result": "",
        "logs": [f"{_now_iso()} | screen-vlm task created"],
        "args": {"question": question},
    }
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@app.post("/api/agent/tasks/smart-gui")
async def api_agent_smart_gui(request: Request):
    """建立 Smart GUI 任務：由 VLM 規劃動態座標並執行。"""
    payload = await request.json()
    instruction = str((payload or {}).get("instruction", "")).strip()
    execute = bool((payload or {}).get("execute", True))
    max_actions = int((payload or {}).get("max_actions", 8) or 8)
    retry_count = int((payload or {}).get("retry_count", 3) or 3)
    if not instruction:
        raise HTTPException(status_code=400, detail="instruction is required")
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {
        "id": task_id,
        "objective": f"Smart GUI：{instruction}",
        "provider": "desktop",
        "execution": "host_script",
        "job_type": "smart_gui_agent",
        "status": "queued",
        "context": "透過 VLM 解析畫面後進行點擊/輸入操作。",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "result": "",
        "logs": [f"{_now_iso()} | smart-gui task created"],
        "args": {
            "instruction": instruction,
            "execute": execute,
            "max_actions": max(1, min(20, max_actions)),
            "retry_count": max(1, min(5, retry_count)),
        },
    }
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@app.post("/api/agent/tasks/semantic-route")
async def api_agent_semantic_route(request: Request):
    """
    語義路由：
    - 將自然語句拆成多個可執行任務（LINE、VLM、Smart GUI）
    - 可選擇立即入列執行
    """
    payload = await request.json()
    text = str((payload or {}).get("text", "")).strip()
    auto_run = bool((payload or {}).get("auto_run", True))
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    plan = _semantic_route_plan(text)
    created: list[dict] = []
    parent_id = f"R-{uuid.uuid4().hex[:8]}"
    for idx, step in enumerate(plan, start=1):
        task = _build_task_from_step(
            route_id=parent_id,
            idx=idx,
            total=len(plan),
            route_context=text,
            step=step if isinstance(step, dict) else {},
            auto_run=auto_run,
        )
        task["logs"] = [f"{_now_iso()} | semantic-route task created"]
        tid = str(task.get("id", ""))
        agent_tasks[tid] = task
        created.append(task)
        if auto_run and tid:
            await agent_task_queue.put(tid)
    _save_agent_tasks()
    return {"ok": True, "route_id": parent_id, "count": len(created), "tasks": created}


@app.post("/api/jarvis/generate-image")
async def api_jarvis_generate_image(request: Request):
    """遠端文字生圖（ComfyUI 本地優先）。"""
    payload = await request.json()
    prompt = str((payload or {}).get("prompt", "")).strip()
    filename = str((payload or {}).get("filename", "jarvis_gen.png")).strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "ai_modules"))
        from ai_creative_tools import text_to_image
        result = await asyncio.to_thread(text_to_image, prompt, filename)
        return {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/jarvis/analyze-image")
async def api_jarvis_analyze_image(request: Request):
    """分析上傳的圖片（多模態輸入）。"""
    payload = await request.json()
    image = str((payload or {}).get("image", "")).strip()
    prompt = str((payload or {}).get("prompt", "請描述這張圖片的內容")).strip()
    
    if not image:
        return {"ok": False, "error": "image is required"}
    
    try:
        # 使用 Gemini Vision 分析圖片
        import google.generativeai as genai
        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
        if not GEMINI_API_KEY:
            return {"ok": False, "error": "未設定 GEMINI_API_KEY"}
        
        genai.configure(api_key=GEMINI_API_KEY)
        
        # 移除 data:image 前綴
        if image.startswith("data:image"):
            image = image.split(",", 1)[1]
        
        import base64
        image_data = base64.b64decode(image)
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([
            prompt,
            {"inline_data": {"mime_type": "image/png", "data": image_data}}
        ])
        
        return {"ok": True, "result": response.text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/jarvis/ask-and-learn")
async def api_jarvis_ask_and_learn(request: Request):
    """問大模型問題，自動萃取精華寫入本地知識庫。"""
    payload = await request.json()
    question = str((payload or {}).get("question", "")).strip()
    providers = (payload or {}).get("providers", ["gemini", "claude", "grok"])
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "Jarvis_Training"))
        from learn_from_giants import ask_and_learn
        result = await asyncio.to_thread(ask_and_learn, question, providers, True)
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/jarvis/batch-learn")
async def api_jarvis_batch_learn(request: Request):
    """批次學習：給定主題列表，逐一問大模型並學習精華。"""
    payload = await request.json()
    topics = (payload or {}).get("topics", [])
    providers = (payload or {}).get("providers", ["gemini", "claude", "grok"])
    if not topics or not isinstance(topics, list):
        raise HTTPException(status_code=400, detail="topics (list) is required")
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "Jarvis_Training"))
        from learn_from_giants import batch_learn
        result = await asyncio.to_thread(batch_learn, topics[:20], providers)
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/jarvis/learning-stats")
def api_jarvis_learning_stats():
    """查看大模型學習統計。"""
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "Jarvis_Training"))
        from learn_from_giants import learning_stats
        return {"ok": True, **learning_stats()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/jarvis/self-check")
async def api_jarvis_self_check():
    """系統自檢：檢查 Ollama、ChromaDB、API Keys、學習管線。"""
    try:
        import self_check
        # 使用較長的超時時間，確保檢查完成
        result = await asyncio.wait_for(
            asyncio.to_thread(self_check.full_check),
            timeout=60.0  # 60秒超時
        )
        return result
    except asyncio.TimeoutError:
        return {"ok": False, "error": "自檢超時，請稍後重試"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/jarvis/self-repair")
async def api_jarvis_self_repair():
    """系統自動修復：拉取缺失模型、重建 Collection 等。"""
    try:
        import self_check
        result = await asyncio.to_thread(self_check.repair_all)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── 角色知識庫 API ──────────────────────────────────────────
@app.get("/api/jarvis/roles")
def api_jarvis_roles():
    """列出所有可用角色。"""
    try:
        import role_manager
        return {"ok": True, "roles": role_manager.list_roles()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/jarvis/roles/stats")
def api_jarvis_roles_stats():
    """取得所有角色知識庫統計。"""
    try:
        import role_manager
        return role_manager.all_roles_stats()
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/jarvis/roles/{role_id}/stats")
def api_jarvis_role_stats(role_id: str):
    """取得單一角色知識庫統計。"""
    try:
        import role_manager
        return role_manager.role_stats(role_id)
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/jarvis/roles/{role_id}/learn")
async def api_jarvis_role_learn(role_id: str, request: Request):
    """將知識寫入角色專屬知識庫。"""
    payload = await request.json()
    question = str((payload or {}).get("question", "")).strip()
    answer = str((payload or {}).get("answer", "")).strip()
    source = str((payload or {}).get("source", "api")).strip()
    if not question or not answer:
        raise HTTPException(status_code=400, detail="question and answer are required")
    try:
        import role_manager
        return role_manager.role_learn(role_id, question, answer, source)
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/jarvis/roles/{role_id}/search")
async def api_jarvis_role_search(role_id: str, request: Request):
    """搜尋角色知識庫（含大智庫）。"""
    payload = await request.json()
    query = str((payload or {}).get("query", "")).strip()
    top_k = int((payload or {}).get("top_k", 5) or 5)
    include_master = bool((payload or {}).get("include_master", True))
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    try:
        import role_manager
        hits = await asyncio.to_thread(role_manager.role_search, role_id, query, top_k, include_master)
        return {"ok": True, "hits": hits, "count": len(hits)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/jarvis/roles/{role_id}/ask")
async def api_jarvis_role_ask(role_id: str, request: Request):
    """以角色身份回答問題（角色知識庫 + 大智庫 + 角色提示詞）。"""
    payload = await request.json()
    query = str((payload or {}).get("query", "")).strip()
    top_k = int((payload or {}).get("top_k", 5) or 5)
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    try:
        import role_manager
        result = await asyncio.to_thread(role_manager.role_ask, role_id, query, top_k)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/jarvis/roles/{role_id}/ask-and-learn")
async def api_jarvis_role_ask_and_learn(role_id: str, request: Request):
    """以角色身份問大模型並學習精華到角色知識庫。"""
    payload = await request.json()
    question = str((payload or {}).get("question", "")).strip()
    providers = (payload or {}).get("providers", ["groq"])
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "Jarvis_Training"))
        from learn_from_giants import ask_and_learn
        import role_manager
        role = role_manager.get_role(role_id)
        if not role:
            raise HTTPException(status_code=404, detail=f"角色 '{role_id}' 不存在")
        # 加入角色前綴讓大模型以角色視角回答
        role_prefix = f"[以{role['name']}的專業視角回答] "
        result = await asyncio.to_thread(ask_and_learn, role_prefix + question, providers, True)
        # 同時寫入角色知識庫
        if result.get("learned") and result.get("essence"):
            role_manager.role_learn(role_id, question, result["essence"], f"giant_{result.get('source', 'unknown')}")
        result["role"] = role_id
        result["role_name"] = role["name"]
        return {"ok": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── MCP 工作流 API ──────────────────────────────────────────
@app.post("/api/jarvis/workflow/create")
async def api_workflow_create(request: Request):
    """建立新 MCP 工作流。"""
    payload = await request.json()
    role_id = str((payload or {}).get("role_id", "")).strip()
    idea = str((payload or {}).get("idea", "")).strip()
    title = str((payload or {}).get("title", "")).strip()
    if not role_id or not idea:
        raise HTTPException(status_code=400, detail="role_id and idea are required")
    try:
        import mcp_workflow
        result = mcp_workflow.create_workflow(role_id, idea, title)
        # 自動推進到 analyze 步驟
        if result.get("ok"):
            result = await asyncio.to_thread(mcp_workflow.advance_step, result["workflow"]["id"])
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/jarvis/workflow/list")
def api_workflow_list(status: str = ""):
    """列出所有工作流。"""
    try:
        import mcp_workflow
        return {"ok": True, "workflows": mcp_workflow.list_workflows(status)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/jarvis/workflow/{wf_id}")
def api_workflow_get(wf_id: str):
    """取得工作流詳情。"""
    try:
        import mcp_workflow
        return mcp_workflow.get_workflow(wf_id)
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/jarvis/workflow/{wf_id}/advance")
async def api_workflow_advance(wf_id: str, request: Request):
    """推進工作流到下一步。"""
    payload = await request.json()
    user_input = str((payload or {}).get("input", "")).strip()
    user_approved = bool((payload or {}).get("approved", True))
    try:
        import mcp_workflow
        result = await asyncio.to_thread(mcp_workflow.advance_step, wf_id, user_input, user_approved)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/jarvis/workflow/stats")
def api_workflow_stats():
    """工作流統計。"""
    try:
        import mcp_workflow
        return mcp_workflow.workflow_stats()
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/jarvis/generate-code")
async def api_jarvis_generate_code(request: Request):
    """根據需求描述生成完整 HTML/CSS/JS 網頁程式碼。"""
    payload = await request.json()
    prompt = str((payload or {}).get("prompt", "")).strip()
    lang = str((payload or {}).get("lang", "html")).strip().lower()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    system_msg = (
        "你是一個專業的前端工程師。根據使用者需求，生成完整可運行的程式碼。\n"
        "規則：\n"
        "1. 如果是網頁需求，生成一個完整的 HTML 檔案（包含內嵌 CSS 和 JS），可直接在瀏覽器中運行。\n"
        "2. 使用現代 CSS（flexbox/grid）和原生 JS，不依賴外部框架（除非使用者指定）。\n"
        "3. 設計要美觀、響應式、有動畫效果。\n"
        "4. 只輸出程式碼，不要解釋。用 ```html 包裹。\n"
        "5. 如果是其他語言（Python/JS/etc），用對應的 code block 包裹。"
    )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"需求：{prompt}\n語言：{lang}"},
    ]
    try:
        reply = await _remote_chat_reply("groq", messages)
        if not reply:
            reply = await _remote_chat_reply("deepseek", messages)
        if not reply:
            reply = await _remote_chat_reply("ollama", messages)
        code = reply or ""
        # Extract code from markdown code block
        import re
        m = re.search(r"```(?:html|css|js|javascript|python|java|cpp)?\s*\n(.*?)```", code, re.DOTALL)
        if m:
            code = m.group(1).strip()
        return {"ok": True, "code": code, "raw": reply}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/jarvis/chat-history")
async def api_jarvis_chat_history(request: Request):
    """儲存/讀取對話紀錄（server-side persistence）。"""
    payload = await request.json()
    action = str((payload or {}).get("action", "list")).strip()
    history_dir = BRAIN_WORKSPACE / "chat_history"
    history_dir.mkdir(parents=True, exist_ok=True)

    if action == "save":
        chat_id = str((payload or {}).get("id", "")).strip() or f"chat_{uuid.uuid4().hex[:8]}"
        title = str((payload or {}).get("title", "")).strip() or "未命名對話"
        msgs = (payload or {}).get("messages", [])
        data = {"id": chat_id, "title": title, "messages": msgs, "updated": _now_iso()}
        (history_dir / f"{chat_id}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"ok": True, "id": chat_id}

    elif action == "load":
        chat_id = str((payload or {}).get("id", "")).strip()
        p = history_dir / f"{chat_id}.json"
        if not p.exists():
            return {"ok": False, "error": "not found"}
        return {"ok": True, **json.loads(p.read_text(encoding="utf-8"))}

    elif action == "delete":
        chat_id = str((payload or {}).get("id", "")).strip()
        p = history_dir / f"{chat_id}.json"
        if p.exists():
            p.unlink()
        return {"ok": True}

    else:  # list
        chats = []
        for f in sorted(history_dir.glob("chat_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                chats.append({"id": d.get("id", f.stem), "title": d.get("title", ""), "updated": d.get("updated", "")})
            except Exception:
                pass
        return {"ok": True, "chats": chats[:50]}


@app.get("/api/playbooks")
def api_playbook_list():
    items = _list_business_playbooks()
    return {"ok": True, "count": len(items), "playbooks": items}


@app.get("/api/playbooks/{playbook_id}")
def api_playbook_detail(playbook_id: str):
    pb = _load_business_playbook(playbook_id)
    if not pb:
        raise HTTPException(status_code=404, detail="playbook not found")
    return {"ok": True, "playbook": pb}


@app.post("/api/playbooks/{playbook_id}/run")
async def api_playbook_run(playbook_id: str, request: Request):
    payload = await request.json() if request else {}
    auto_run = bool((payload or {}).get("auto_run", True))
    context = str((payload or {}).get("context", "")).strip()
    overrides = (payload or {}).get("overrides", {})
    if not isinstance(overrides, dict):
        overrides = {}
    pb = _load_business_playbook(playbook_id)
    if not pb:
        raise HTTPException(status_code=404, detail="playbook not found")
    steps = pb.get("steps", [])
    if not isinstance(steps, list) or not steps:
        raise HTTPException(status_code=400, detail="playbook has no steps")

    route_id = f"P-{uuid.uuid4().hex[:8]}"
    created: list[dict] = []
    total = len(steps)
    for idx, raw_step in enumerate(steps, start=1):
        step = raw_step if isinstance(raw_step, dict) else {}
        merged_args = step.get("args", {})
        if not isinstance(merged_args, dict):
            merged_args = {}
        merged_args = {**merged_args, **overrides}
        step = {**step, "args": merged_args}
        task = _build_task_from_step(
            route_id=route_id,
            idx=idx,
            total=total,
            route_context=context or str(pb.get("description", "")),
            step=step,
            auto_run=auto_run,
        )
        task["playbook_id"] = str(pb.get("id") or playbook_id)
        task["playbook_name"] = str(pb.get("name") or playbook_id)
        task["logs"] = [f"{_now_iso()} | playbook task created"]
        tid = str(task.get("id", ""))
        agent_tasks[tid] = task
        created.append(task)
        if auto_run and tid:
            await agent_task_queue.put(tid)

    _save_agent_tasks()
    return {
        "ok": True,
        "route_id": route_id,
        "playbook_id": str(pb.get("id") or playbook_id),
        "playbook_name": str(pb.get("name") or playbook_id),
        "count": len(created),
        "tasks": created,
    }


# --- 智能管家（Task Butler）：全通訊收件 → 分類 → 建議 → 低風險自動執行、高風險待確認 ---
def _butler_inbox(limit_per_channel: int = 20) -> list[dict]:
    try:
        from brain_modules.task_butler import fetch_all_inbox
        return fetch_all_inbox(limit_per_channel=limit_per_channel)
    except Exception:
        return []


def _butler_run_one_round(limit_per_channel: int = 20, enqueue_auto_tasks: bool = True) -> dict:
    try:
        from brain_modules.task_butler import run_one_round
        return run_one_round(
            limit_per_channel=limit_per_channel,
            enqueue_auto_tasks=enqueue_auto_tasks,
            brain_api_base="http://127.0.0.1:8002",
        )
    except Exception as e:
        return {"ok": False, "error": str(e), "inbox_count": 0, "auto_tasks_created": [], "pending_confirm_count": 0}


@app.get("/api/butler/inbox")
def api_butler_inbox(limit: int = 20):
    """智能管家：取得各通道（Email/Discord/Telegram）近期訊息統一格式。"""
    items = _butler_inbox(limit_per_channel=max(1, min(50, limit)))
    return {"ok": True, "count": len(items), "messages": items}


@app.post("/api/butler/run")
async def api_butler_run(request: Request):
    """
    智能管家：執行一輪收件 → 分類 → 建議 → 低風險自動派工、高風險寫入待確認。
    body: { "limit": 20, "enqueue_auto_tasks": true }
    """
    payload = await request.json() if request else {}
    limit = max(1, min(50, int((payload or {}).get("limit", 20) or 20)))
    enqueue = bool((payload or {}).get("enqueue_auto_tasks", True))
    result = await asyncio.to_thread(_butler_run_one_round, limit_per_channel=limit, enqueue_auto_tasks=enqueue)
    return result


@app.get("/api/butler/pending")
def api_butler_pending():
    """智能管家：取得待確認清單（高/關鍵風險需人工確認後再派工）。"""
    pending_file = ROOT / "reports" / "task_butler_pending_confirm.json"
    if not pending_file.exists():
        return {"ok": True, "count": 0, "pending": []}
    try:
        data = json.loads(pending_file.read_text(encoding="utf-8", errors="ignore"))
        pending = data.get("pending", []) if isinstance(data, dict) else []
        return {"ok": True, "count": len(pending), "pending": pending}
    except Exception as e:
        return {"ok": False, "error": str(e), "count": 0, "pending": []}


@app.post("/api/graph-rag/ingest")
async def api_graph_rag_ingest(request: Request):
    """Graph RAG：將 PDF 匯入（轉圖 → VLM 描述 → 向量庫）。"""
    payload = await request.json() if request else {}
    pdf_path = str((payload or {}).get("pdf_path", "")).strip()
    source_name = str((payload or {}).get("source_name", "")).strip()
    if not pdf_path:
        raise HTTPException(status_code=400, detail="pdf_path is required")
    try:
        from brain_modules.brain_graph_rag import ingest_pdf
        from pathlib import Path
        p = Path(pdf_path).resolve()
        result = await asyncio.to_thread(ingest_pdf, p, source_name or p.stem)
        return {"ok": result.get("ok", False), "pages": result.get("pages", 0), "errors": result.get("errors", [])}
    except Exception as e:
        return {"ok": False, "pages": 0, "errors": [str(e)]}


@app.get("/api/graph-rag/search")
def api_graph_rag_search(q: str = "", limit: int = 5):
    """Graph RAG：搜尋圖表知識（配筋、搭接、施工大樣等）。"""
    if not q.strip():
        raise HTTPException(status_code=400, detail="q is required")
    try:
        from brain_modules.brain_graph_rag import search_graph_rag
        hits = search_graph_rag(q.strip(), limit=max(1, min(10, limit)))
        return {"ok": True, "count": len(hits), "hits": hits}
    except Exception as e:
        return {"ok": False, "count": 0, "hits": [], "error": str(e)}


@app.post("/api/agent/tasks/local-command")
async def api_agent_local_command(request: Request):
    """
    本地命令任務（主機端執行）：
    - 允許常規操作
    - 關機/重開/格式化/自毀類指令由主機橋接安全策略封鎖
    """
    payload = await request.json()
    command = str((payload or {}).get("command", "")).strip()
    timeout_sec = int((payload or {}).get("timeout", 180) or 180)
    if not command:
        raise HTTPException(status_code=400, detail="command is required")

    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {
        "id": task_id,
        "objective": f"執行本地命令：{command}",
        "provider": "desktop",
        "execution": "host_script",
        "job_type": "host_command",
        "status": "queued",
        "context": "本地命令執行（含安全封鎖策略）",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "result": "",
        "logs": [f"{_now_iso()} | local-command task created"],
        "args": {"command": command, "timeout": max(10, min(600, timeout_sec))},
    }
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@app.post("/api/agent/tasks/local-python")
async def api_agent_local_python(request: Request):
    payload = await request.json()
    script_path = str((payload or {}).get("script_path", "")).strip()
    script_args = (payload or {}).get("script_args", [])
    timeout_sec = int((payload or {}).get("timeout", 240) or 240)
    if not script_path:
        raise HTTPException(status_code=400, detail="script_path is required")
    if not isinstance(script_args, list):
        script_args = []

    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {
        "id": task_id,
        "objective": f"執行本地 Python 腳本：{script_path}",
        "provider": "desktop",
        "execution": "host_script",
        "job_type": "host_python",
        "status": "queued",
        "context": "本地 Python 腳本執行",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "result": "",
        "logs": [f"{_now_iso()} | local-python task created"],
        "args": {
            "script_path": script_path,
            "script_args": [str(x) for x in script_args],
            "timeout": max(10, min(900, timeout_sec)),
        },
    }
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@app.get("/api/progress")
def api_progress():
    """回傳 web_admin_progress.json 內容，供管理介面輪詢或初次載入。"""
    try:
        if PROGRESS_FILE.exists():
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8", errors="replace"))
            return {"ok": True, "data": data.get("data", ""), "updated": data.get("updated", "")}
    except (json.JSONDecodeError, OSError):
        pass
    return {"ok": True, "data": "", "updated": ""}


@app.get("/api/agents")
def api_agents():
    """各引擎可用性（Gemini/Ollama 等），供管理介面動態顯示在線/離線。"""
    gemini_ok = bool(os.environ.get("GEMINI_API_KEY", "").strip() and os.environ.get("GEMINI_API_KEY", "").strip() != "your-gemini-api-key")
    ollama_ok = False
    try:
        import urllib.request
        req = urllib.request.Request(os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as r:
            ollama_ok = r.status == 200
    except Exception:
        pass
    claude_ok = bool((os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY") or "").strip())
    return {
        "Gemini Admin": {"online": gemini_ok, "role": "複雜決策/管理員"},
        "Claude Dev": {"online": claude_ok, "role": "編碼/修正"},
        "Ollama Local": {"online": ollama_ok, "role": "地端檢核"},
        "Media Gen": {"online": bool(os.environ.get("XAI_API_KEY", "").strip()), "role": "Jimeng/Grok"},
    }


# ── Agent 記憶 API（memU 整合）──
try:
    from memu_bridge import get_memu_agent_memory, get_memu_service, memorize as memu_memorize, retrieve as memu_retrieve
    from agent_memory import get_agent_memory
    AGENT_MEMORY_AVAILABLE = True
    MEMU_AVAILABLE = True
except ImportError:
    try:
        from agent_memory import get_agent_memory
        AGENT_MEMORY_AVAILABLE = True
    except ImportError:
        AGENT_MEMORY_AVAILABLE = False
    MEMU_AVAILABLE = False


@app.get("/api/agent/memory/context")
async def api_agent_memory_context():
    """取得 Agent 記憶上下文"""
    if not AGENT_MEMORY_AVAILABLE:
        return {"ok": False, "error": "記憶模組未安裝"}
    memory = get_memu_agent_memory("jarvis") if MEMU_AVAILABLE else get_agent_memory("jarvis")
    return {
        "ok": True,
        "context": memory.get_context_summary(),
        "preferences": memory.get_user_preferences(),
        "engine": "memU" if MEMU_AVAILABLE else "legacy",
    }


@app.post("/api/agent/memory/store")
async def api_agent_memory_store(request: Request):
    """儲存互動到 Agent 記憶（memU + legacy 雙寫）"""
    if not AGENT_MEMORY_AVAILABLE:
        return {"ok": False, "error": "記憶模組未安裝"}
    payload = await request.json()
    user_input = str((payload or {}).get("user_input", "")).strip()
    ai_response = str((payload or {}).get("ai_response", "")).strip()
    session_id = str((payload or {}).get("session_id", "")).strip() or None
    
    if not user_input or not ai_response:
        return {"ok": False, "error": "user_input 和 ai_response 為必填"}
    
    memory = get_memu_agent_memory("jarvis") if MEMU_AVAILABLE else get_agent_memory("jarvis")
    memory.store_interaction(user_input, ai_response, session_id)
    return {"ok": True, "engine": "memU" if MEMU_AVAILABLE else "legacy"}


@app.post("/api/agent/memory/search")
async def api_agent_memory_search(request: Request):
    """搜尋 Agent 記憶"""
    if not AGENT_MEMORY_AVAILABLE:
        return {"ok": False, "error": "記憶模組未安裝"}
    payload = await request.json()
    query = str((payload or {}).get("query", "")).strip()
    limit = int((payload or {}).get("limit", 5))
    
    if not query:
        return {"ok": False, "error": "query 為必填"}
    
    memory = get_memu_agent_memory("jarvis") if MEMU_AVAILABLE else get_agent_memory("jarvis")
    results = memory.search_memory(query, limit)
    return {"ok": True, "results": results, "engine": "memU" if MEMU_AVAILABLE else "legacy"}


@app.post("/api/agent/memory/clear")
async def api_agent_memory_clear(request: Request):
    """清除 Agent 記憶"""
    if not AGENT_MEMORY_AVAILABLE:
        return {"ok": False, "error": "記憶模組未安裝"}
    memory = get_memu_agent_memory("jarvis") if MEMU_AVAILABLE else get_agent_memory("jarvis")
    memory.clear_session()
    return {"ok": True}


@app.get("/api/agent/memory/recent")
async def api_agent_memory_recent(limit: int = 10):
    """取得最近記憶"""
    if not AGENT_MEMORY_AVAILABLE:
        return {"ok": False, "error": "記憶模組未安裝"}
    memory = get_memu_agent_memory("jarvis") if MEMU_AVAILABLE else get_agent_memory("jarvis")
    recent = memory.get_recent_context(limit)
    return {"ok": True, "recent": recent}


# ── memU 進階 API（語意記憶 + 檢索）──
@app.post("/api/memu/memorize")
async def api_memu_memorize(request: Request):
    """將內容寫入 memU 記憶（自動分類 + 向量化）"""
    if not MEMU_AVAILABLE:
        return {"ok": False, "error": "memU 未安裝"}
    payload = await request.json()
    content = str((payload or {}).get("content", "")).strip()
    user_id = str((payload or {}).get("user_id", "default")).strip()
    if not content:
        return {"ok": False, "error": "content 為必填"}
    result = await memu_memorize(content=content, user_id=user_id)
    return result


@app.post("/api/memu/retrieve")
async def api_memu_retrieve(request: Request):
    """從 memU 記憶中語意檢索"""
    if not MEMU_AVAILABLE:
        return {"ok": False, "error": "memU 未安裝"}
    payload = await request.json()
    query = str((payload or {}).get("query", "")).strip()
    user_id = str((payload or {}).get("user_id", "default")).strip()
    if not query:
        return {"ok": False, "error": "query 為必填"}
    result = await memu_retrieve(query=query, user_id=user_id)
    return result


@app.get("/api/memu/status")
async def api_memu_status():
    """取得 memU 狀態"""
    return {
        "ok": True,
        "memu_available": MEMU_AVAILABLE,
        "engine": "memU + Ollama (local)" if MEMU_AVAILABLE else "legacy JSONL",
        "features": [
            "proactive_memory", "semantic_search", "auto_categorization",
            "pattern_detection", "context_prediction",
        ] if MEMU_AVAILABLE else ["keyword_search", "jsonl_storage"],
    }


# ── AI 用量警報 API ──
try:
    from ai_usage_alerts import alerts_manager
    USAGE_ALERTS_AVAILABLE = True
except ImportError:
    USAGE_ALERTS_AVAILABLE = False


@app.get("/api/usage/alerts")
async def api_usage_alerts():
    """取得用量警報"""
    if not USAGE_ALERTS_AVAILABLE:
        return {"ok": False, "error": "警報模組未安裝"}
    alerts = alerts_manager.get_recent_alerts()
    return {"ok": True, "alerts": alerts}


@app.get("/api/usage/alerts/check")
async def api_usage_alerts_check():
    """檢查並返回警報"""
    if not USAGE_ALERTS_AVAILABLE:
        return {"ok": False, "error": "警報模組未安裝"}
    try:
        from ai_usage_tracker import usage_tracker
        stats = usage_tracker.get_today_stats()
        alerts = alerts_manager.check_usage(stats)
        return {"ok": True, "alerts": alerts}
    except ImportError:
        return {"ok": False, "error": "用量追蹤模組未安裝"}


@app.post("/api/usage/alerts/threshold")
async def api_usage_alerts_threshold(request: Request):
    """設定警報閾值"""
    if not USAGE_ALERTS_AVAILABLE:
        return {"ok": False, "error": "警報模組未安裝"}
    payload = await request.json()
    provider = str((payload or {}).get("provider", "")).strip().lower()
    value = float((payload or {}).get("value", 0))
    
    if provider and value > 0:
        alerts_manager.set_threshold(provider, value)
        return {"ok": True, "message": f"已設定 {provider} 閾值為 ${value}"}
    return {"ok": False, "error": "provider 和 value 為必填"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.add(websocket)

    async def send_to_client(message):
        await websocket.send_json(message)

    manager = AgentManager(
        gemini_service=gemini_ai,
        ollama_service=ollama_ai,
        max_turns=10,
    )

    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            user_input = request.get("text", "") or request.get("message", "")

            if not user_input:
                continue

            # 觸發八階段工作流；進度與結果即時推播
            await manager.run(user_input, send_message=send_to_client)

    except WebSocketDisconnect:
        ws_clients.discard(websocket)
        logging.info("Client disconnected")
    except json.JSONDecodeError:
        try:
            await websocket.send_json({"type": "error", "content": "請傳送 JSON，含 text 或 message 欄位"})
        except Exception:
            pass
    except Exception as e:
        logging.error("WS 異常: %s\n%s", e, traceback.format_exc())
        try:
            await websocket.send_json({"type": "error", "content": f"系統異常: {str(e)}"})
        except Exception:
            pass


# ── Ntfy 推播 API ──────────────────────────────────────────────
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://notify.zhe-wei.net").rstrip("/")
NTFY_ADMIN_USER = os.environ.get("NTFY_ADMIN_USER", "").strip()
NTFY_ADMIN_PASS = os.environ.get("NTFY_ADMIN_PASS", "").strip()
NTFY_DEFAULT_TOPIC = os.environ.get("NTFY_DEFAULT_TOPIC", "zhewei_general").strip()


def _ntfy_publish(topic: str, title: str, message: str, priority: int = 3,
                  tags: list | None = None, click: str = "", attach: str = "") -> dict:
    """發送推播到 Ntfy server。"""
    import urllib.request
    url = f"{NTFY_SERVER}/{topic}"
    payload = {"topic": topic, "title": title, "message": message, "priority": priority}
    if tags:
        payload["tags"] = tags
    if click:
        payload["click"] = click
    if attach:
        payload["attach"] = attach
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if NTFY_ADMIN_USER and NTFY_ADMIN_PASS:
        import base64
        cred = base64.b64encode(f"{NTFY_ADMIN_USER}:{NTFY_ADMIN_PASS}".encode()).decode()
        headers["Authorization"] = f"Basic {cred}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"ok": True, **json.loads(resp.read().decode("utf-8"))}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/ntfy/send")
async def api_ntfy_send(request: Request):
    """發送推播通知（僅 admin+）。"""
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    payload = await request.json()
    topic = str((payload or {}).get("topic", "")).strip() or NTFY_DEFAULT_TOPIC
    title = str((payload or {}).get("title", "")).strip()
    message = str((payload or {}).get("message", "")).strip()
    priority = int((payload or {}).get("priority", 3))
    tags = (payload or {}).get("tags", [])
    click = str((payload or {}).get("click", "")).strip()
    attach = str((payload or {}).get("attach", "")).strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    result = _ntfy_publish(topic, title, message, priority,
                           tags if isinstance(tags, list) else [], click, attach)
    return result


@app.post("/api/ntfy/broadcast")
async def api_ntfy_broadcast(request: Request):
    """廣播推播到多個 topic（僅 admin+）。"""
    data = _extract_token(request)
    if not data or data.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    payload = await request.json()
    topics = (payload or {}).get("topics", [])
    title = str((payload or {}).get("title", "")).strip()
    message = str((payload or {}).get("message", "")).strip()
    priority = int((payload or {}).get("priority", 3))
    tags = (payload or {}).get("tags", [])
    if not message or not topics:
        raise HTTPException(status_code=400, detail="topics and message are required")
    results = {}
    for t in topics:
        t = str(t).strip()
        if t:
            results[t] = _ntfy_publish(t, title, message, priority,
                                       tags if isinstance(tags, list) else [])
    return {"ok": True, "results": results, "count": len(results)}


@app.get("/api/ntfy/config")
async def api_ntfy_config():
    """回傳前端推播模組所需的公開配置（不含密碼）。"""
    return {
        "ok": True,
        "server": NTFY_SERVER,
        "default_topic": NTFY_DEFAULT_TOPIC,
        "user": os.environ.get("NTFY_CLIENT_USER", "client_general"),
        "brand": "哲維通知",
    }


# ── 虛擬人物 MV 製作 API ───────────────────────────────────────
@app.post("/api/mv/create")
async def api_mv_create(request: Request):
    """建立 MV 專案。"""
    data = await request.json()
    name = str(data.get("name", "")).strip()
    character_path = str(data.get("character_path", "")).strip()
    audio_path = str(data.get("audio_path", "")).strip()
    if not all([name, character_path, audio_path]):
        raise HTTPException(status_code=400, detail="name, character_path, audio_path required")
    try:
        from ai_modules.virtual_mv_service import handle_create_project
        return handle_create_project({"name": name, "character_path": character_path, "audio_path": audio_path})
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/mv/generate-character")
async def api_mv_generate_character(request: Request):
    """生成角色圖片（返回 ComfyUI 指令）。"""
    data = await request.json()
    prompt = str(data.get("prompt", "")).strip()
    negative_prompt = str(data.get("negative_prompt", "text, watermark, blurry, low quality")).strip()
    width = int(data.get("width", 512))
    height = int(data.get("height", 512))
    try:
        from ai_modules.virtual_mv_service import handle_generate_character
        return handle_generate_character({"prompt": prompt, "negative_prompt": negative_prompt, "width": width, "height": height})
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/mv/run-liveportrait")
async def api_mv_run_liveportrait(request: Request):
    """執行 LivePortrait 角色動畫。"""
    data = await request.json()
    project_name = str(data.get("project_name", "")).strip()
    driving_video = str(data.get("driving_video", "")).strip() if data.get("driving_video") else None
    try:
        from ai_modules.virtual_mv_service import handle_run_liveportrait
        return handle_run_liveportrait({"project_name": project_name, "driving_video": driving_video})
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/mv/run-wav2lip")
async def api_mv_run_wav2lip(request: Request):
    """執行 Wav2Lip 對口型。"""
    data = await request.json()
    project_name = str(data.get("project_name", "")).strip()
    try:
        from ai_modules.virtual_mv_service import handle_run_wav2lip
        return handle_run_wav2lip({"project_name": project_name})
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/mv/run-composite")
async def api_mv_run_composite(request: Request):
    """執行 FFmpeg 合成最終 MV。"""
    data = await request.json()
    project_name = str(data.get("project_name", "")).strip()
    try:
        from ai_modules.virtual_mv_service import handle_run_composite
        return handle_run_composite({"project_name": project_name})
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/mv/projects")
async def api_mv_list_projects():
    """列出所有 MV 專案。"""
    try:
        from ai_modules.virtual_mv_service import handle_list_projects
        return handle_list_projects()
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/mv/status/{project_name}")
async def api_mv_get_status(project_name: str):
    try:
        from ai_modules.virtual_mv_service import handle_get_status
        return handle_get_status({"project_name": project_name})
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.on_event("startup")
async def startup():
    _load_agent_tasks()
    asyncio.create_task(broadcast_progress())
    asyncio.create_task(_agent_worker_loop())


# ── 檔案傳輸 API ────────────────────────────────────────────
TRANSFER_DIR = BRAIN_WORKSPACE / "transfer_files"
TRANSFER_DIR.mkdir(exist_ok=True)
PAIR_CODES = {}
TRANSFER_SESSIONS = {}


def generate_pair_code():
    import random
    return ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=6))


@app.post("/api/transfer/pair")
async def api_transfer_pair(request: Request):
    """配對電腦與手機。"""
    data = await request.json()
    pair_code = data.get('pairCode', '').upper()
    is_receiver = data.get('isReceiver', False)

    if is_receiver:
        if pair_code not in PAIR_CODES:
            return {"success": False, "error": "配對碼無效或已過期"}
        transfer_id = PAIR_CODES[pair_code]['transferId']
        TRANSFER_SESSIONS[transfer_id] = PAIR_CODES[pair_code]
        del PAIR_CODES[pair_code]
        return {"success": True, "transferId": transfer_id, "deviceName": PAIR_CODES.get(pair_code, {}).get('deviceName', '手機')}
    else:
        if len(pair_code) != 6:
            return {"success": False, "error": "配對碼必須是6位"}
        transfer_id = str(uuid.uuid4())[:8]
        PAIR_CODES[pair_code] = {
            'transferId': transfer_id,
            'deviceName': socket.gethostname(),
            'createdAt': datetime.now()
        }
        return {"success": True, "transferId": transfer_id}


@app.post("/api/transfer/upload")
async def api_transfer_upload(request: Request):
    """上傳檔案到手機。"""
    form = await request.form()
    device_id = form.get('deviceId', 'any')
    files = form.getlist('files')

    if not files:
        return {"success": False, "error": "沒有檔案"}

    transfer_id = None
    for tid, session in TRANSFER_SESSIONS.items():
        if device_id == 'any' or session.get('transferId') == device_id:
            transfer_id = tid
            break

    if not transfer_id:
        return {"success": False, "error": "沒有配對的手機"}

    uploaded = []
    for file in files:
        file_id = str(uuid.uuid4())[:8]
        ext = Path(file.filename).suffix
        filename = f"{file_id}{ext}"
        filepath = TRANSFER_DIR / filename
        content = await file.read()
        filepath.write_bytes(content)

        record = {
            'id': file_id,
            'name': file.filename,
            'type': file.content_type,
            'size': len(content),
            'createdAt': datetime.now().isoformat()
        }
        session_file_db = TRANSFER_DIR / f"{transfer_id}_files.json"
        if session_file_db.exists():
            records = json.loads(session_file_db.read_text())
        else:
            records = {'files': [], 'texts': []}
        records['files'].append(record)
        session_file_db.write_text(json.dumps(records, ensure_ascii=False))
        uploaded.append(record)

    # Ntfy 推播通知
    try:
        ntfy_topic = f"transfer_{transfer_id}"
        ntfy_url = os.environ.get("NTFY_SERVER", "https://notify.zhe-wei.net")
        ntfy_user = os.environ.get("NTFY_ADMIN_USER")
        ntfy_pass = os.environ.get("NTFY_ADMIN_PASS")
        import httpx
        auth = (ntfy_user, ntfy_pass) if ntfy_user and ntfy_pass else None
        httpx.post(f"{ntfy_url}/publish", json={
            "topic": ntfy_topic,
            "title": "📱 新檔案",
            "body": f"收到 {len(files)} 個檔案，請打開 App 查看",
            "tags": ["file", "incoming"]
        }, auth=auth, timeout=10)
    except Exception as e:
        logging.warning(f"Ntfy 推播失敗: {e}")

    return {"success": True, "files": uploaded}


@app.post("/api/transfer/text")
async def api_transfer_text(request: Request):
    """傳送文字到手機。"""
    data = await request.json()
    text = data.get('text', '')
    device_id = data.get('deviceId', 'any')

    transfer_id = None
    for tid, session in TRANSFER_SESSIONS.items():
        if device_id == 'any' or session.get('transferId') == device_id:
            transfer_id = tid
            break

    if not transfer_id:
        return {"success": False, "error": "沒有配對的手機"}

    record = {'id': str(uuid.uuid4())[:8], 'text': text, 'createdAt': datetime.now().isoformat()}
    session_file_db = TRANSFER_DIR / f"{transfer_id}_files.json"
    if session_file_db.exists():
        records = json.loads(session_file_db.read_text())
    else:
        records = {'files': [], 'texts': []}
    records['texts'].append(record)
    session_file_db.write_text(json.dumps(records, ensure_ascii=False))

    # Ntfy 推播通知
    try:
        ntfy_topic = f"transfer_{transfer_id}"
        ntfy_url = os.environ.get("NTFY_SERVER", "https://notify.zhe-wei.net")
        ntfy_user = os.environ.get("NTFY_ADMIN_USER")
        ntfy_pass = os.environ.get("NTFY_ADMIN_PASS")
        import httpx
        auth = (ntfy_user, ntfy_pass) if ntfy_user and ntfy_pass else None
        httpx.post(f"{ntfy_url}/publish", json={
            "topic": ntfy_topic,
            "title": "💬 新訊息",
            "body": text[:50] + ('...' if len(text) > 50 else ''),
            "tags": ["message"]
        }, auth=auth, timeout=10)
    except Exception as e:
        logging.warning(f"Ntfy 推播失敗: {e}")

    return {"success": True}


@app.get("/api/transfer/list/{transfer_id}")
async def api_transfer_list(transfer_id: str):
    """取得該配對的檔案列表。"""
    session_file_db = TRANSFER_DIR / f"{transfer_id}_files.json"
    if not session_file_db.exists():
        return {"files": [], "texts": []}
    records = json.loads(session_file_db.read_text())
    return {"files": records.get('files', []), "texts": records.get('texts', [])}


@app.get("/api/transfer/download/{file_id}")
async def api_transfer_download(file_id: str):
    """下載檔案。"""
    for fpath in TRANSFER_DIR.glob("*"):
        if fpath.stem == file_id:
            return FileResponse(str(fpath), filename=fpath.name)
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("檔案不存在", status_code=404)


@app.get("/api/transfer/history")
async def api_transfer_history(request: Request):
    """取得傳送歷史。"""
    return {"items": []}


@app.get("/pwa")
async def get_pwa(request: Request):
    """PWA 可攜式 AI 助手入口。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "pwa" / "index.html"
        if p.exists():
            return FileResponse(str(p), media_type="text/html")
    return PlainTextResponse("pwa/index.html not found", status_code=404)


@app.get("/pwa/{path:path}")
async def get_pwa_static(path: str):
    """PWA 靜態資源。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "pwa" / path
        if p.exists() and p.is_file():
            media = None
            if path.endswith(".js"):
                media = "application/javascript"
            elif path.endswith(".json"):
                media = "application/json"
            elif path.endswith(".png"):
                media = "image/png"
            return FileResponse(str(p), media_type=media)
    return PlainTextResponse("not found", status_code=404)


@app.get("/app")
async def get_app_platform(request: Request):
    """統一應用平台（需登入，所有功能統一入口）。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "app.html"
        if p.exists():
            return FileResponse(str(p))
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("app.html not found", status_code=404)


@app.get("/transfer")
async def get_transfer_page(request: Request):
    """電腦端上傳頁面。"""
    auth = _require_auth(request)
    if isinstance(auth, RedirectResponse):
        return auth
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "transfer.html"
        if p.exists():
            return FileResponse(str(p))
    return PlainTextResponse("transfer.html not found", status_code=404)


@app.get("/transfer-receive.html")
async def get_transfer_receive_page():
    """手機端接收頁面（無需認證）。"""
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "transfer-receive.html"
        if p.exists():
            return FileResponse(str(p))
    return PlainTextResponse("transfer-receive.html not found", status_code=404)


@app.on_event("startup")
async def startup():
    _load_agent_tasks()
    asyncio.create_task(broadcast_progress())
    asyncio.create_task(_agent_worker_loop())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    PORT = int(os.environ.get("PORT", os.environ.get("BRAIN_WS_PORT", "8002")))
    uvicorn.run(app, host="0.0.0.0", port=PORT)

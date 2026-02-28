# -*- coding: utf-8 -*-
"""築未科技 — memU 記憶 + Ntfy 推播 + Agent Memory Router"""
import asyncio
import base64
import json
import os

from fastapi import APIRouter, Request, HTTPException
from routers.deps import _extract_token, _require_admin, logger

router = APIRouter(tags=["擴充功能"])

# ── memU + Agent Memory ──
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


@router.get("/api/agent/memory/context")
async def api_agent_memory_context():
    if not AGENT_MEMORY_AVAILABLE:
        return {"ok": False, "error": "記憶模組未安裝"}
    memory = get_memu_agent_memory("jarvis") if MEMU_AVAILABLE else get_agent_memory("jarvis")
    return {"ok": True, "context": memory.get_context_summary(), "preferences": memory.get_user_preferences(), "engine": "memU" if MEMU_AVAILABLE else "legacy"}


@router.post("/api/agent/memory/store")
async def api_agent_memory_store(request: Request):
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


@router.post("/api/agent/memory/search")
async def api_agent_memory_search(request: Request):
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


@router.post("/api/agent/memory/clear")
async def api_agent_memory_clear(request: Request):
    if not AGENT_MEMORY_AVAILABLE:
        return {"ok": False, "error": "記憶模組未安裝"}
    memory = get_memu_agent_memory("jarvis") if MEMU_AVAILABLE else get_agent_memory("jarvis")
    memory.clear_session()
    return {"ok": True}


@router.get("/api/agent/memory/recent")
async def api_agent_memory_recent(limit: int = 10):
    if not AGENT_MEMORY_AVAILABLE:
        return {"ok": False, "error": "記憶模組未安裝"}
    memory = get_memu_agent_memory("jarvis") if MEMU_AVAILABLE else get_agent_memory("jarvis")
    return {"ok": True, "recent": memory.get_recent_context(limit)}


# ── memU 進階 ──
@router.post("/api/memu/memorize")
async def api_memu_memorize(request: Request):
    if not MEMU_AVAILABLE:
        return {"ok": False, "error": "memU 未安裝"}
    payload = await request.json()
    content = str((payload or {}).get("content", "")).strip()
    user_id = str((payload or {}).get("user_id", "default")).strip()
    if not content:
        return {"ok": False, "error": "content 為必填"}
    return await memu_memorize(content=content, user_id=user_id)


@router.post("/api/memu/retrieve")
async def api_memu_retrieve(request: Request):
    if not MEMU_AVAILABLE:
        return {"ok": False, "error": "memU 未安裝"}
    payload = await request.json()
    query = str((payload or {}).get("query", "")).strip()
    user_id = str((payload or {}).get("user_id", "default")).strip()
    if not query:
        return {"ok": False, "error": "query 為必填"}
    return await memu_retrieve(query=query, user_id=user_id)


@router.get("/api/memu/status")
async def api_memu_status():
    return {"ok": True, "memu_available": MEMU_AVAILABLE, "engine": "memU + Ollama (local)" if MEMU_AVAILABLE else "legacy JSONL", "features": ["proactive_memory", "semantic_search", "auto_categorization", "pattern_detection", "context_prediction"] if MEMU_AVAILABLE else ["keyword_search", "jsonl_storage"]}


# ── Ntfy 推播 ──
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://notify.zhe-wei.net").rstrip("/")
NTFY_ADMIN_USER = os.environ.get("NTFY_ADMIN_USER", "").strip()
NTFY_ADMIN_PASS = os.environ.get("NTFY_ADMIN_PASS", "").strip()
NTFY_DEFAULT_TOPIC = os.environ.get("NTFY_DEFAULT_TOPIC", "zhewei_general").strip()


def _ntfy_publish(topic: str, title: str, message: str, priority: int = 3, tags: list | None = None, click: str = "", attach: str = "") -> dict:
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
        cred = base64.b64encode(f"{NTFY_ADMIN_USER}:{NTFY_ADMIN_PASS}".encode()).decode()
        headers["Authorization"] = f"Basic {cred}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"ok": True, **json.loads(resp.read().decode("utf-8"))}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/ntfy/send")
async def api_ntfy_send(request: Request):
    _require_admin(request)
    payload = await request.json()
    topic = str((payload or {}).get("topic", NTFY_DEFAULT_TOPIC)).strip()
    title = str((payload or {}).get("title", "")).strip()
    message = str((payload or {}).get("message", "")).strip()
    priority = int((payload or {}).get("priority", 3))
    tags = (payload or {}).get("tags")
    if not message:
        raise HTTPException(400, "message is required")
    return _ntfy_publish(topic, title, message, priority, tags, str((payload or {}).get("click", "")), str((payload or {}).get("attach", "")))


@router.post("/api/ntfy/broadcast")
async def api_ntfy_broadcast(request: Request):
    _require_admin(request)
    payload = await request.json()
    topics = (payload or {}).get("topics", [NTFY_DEFAULT_TOPIC])
    title = str((payload or {}).get("title", "")).strip()
    message = str((payload or {}).get("message", "")).strip()
    priority = int((payload or {}).get("priority", 3))
    if not message:
        raise HTTPException(400, "message is required")
    results = []
    for t in topics:
        results.append({"topic": t, **_ntfy_publish(str(t).strip(), title, message, priority)})
    return {"ok": True, "results": results}


@router.get("/api/ntfy/config")
async def api_ntfy_config():
    return {"ok": True, "server": NTFY_SERVER, "default_topic": NTFY_DEFAULT_TOPIC, "client_user": os.environ.get("NTFY_CLIENT_USER", "client_general")}

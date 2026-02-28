# -*- coding: utf-8 -*-
"""築未科技 — 智慧遙控 + 對話遙控 + Vision Edge Router"""
import asyncio
import json
import os
import sys

from fastapi import APIRouter, Request, HTTPException
from routers.deps import (
    _extract_token, _provider_alias, _remote_chat_reply, _clean_model_output,
    smart_ai, remote_sessions, logger, ROOT, ChatRequest,
)

router = APIRouter(tags=["智慧遙控"])

SMART_REMOTE_LOCK = asyncio.Lock()
CONVERSATION_LOCK = asyncio.Lock()
VISION_EDGE_URL = os.environ.get("VISION_EDGE_URL", "http://localhost:8015")


def _proxy_vision(path: str, method: str = "GET", params: dict = None, json_body: dict = None):
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


# ── Smart Remote Agent ──
@router.post("/api/smart/execute")
async def api_smart_execute(request: Request):
    body = await request.json()
    instruction = body.get("instruction", "").strip()
    execute = body.get("execute", True)
    provider = body.get("provider", "gemini")
    if not instruction:
        return {"ok": False, "error": "instruction 必填"}
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from smart_remote_agent import SmartRemoteAgent
        async with SMART_REMOTE_LOCK:
            agent = SmartRemoteAgent(llm_provider=provider)
            result = agent.run(instruction, execute=execute)
        return {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/smart/analyze")
async def api_smart_analyze(request: Request):
    body = await request.json()
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from smart_remote_agent import SmartRemoteAgent
        agent = SmartRemoteAgent()
        return {"ok": True, "analysis": agent.analyze_screen(body.get("focus_area", "全螢幕"))}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/smart/ask")
async def api_smart_ask(request: Request):
    body = await request.json()
    question = body.get("question", "").strip()
    if not question:
        return {"ok": False, "error": "question 必填"}
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from smart_remote_agent import SmartRemoteAgent
        return {"ok": True, "answer": SmartRemoteAgent().ask(question)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/smart/status")
async def api_smart_status():
    return {"ok": True, "features": ["自然語言理解", "多步驟任務規劃", "VLM 視覺分析", "智慧檔案搜尋", "GUI 自動化"], "providers": ["gemini", "claude", "ollama", "deepseek", "groq"]}


# ── Conversational Remote ──
@router.post("/api/chat/remote")
async def api_chat_remote(request: Request):
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


@router.get("/api/chat/remote/history")
async def api_chat_remote_history(limit: int = 20):
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from conversational_remote import ConversationalRemote
        return {"ok": True, "history": ConversationalRemote().get_conversation_history(limit)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/chat/remote/clear")
async def api_chat_remote_clear():
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from conversational_remote import ConversationalRemote
        ConversationalRemote().clear_history()
        return {"ok": True, "message": "對話歷史已清除"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/chat/remote/status")
async def api_chat_remote_status():
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from conversational_remote import ConversationalRemote
        return {"ok": True, "features": ["自然語言對話", "意圖理解", "動作規劃", "執行回覆", "對話歷史"], "system_status": ConversationalRemote().get_system_status()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Remote Chat (Agent Hub) ──
@router.post("/api/remote/chat")
async def api_remote_chat(request: Request):
    payload = await request.json()
    provider_raw = str((payload or {}).get("provider", "ollama"))
    message = str((payload or {}).get("message", "")).strip()
    session_id = str((payload or {}).get("session_id", "default")).strip() or "default"
    max_turns = max(2, min(20, int((payload or {}).get("max_turns", 10) or 10)))
    if not message:
        raise HTTPException(400, "message is required")
    provider_effective, provider_mapping = _provider_alias(provider_raw)
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
    return {"ok": True, "session_id": session_id, "provider_requested": provider_raw, "provider_effective": provider_effective, "provider_mapping": provider_mapping, "reply": reply_clean}


# ── Vision Edge ──
@router.get("/api/vision/health")
async def api_vision_health():
    return _proxy_vision("/health")


@router.get("/api/vision/stats")
async def api_vision_stats():
    return _proxy_vision("/api/vision/stats")


@router.get("/api/vision/history")
async def api_vision_history(limit: int = 20):
    return _proxy_vision("/api/vision/history", params={"limit": limit})


@router.get("/api/vision/monitor/status")
async def api_vision_monitor_status():
    return _proxy_vision("/api/monitor/status")


@router.get("/api/vision/monitor/alerts")
async def api_vision_monitor_alerts(limit: int = 50, level: str = ""):
    return _proxy_vision("/api/monitor/alerts", params={"limit": limit, "level": level})


@router.get("/api/vision/knowledge/search")
async def api_vision_kb_search(q: str = "", limit: int = 10):
    return _proxy_vision("/api/vision/knowledge/search", params={"q": q, "limit": limit})

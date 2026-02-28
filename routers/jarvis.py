# -*- coding: utf-8 -*-
"""築未科技 — Jarvis AI 服務 Router (生圖/學習/角色/工作流/代碼生成/對話紀錄)"""
import asyncio
import json
import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from routers.deps import (
    _remote_chat_reply, _now_iso, _extract_token,
    logger, ROOT, BRAIN_WORKSPACE,
    ImageGenRequest, LearnRequest, SearchRequest,
)

router = APIRouter(tags=["Jarvis AI"])


@router.post("/api/jarvis/generate-image")
async def api_jarvis_generate_image(body: ImageGenRequest):
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "ai_modules"))
        from ai_creative_tools import text_to_image
        result = await asyncio.to_thread(text_to_image, body.prompt, body.filename)
        return {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/jarvis/analyze-image")
async def api_jarvis_analyze_image(request: Request):
    payload = await request.json()
    image = str((payload or {}).get("image", "")).strip()
    prompt = str((payload or {}).get("prompt", "請描述這張圖片的內容")).strip()
    if not image:
        return {"ok": False, "error": "image is required"}
    try:
        import google.generativeai as genai
        import base64
        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
        if not GEMINI_API_KEY:
            return {"ok": False, "error": "未設定 GEMINI_API_KEY"}
        genai.configure(api_key=GEMINI_API_KEY)
        if image.startswith("data:image"):
            image = image.split(",", 1)[1]
        image_data = base64.b64decode(image)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([prompt, {"inline_data": {"mime_type": "image/png", "data": image_data}}])
        return {"ok": True, "result": response.text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/jarvis/ask-and-learn")
async def api_jarvis_ask_and_learn(request: Request):
    payload = await request.json()
    question = str((payload or {}).get("question", "")).strip()
    providers = (payload or {}).get("providers", ["gemini", "claude", "grok"])
    if not question:
        raise HTTPException(400, "question is required")
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "Jarvis_Training"))
        from learn_from_giants import ask_and_learn
        result = await asyncio.to_thread(ask_and_learn, question, providers, True)
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/jarvis/batch-learn")
async def api_jarvis_batch_learn(request: Request):
    payload = await request.json()
    topics = (payload or {}).get("topics", [])
    providers = (payload or {}).get("providers", ["gemini", "claude", "grok"])
    if not topics or not isinstance(topics, list):
        raise HTTPException(400, "topics (list) is required")
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "Jarvis_Training"))
        from learn_from_giants import batch_learn
        result = await asyncio.to_thread(batch_learn, topics[:20], providers)
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/jarvis/learning-stats")
def api_jarvis_learning_stats():
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "Jarvis_Training"))
        from learn_from_giants import learning_stats
        return {"ok": True, **learning_stats()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/jarvis/self-check")
async def api_jarvis_self_check():
    try:
        import self_check
        result = await asyncio.wait_for(asyncio.to_thread(self_check.full_check), timeout=60.0)
        return result
    except asyncio.TimeoutError:
        return {"ok": False, "error": "自檢超時，請稍後重試"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/jarvis/self-repair")
async def api_jarvis_self_repair():
    try:
        import self_check
        return await asyncio.to_thread(self_check.repair_all)
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── 角色知識庫 ──
@router.get("/api/jarvis/roles")
def api_jarvis_roles():
    try:
        import role_manager
        return {"ok": True, "roles": role_manager.list_roles()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/jarvis/roles/stats")
def api_jarvis_roles_stats():
    try:
        import role_manager
        return role_manager.all_roles_stats()
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/jarvis/roles/{role_id}/stats")
def api_jarvis_role_stats(role_id: str):
    try:
        import role_manager
        return role_manager.role_stats(role_id)
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/jarvis/roles/{role_id}/learn")
async def api_jarvis_role_learn(role_id: str, request: Request):
    payload = await request.json()
    question = str((payload or {}).get("question", "")).strip()
    answer = str((payload or {}).get("answer", "")).strip()
    source = str((payload or {}).get("source", "api")).strip()
    if not question or not answer:
        raise HTTPException(400, "question and answer are required")
    try:
        import role_manager
        return role_manager.role_learn(role_id, question, answer, source)
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/jarvis/roles/{role_id}/search")
async def api_jarvis_role_search(role_id: str, request: Request):
    payload = await request.json()
    query = str((payload or {}).get("query", "")).strip()
    top_k = int((payload or {}).get("top_k", 5) or 5)
    include_master = bool((payload or {}).get("include_master", True))
    if not query:
        raise HTTPException(400, "query is required")
    try:
        import role_manager
        hits = await asyncio.to_thread(role_manager.role_search, role_id, query, top_k, include_master)
        return {"ok": True, "hits": hits, "count": len(hits)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/jarvis/roles/{role_id}/ask")
async def api_jarvis_role_ask(role_id: str, request: Request):
    payload = await request.json()
    query = str((payload or {}).get("query", "")).strip()
    top_k = int((payload or {}).get("top_k", 5) or 5)
    if not query:
        raise HTTPException(400, "query is required")
    try:
        import role_manager
        return await asyncio.to_thread(role_manager.role_ask, role_id, query, top_k)
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/jarvis/roles/{role_id}/ask-and-learn")
async def api_jarvis_role_ask_and_learn(role_id: str, request: Request):
    payload = await request.json()
    question = str((payload or {}).get("question", "")).strip()
    providers = (payload or {}).get("providers", ["groq"])
    if not question:
        raise HTTPException(400, "question is required")
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "Jarvis_Training"))
        from learn_from_giants import ask_and_learn
        import role_manager
        role = role_manager.get_role(role_id)
        if not role:
            raise HTTPException(404, f"角色 '{role_id}' 不存在")
        role_prefix = f"[以{role['name']}的專業視角回答] "
        result = await asyncio.to_thread(ask_and_learn, role_prefix + question, providers, True)
        if result.get("learned") and result.get("essence"):
            role_manager.role_learn(role_id, question, result["essence"], f"giant_{result.get('source', 'unknown')}")
        result["role"] = role_id
        result["role_name"] = role["name"]
        return {"ok": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── MCP 工作流 ──
@router.post("/api/jarvis/workflow/create")
async def api_workflow_create(request: Request):
    payload = await request.json()
    role_id = str((payload or {}).get("role_id", "")).strip()
    idea = str((payload or {}).get("idea", "")).strip()
    title = str((payload or {}).get("title", "")).strip()
    if not role_id or not idea:
        raise HTTPException(400, "role_id and idea are required")
    try:
        import mcp_workflow
        result = mcp_workflow.create_workflow(role_id, idea, title)
        if result.get("ok"):
            result = await asyncio.to_thread(mcp_workflow.advance_step, result["workflow"]["id"])
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/jarvis/workflow/list")
def api_workflow_list(status: str = ""):
    try:
        import mcp_workflow
        return {"ok": True, "workflows": mcp_workflow.list_workflows(status)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/jarvis/workflow/{wf_id}")
def api_workflow_get(wf_id: str):
    try:
        import mcp_workflow
        return mcp_workflow.get_workflow(wf_id)
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/jarvis/workflow/{wf_id}/advance")
async def api_workflow_advance(wf_id: str, request: Request):
    payload = await request.json()
    try:
        import mcp_workflow
        return await asyncio.to_thread(mcp_workflow.advance_step, wf_id, str((payload or {}).get("input", "")).strip(), bool((payload or {}).get("approved", True)))
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/jarvis/workflow/stats")
def api_workflow_stats():
    try:
        import mcp_workflow
        return mcp_workflow.workflow_stats()
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/jarvis/generate-code")
async def api_jarvis_generate_code(request: Request):
    payload = await request.json()
    prompt = str((payload or {}).get("prompt", "")).strip()
    lang = str((payload or {}).get("lang", "html")).strip().lower()
    if not prompt:
        raise HTTPException(400, "prompt is required")
    system_msg = "你是一個專業的前端工程師。根據使用者需求，生成完整可運行的程式碼。\n規則：\n1. 如果是網頁需求，生成一個完整的 HTML 檔案（包含內嵌 CSS 和 JS），可直接在瀏覽器中運行。\n2. 使用現代 CSS（flexbox/grid）和原生 JS，不依賴外部框架（除非使用者指定）。\n3. 設計要美觀、響應式、有動畫效果。\n4. 只輸出程式碼，不要解釋。用 ```html 包裹。\n5. 如果是其他語言（Python/JS/etc），用對應的 code block 包裹。"
    messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": f"需求：{prompt}\n語言：{lang}"}]
    try:
        reply = await _remote_chat_reply("groq", messages)
        if not reply:
            reply = await _remote_chat_reply("deepseek", messages)
        if not reply:
            reply = await _remote_chat_reply("ollama", messages)
        code = reply or ""
        m = re.search(r"```(?:html|css|js|javascript|python|java|cpp)?\s*\n(.*?)```", code, re.DOTALL)
        if m:
            code = m.group(1).strip()
        return {"ok": True, "code": code, "raw": reply}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/jarvis/chat-history")
async def api_jarvis_chat_history(request: Request):
    payload = await request.json()
    action = str((payload or {}).get("action", "list")).strip()
    history_dir = BRAIN_WORKSPACE / "chat_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    if action == "save":
        chat_id = str((payload or {}).get("id", "")).strip() or f"chat_{uuid.uuid4().hex[:8]}"
        title = str((payload or {}).get("title", "")).strip() or "未命名對話"
        msgs = (payload or {}).get("messages", [])
        data = {"id": chat_id, "title": title, "messages": msgs, "updated": _now_iso()}
        (history_dir / f"{chat_id}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
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
    else:
        chats = []
        for f in sorted(history_dir.glob("chat_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                chats.append({"id": d.get("id", f.stem), "title": d.get("title", ""), "updated": d.get("updated", "")})
            except Exception:
                pass
        return {"ok": True, "chats": chats[:50]}

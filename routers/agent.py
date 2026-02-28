# -*- coding: utf-8 -*-
"""築未科技 — Agent 任務 + Playbook + Butler + Graph-RAG Router"""
import asyncio
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from routers.deps import (
    agent_tasks, agent_task_queue, _save_agent_tasks, _now_iso,
    _enqueue_host_job, _read_host_job_result,
    _remote_chat_reply, _clean_model_output, _provider_alias,
    _extract_token, smart_ai, logger, ROOT,
    PLAYBOOK_DIR, TaskRequest,
)

router = APIRouter(tags=["Agent"])


# ── 語義路由 helper ──
def _semantic_route_plan(text: str) -> list[dict]:
    low = text.lower()
    steps = []
    if any(k in low for k in ["line", "訊息", "回覆"]):
        if "讀" in low or "看" in low or "read" in low:
            steps.append({"job_type": "line_read_vlm", "objective": "讀取 LINE 訊息"})
        if "回" in low or "reply" in low or "傳" in low:
            steps.append({"job_type": "line_reply", "objective": "回覆 LINE 訊息", "args": {"message": text}})
    if any(k in low for k in ["截圖", "螢幕", "screen", "screenshot"]):
        steps.append({"job_type": "screen_vlm_query", "objective": "螢幕截圖分析", "args": {"question": text}})
    if any(k in low for k in ["點擊", "開啟", "輸入", "click", "open", "type"]):
        steps.append({"job_type": "smart_gui_agent", "objective": text, "args": {"instruction": text}})
    if not steps:
        steps.append({"job_type": "", "objective": text, "execution": "llm"})
    return steps


def _build_task_from_step(route_id: str, idx: int, total: int, route_context: str, step: dict, auto_run: bool) -> dict:
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    job_type = step.get("job_type", "")
    execution = step.get("execution", "host_script" if job_type else "llm")
    return {
        "id": task_id,
        "route_id": route_id,
        "step": f"{idx}/{total}",
        "objective": step.get("objective", route_context),
        "provider": step.get("provider", "desktop" if execution == "host_script" else "cursor"),
        "execution": execution,
        "job_type": job_type,
        "status": "queued" if auto_run else "pending",
        "context": route_context,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "result": "",
        "args": step.get("args", {}),
    }


def _list_business_playbooks() -> list[dict]:
    if not PLAYBOOK_DIR.exists():
        return []
    items = []
    for f in PLAYBOOK_DIR.glob("*.json"):
        if f.name.startswith("_"):
            continue
        try:
            pb = json.loads(f.read_text(encoding="utf-8"))
            items.append({"id": f.stem, "name": pb.get("name", f.stem), "description": pb.get("description", ""), "steps_count": len(pb.get("steps", []))})
        except Exception:
            pass
    return items


def _load_business_playbook(playbook_id: str) -> dict | None:
    p = PLAYBOOK_DIR / f"{playbook_id}.json"
    if not p.exists():
        return None
    try:
        pb = json.loads(p.read_text(encoding="utf-8"))
        pb["id"] = playbook_id
        return pb
    except Exception:
        return None


# ── Agent Tasks ──
@router.get("/api/agent/tasks")
def api_agent_tasks():
    items = sorted(agent_tasks.values(), key=lambda x: str(x.get("created_at", "")), reverse=True)
    return {"ok": True, "count": len(items), "tasks": items[:200]}


@router.post("/api/agent/tasks")
async def api_agent_create_task(request: Request):
    payload = await request.json()
    objective = str((payload or {}).get("objective", "")).strip()
    provider = str((payload or {}).get("provider", "cursor")).strip().lower()
    context = str((payload or {}).get("context", "")).strip()
    execution = str((payload or {}).get("execution", "llm")).strip().lower()
    job_type = str((payload or {}).get("job_type", "")).strip().lower()
    auto_run = bool((payload or {}).get("auto_run", True))
    if not objective:
        raise HTTPException(400, "objective is required")
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {"id": task_id, "objective": objective, "provider": provider, "execution": execution if execution in {"llm", "host_script"} else "llm", "job_type": job_type or "", "status": "queued" if auto_run else "pending", "context": context, "created_at": _now_iso(), "updated_at": _now_iso(), "result": "", "logs": [f"{_now_iso()} | task created"]}
    agent_tasks[task_id] = task
    _save_agent_tasks()
    if auto_run:
        await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@router.post("/api/agent/tasks/{task_id}/run")
async def api_agent_run_task(task_id: str):
    task = agent_tasks.get(str(task_id or "").strip())
    if not task:
        raise HTTPException(404, "task not found")
    if task.get("status") in {"running"}:
        return {"ok": True, "queued": False, "task": task}
    task["status"] = "queued"
    task["updated_at"] = _now_iso()
    task.setdefault("logs", []).append(f"{_now_iso()} | queued by user")
    _save_agent_tasks()
    await agent_task_queue.put(str(task_id))
    return {"ok": True, "queued": True, "task": task}


@router.get("/api/agent/tasks/{task_id}")
def api_agent_task_detail(task_id: str):
    task = agent_tasks.get(str(task_id or "").strip())
    if not task:
        raise HTTPException(404, "task not found")
    return {"ok": True, "task": task}


@router.post("/api/agent/tasks/desktop-demo")
async def api_agent_desktop_demo():
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {"id": task_id, "objective": "執行 PyAutoGUI 桌面示範腳本（my_agent.py）", "provider": "desktop", "execution": "host_script", "job_type": "pyautogui_demo", "status": "queued", "context": "此任務會控制滑鼠與鍵盤，請先把焦點切到安全視窗。", "created_at": _now_iso(), "updated_at": _now_iso(), "result": "", "logs": [f"{_now_iso()} | desktop demo task created"]}
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@router.post("/api/agent/tasks/line-open")
async def api_agent_line_open():
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {"id": task_id, "objective": "開啟 LINE 桌面版", "provider": "desktop", "execution": "host_script", "job_type": "line_open", "status": "queued", "context": "若找不到執行檔，請確認 LINE 安裝路徑。", "created_at": _now_iso(), "updated_at": _now_iso(), "result": "", "logs": [f"{_now_iso()} | line-open task created"]}
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@router.post("/api/agent/tasks/line-read")
async def api_agent_line_read():
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {"id": task_id, "objective": "OCR 讀取目前 LINE 視窗訊息（估測）", "provider": "desktop", "execution": "host_script", "job_type": "line_read_ocr", "status": "queued", "context": "LINE 無官方讀訊 API，此任務依賴截圖+OCR，可能不準確。", "created_at": _now_iso(), "updated_at": _now_iso(), "result": "", "logs": [f"{_now_iso()} | line-read task created"]}
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@router.post("/api/agent/tasks/line-read-vlm")
async def api_agent_line_read_vlm(request: Request):
    payload = await request.json() if request else {}
    question = str((payload or {}).get("question", "")).strip() or "最後一則訊息是誰發的？內容是什麼？有沒有提到『緊急』或『修改』？"
    keywords = (payload or {}).get("keywords", ["緊急", "修改", "urgent", "change"])
    if not isinstance(keywords, list):
        keywords = ["緊急", "修改", "urgent", "change"]
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {"id": task_id, "objective": "VLM 判讀目前 LINE 視窗內容", "provider": "desktop", "execution": "host_script", "job_type": "line_read_vlm", "status": "queued", "context": "透過截圖 + VLM 判讀最後訊息與關鍵字。", "created_at": _now_iso(), "updated_at": _now_iso(), "result": "", "logs": [f"{_now_iso()} | line-read-vlm task created"], "args": {"question": question, "keywords": keywords}}
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@router.post("/api/agent/tasks/screen-vlm")
async def api_agent_screen_vlm(request: Request):
    payload = await request.json() if request else {}
    question = str((payload or {}).get("question", "")).strip()
    if not question:
        raise HTTPException(400, "question is required")
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {"id": task_id, "objective": f"VLM 判讀全螢幕：{question}", "provider": "desktop", "execution": "host_script", "job_type": "screen_vlm_query", "status": "queued", "context": "全螢幕截圖 + VLM 問答。", "created_at": _now_iso(), "updated_at": _now_iso(), "result": "", "logs": [f"{_now_iso()} | screen-vlm task created"], "args": {"question": question}}
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@router.post("/api/agent/tasks/smart-gui")
async def api_agent_smart_gui(request: Request):
    payload = await request.json()
    instruction = str((payload or {}).get("instruction", "")).strip()
    if not instruction:
        raise HTTPException(400, "instruction is required")
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {"id": task_id, "objective": f"Smart GUI：{instruction}", "provider": "desktop", "execution": "host_script", "job_type": "smart_gui_agent", "status": "queued", "context": "透過 VLM 解析畫面後進行點擊/輸入操作。", "created_at": _now_iso(), "updated_at": _now_iso(), "result": "", "logs": [f"{_now_iso()} | smart-gui task created"], "args": {"instruction": instruction, "execute": bool((payload or {}).get("execute", True)), "max_actions": max(1, min(20, int((payload or {}).get("max_actions", 8) or 8))), "retry_count": max(1, min(5, int((payload or {}).get("retry_count", 3) or 3)))}}
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@router.post("/api/agent/tasks/semantic-route")
async def api_agent_semantic_route(request: Request):
    payload = await request.json()
    text = str((payload or {}).get("text", "")).strip()
    auto_run = bool((payload or {}).get("auto_run", True))
    if not text:
        raise HTTPException(400, "text is required")
    plan = _semantic_route_plan(text)
    created = []
    parent_id = f"R-{uuid.uuid4().hex[:8]}"
    for idx, step in enumerate(plan, start=1):
        task = _build_task_from_step(route_id=parent_id, idx=idx, total=len(plan), route_context=text, step=step if isinstance(step, dict) else {}, auto_run=auto_run)
        task["logs"] = [f"{_now_iso()} | semantic-route task created"]
        tid = str(task.get("id", ""))
        agent_tasks[tid] = task
        created.append(task)
        if auto_run and tid:
            await agent_task_queue.put(tid)
    _save_agent_tasks()
    return {"ok": True, "route_id": parent_id, "count": len(created), "tasks": created}


@router.post("/api/agent/tasks/local-command")
async def api_agent_local_command(request: Request):
    payload = await request.json()
    command = str((payload or {}).get("command", "")).strip()
    timeout_sec = int((payload or {}).get("timeout", 180) or 180)
    if not command:
        raise HTTPException(400, "command is required")
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {"id": task_id, "objective": f"執行本地命令：{command}", "provider": "desktop", "execution": "host_script", "job_type": "host_command", "status": "queued", "context": "本地命令執行（含安全封鎖策略）", "created_at": _now_iso(), "updated_at": _now_iso(), "result": "", "logs": [f"{_now_iso()} | local-command task created"], "args": {"command": command, "timeout": max(10, min(600, timeout_sec))}}
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


@router.post("/api/agent/tasks/local-python")
async def api_agent_local_python(request: Request):
    payload = await request.json()
    script_path = str((payload or {}).get("script_path", "")).strip()
    script_args = (payload or {}).get("script_args", [])
    timeout_sec = int((payload or {}).get("timeout", 240) or 240)
    if not script_path:
        raise HTTPException(400, "script_path is required")
    if not isinstance(script_args, list):
        script_args = []
    task_id = f"T-{uuid.uuid4().hex[:8]}"
    task = {"id": task_id, "objective": f"執行本地 Python 腳本：{script_path}", "provider": "desktop", "execution": "host_script", "job_type": "host_python", "status": "queued", "context": "本地 Python 腳本執行", "created_at": _now_iso(), "updated_at": _now_iso(), "result": "", "logs": [f"{_now_iso()} | local-python task created"], "args": {"script_path": script_path, "script_args": [str(x) for x in script_args], "timeout": max(10, min(900, timeout_sec))}}
    agent_tasks[task_id] = task
    _save_agent_tasks()
    await agent_task_queue.put(task_id)
    return {"ok": True, "task": task}


# ── Playbooks ──
@router.get("/api/playbooks")
def api_playbook_list():
    items = _list_business_playbooks()
    return {"ok": True, "count": len(items), "playbooks": items}


@router.get("/api/playbooks/{playbook_id}")
def api_playbook_detail(playbook_id: str):
    pb = _load_business_playbook(playbook_id)
    if not pb:
        raise HTTPException(404, "playbook not found")
    return {"ok": True, "playbook": pb}


@router.post("/api/playbooks/{playbook_id}/run")
async def api_playbook_run(playbook_id: str, request: Request):
    payload = await request.json() if request else {}
    auto_run = bool((payload or {}).get("auto_run", True))
    context = str((payload or {}).get("context", "")).strip()
    overrides = (payload or {}).get("overrides", {})
    if not isinstance(overrides, dict):
        overrides = {}
    pb = _load_business_playbook(playbook_id)
    if not pb:
        raise HTTPException(404, "playbook not found")
    steps = pb.get("steps", [])
    if not isinstance(steps, list) or not steps:
        raise HTTPException(400, "playbook has no steps")
    route_id = f"P-{uuid.uuid4().hex[:8]}"
    created = []
    for idx, raw_step in enumerate(steps, start=1):
        step = raw_step if isinstance(raw_step, dict) else {}
        merged_args = step.get("args", {})
        if not isinstance(merged_args, dict):
            merged_args = {}
        merged_args = {**merged_args, **overrides}
        step = {**step, "args": merged_args}
        task = _build_task_from_step(route_id=route_id, idx=idx, total=len(steps), route_context=context or str(pb.get("description", "")), step=step, auto_run=auto_run)
        task["playbook_id"] = str(pb.get("id") or playbook_id)
        task["playbook_name"] = str(pb.get("name") or playbook_id)
        task["logs"] = [f"{_now_iso()} | playbook task created"]
        tid = str(task.get("id", ""))
        agent_tasks[tid] = task
        created.append(task)
        if auto_run and tid:
            await agent_task_queue.put(tid)
    _save_agent_tasks()
    return {"ok": True, "route_id": route_id, "playbook_id": str(pb.get("id") or playbook_id), "playbook_name": str(pb.get("name") or playbook_id), "count": len(created), "tasks": created}


# ── Butler ──
def _butler_inbox(limit_per_channel: int = 20) -> list[dict]:
    try:
        from brain_modules.task_butler import fetch_all_inbox
        return fetch_all_inbox(limit_per_channel=limit_per_channel)
    except Exception:
        return []


def _butler_run_one_round(limit_per_channel: int = 20, enqueue_auto_tasks: bool = True) -> dict:
    try:
        from brain_modules.task_butler import run_one_round
        return run_one_round(limit_per_channel=limit_per_channel, enqueue_auto_tasks=enqueue_auto_tasks, brain_api_base="http://127.0.0.1:8002")
    except Exception as e:
        return {"ok": False, "error": str(e), "inbox_count": 0, "auto_tasks_created": [], "pending_confirm_count": 0}


@router.get("/api/butler/inbox")
def api_butler_inbox(limit: int = 20):
    items = _butler_inbox(limit_per_channel=max(1, min(50, limit)))
    return {"ok": True, "count": len(items), "messages": items}


@router.post("/api/butler/run")
async def api_butler_run(request: Request):
    payload = await request.json() if request else {}
    limit = max(1, min(50, int((payload or {}).get("limit", 20) or 20)))
    enqueue = bool((payload or {}).get("enqueue_auto_tasks", True))
    return await asyncio.to_thread(_butler_run_one_round, limit_per_channel=limit, enqueue_auto_tasks=enqueue)


@router.get("/api/butler/pending")
def api_butler_pending():
    pending_file = ROOT / "reports" / "task_butler_pending_confirm.json"
    if not pending_file.exists():
        return {"ok": True, "count": 0, "pending": []}
    try:
        data = json.loads(pending_file.read_text(encoding="utf-8", errors="ignore"))
        pending = data.get("pending", []) if isinstance(data, dict) else []
        return {"ok": True, "count": len(pending), "pending": pending}
    except Exception as e:
        return {"ok": False, "error": str(e), "count": 0, "pending": []}


# ── Graph RAG ──
@router.post("/api/graph-rag/ingest")
async def api_graph_rag_ingest(request: Request):
    payload = await request.json() if request else {}
    pdf_path = str((payload or {}).get("pdf_path", "")).strip()
    source_name = str((payload or {}).get("source_name", "")).strip()
    if not pdf_path:
        raise HTTPException(400, "pdf_path is required")
    try:
        from brain_modules.brain_graph_rag import ingest_pdf
        p = Path(pdf_path).resolve()
        result = await asyncio.to_thread(ingest_pdf, p, source_name or p.stem)
        return {"ok": result.get("ok", False), "pages": result.get("pages", 0), "errors": result.get("errors", [])}
    except Exception as e:
        return {"ok": False, "pages": 0, "errors": [str(e)]}


@router.get("/api/graph-rag/search")
def api_graph_rag_search(q: str = "", limit: int = 5):
    if not q.strip():
        raise HTTPException(400, "q is required")
    try:
        from brain_modules.brain_graph_rag import search_graph_rag
        hits = search_graph_rag(q.strip(), limit=max(1, min(10, limit)))
        return {"ok": True, "count": len(hits), "hits": hits}
    except Exception as e:
        return {"ok": False, "count": 0, "hits": [], "error": str(e)}

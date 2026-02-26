# -*- coding: utf-8 -*-
"""
築未科技 — MCP 工作流引擎
─────────────────────────────
7 步驟自動化工作流：
  1. 想法產出（用戶輸入需求）
  2. 本地 AI 分析及提出建議（角色知識庫 + Ollama）
  3. 用戶確認是否為想要的效果
  4. MCP 開始動手做（用最少流量甚至免費）
  5. 確認成果
  6. AI 提出優化建議
  7. 執行優化 → 結案

每個工作流實例以 JSON 持久化，支援暫停/恢復。
"""
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
WORKFLOW_DIR = ROOT / "brain_workspace" / "workflows"
WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)


def _is_ollama_healthy() -> bool:
    """輕量級 Ollama 健康探針（同步版），2s 超時，快取 30s。"""
    import time as _time
    now = _time.time()
    # 快取：避免每次都探測
    if hasattr(_is_ollama_healthy, "_cache"):
        ok, ts = _is_ollama_healthy._cache
        if now - ts < 30:
            return ok
    try:
        import requests
        from ai_service import OLLAMA_BASE_URL
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        healthy = r.status_code == 200
    except Exception:
        healthy = False
    _is_ollama_healthy._cache = (healthy, now)
    if not healthy:
        print("⚠️ [mcp_workflow] Ollama 本地異常，自動切換雲端")
    return healthy


def smart_generate(prompt: str) -> str:
    """軍師生成：Ollama 本地優先，雲端僅 non-local_only 模式備援。"""
    # 本地 Ollama 軍師優先
    if _is_ollama_healthy():
        try:
            from local_learning_system import ollama_generate
            result = ollama_generate(prompt)
            if result and result.strip():
                return result
        except Exception:
            pass
    # 非 local_only 模式才嘗試雲端備援
    from ai_service import AI_COST_MODE
    if AI_COST_MODE != "local_only":
        try:
            from ai_service import _gemini_chat_sync, GEMINI_API_KEY
            if GEMINI_API_KEY:
                messages = [{"role": "user", "content": prompt}]
                result = _gemini_chat_sync(messages)
                if result and "API 錯誤" not in result and "done" not in result[:20]:
                    return result
        except Exception:
            pass
    return "AI 服務暫時不可用。"


def exec_generate(prompt: str) -> str:
    """士兵生成：Ollama 本地執行，雲端僅 non-local_only 模式救援。"""
    # Ollama 士兵上場
    if _is_ollama_healthy():
        try:
            from local_learning_system import ollama_generate
            result = ollama_generate(prompt)
            if result and result.strip():
                return result
        except Exception:
            pass
    # 非 local_only 模式才嘗試雲端救援
    from ai_service import AI_COST_MODE
    if AI_COST_MODE != "local_only":
        try:
            from ai_service import _gemini_chat_sync, GEMINI_API_KEY
            if GEMINI_API_KEY:
                messages = [{"role": "user", "content": prompt}]
                return _gemini_chat_sync(messages)
        except Exception:
            pass
    return "AI 服務暫時不可用。"

# 工作流步驟定義
STEPS = [
    {"id": "idea",     "name": "想法產出",       "icon": "💡", "auto": False},
    {"id": "analyze",  "name": "AI 分析建議",    "icon": "🧠", "auto": True},
    {"id": "confirm",  "name": "用戶確認方案",   "icon": "✅", "auto": False},
    {"id": "execute",  "name": "MCP 執行",       "icon": "⚡", "auto": True},
    {"id": "review",   "name": "確認成果",       "icon": "🔍", "auto": False},
    {"id": "optimize", "name": "AI 優化建議",    "icon": "🔧", "auto": True},
    {"id": "finalize", "name": "執行優化/結案",  "icon": "🏁", "auto": False},
]

STEP_IDS = [s["id"] for s in STEPS]


def _wf_path(wf_id: str) -> Path:
    return WORKFLOW_DIR / f"{wf_id}.json"


def _save_wf(wf: dict):
    _wf_path(wf["id"]).write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_wf(wf_id: str) -> dict | None:
    p = _wf_path(wf_id)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


# ═══════════════════════════════════════════
# 工作流 CRUD
# ═══════════════════════════════════════════

def create_workflow(role_id: str, idea: str, title: str = "") -> dict[str, Any]:
    """建立新工作流。"""
    import role_manager
    role = role_manager.get_role(role_id)
    if not role:
        return {"ok": False, "error": f"角色 '{role_id}' 不存在"}

    wf_id = f"wf_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    wf = {
        "id": wf_id,
        "title": title or idea[:50],
        "role_id": role_id,
        "role_name": role["name"],
        "role_icon": role["icon"],
        "idea": idea,
        "current_step": "idea",
        "status": "active",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "steps": {
            "idea":     {"status": "done", "input": idea, "output": "", "ts": datetime.now().isoformat(timespec="seconds")},
            "analyze":  {"status": "pending", "input": "", "output": "", "ts": ""},
            "confirm":  {"status": "pending", "input": "", "output": "", "ts": ""},
            "execute":  {"status": "pending", "input": "", "output": "", "ts": ""},
            "review":   {"status": "pending", "input": "", "output": "", "ts": ""},
            "optimize": {"status": "pending", "input": "", "output": "", "ts": ""},
            "finalize": {"status": "pending", "input": "", "output": "", "ts": ""},
        },
        "mcp_actions": [],
        "history": [{"step": "idea", "action": "created", "ts": datetime.now().isoformat(timespec="seconds")}],
    }
    _save_wf(wf)
    return {"ok": True, "workflow": wf}


def list_workflows(status: str = "") -> list[dict]:
    """列出所有工作流（可依狀態篩選）。"""
    results = []
    for p in sorted(WORKFLOW_DIR.glob("wf_*.json"), reverse=True):
        try:
            wf = json.loads(p.read_text(encoding="utf-8"))
            if status and wf.get("status") != status:
                continue
            results.append({
                "id": wf["id"],
                "title": wf.get("title", ""),
                "role_id": wf.get("role_id", ""),
                "role_name": wf.get("role_name", ""),
                "role_icon": wf.get("role_icon", ""),
                "current_step": wf.get("current_step", ""),
                "status": wf.get("status", ""),
                "created_at": wf.get("created_at", ""),
                "updated_at": wf.get("updated_at", ""),
            })
        except Exception:
            continue
    return results


def get_workflow(wf_id: str) -> dict[str, Any]:
    """取得工作流詳情。"""
    wf = _load_wf(wf_id)
    if not wf:
        return {"ok": False, "error": "工作流不存在"}
    return {"ok": True, "workflow": wf}


# ═══════════════════════════════════════════
# 步驟執行
# ═══════════════════════════════════════════

def advance_step(wf_id: str, user_input: str = "", user_approved: bool = True) -> dict[str, Any]:
    """推進工作流到下一步。

    - 自動步驟（analyze/execute/optimize）由 AI 執行
    - 手動步驟（confirm/review/finalize）需用戶確認
    """
    wf = _load_wf(wf_id)
    if not wf:
        return {"ok": False, "error": "工作流不存在"}
    if wf["status"] != "active":
        return {"ok": False, "error": f"工作流狀態為 {wf['status']}，無法推進"}

    current = wf["current_step"]
    current_idx = STEP_IDS.index(current) if current in STEP_IDS else -1

    # 決定下一步
    if current == "idea":
        next_step = "analyze"
    elif current == "analyze":
        next_step = "confirm"
    elif current == "confirm":
        if not user_approved:
            # 用戶不滿意，回到 analyze 重新分析
            wf["steps"]["analyze"]["status"] = "pending"
            wf["steps"]["analyze"]["output"] = ""
            wf["current_step"] = "analyze"
            wf["steps"]["confirm"]["input"] = user_input or "用戶要求重新分析"
            wf["history"].append({"step": "confirm", "action": "rejected", "ts": datetime.now().isoformat(timespec="seconds")})
            wf["updated_at"] = datetime.now().isoformat(timespec="seconds")
            _save_wf(wf)
            return _run_auto_step(wf, "analyze", user_input)
        next_step = "execute"
    elif current == "execute":
        next_step = "review"
    elif current == "review":
        if not user_approved:
            # 成果不滿意，回到 execute 重做
            wf["steps"]["execute"]["status"] = "pending"
            wf["current_step"] = "execute"
            wf["history"].append({"step": "review", "action": "rejected", "ts": datetime.now().isoformat(timespec="seconds")})
            wf["updated_at"] = datetime.now().isoformat(timespec="seconds")
            _save_wf(wf)
            return _run_auto_step(wf, "execute", user_input)
        next_step = "optimize"
    elif current == "optimize":
        next_step = "finalize"
    elif current == "finalize":
        if user_approved:
            wf["status"] = "completed"
            wf["steps"]["finalize"]["status"] = "done"
            wf["steps"]["finalize"]["output"] = "結案"
            wf["steps"]["finalize"]["ts"] = datetime.now().isoformat(timespec="seconds")
            wf["history"].append({"step": "finalize", "action": "completed", "ts": datetime.now().isoformat(timespec="seconds")})
            wf["updated_at"] = datetime.now().isoformat(timespec="seconds")
            _save_wf(wf)
            return {"ok": True, "workflow": wf, "message": "工作流已結案"}
        else:
            # 回到 optimize
            wf["steps"]["optimize"]["status"] = "pending"
            wf["current_step"] = "optimize"
            wf["history"].append({"step": "finalize", "action": "rejected", "ts": datetime.now().isoformat(timespec="seconds")})
            wf["updated_at"] = datetime.now().isoformat(timespec="seconds")
            _save_wf(wf)
            return _run_auto_step(wf, "optimize", user_input)
    else:
        return {"ok": False, "error": f"未知步驟: {current}"}

    # 標記當前步驟完成
    wf["steps"][current]["status"] = "done"
    if user_input:
        wf["steps"][current]["input"] = user_input
    wf["steps"][current]["ts"] = datetime.now().isoformat(timespec="seconds")
    wf["current_step"] = next_step
    wf["updated_at"] = datetime.now().isoformat(timespec="seconds")
    wf["history"].append({"step": current, "action": "done", "ts": datetime.now().isoformat(timespec="seconds")})
    _save_wf(wf)

    # 如果下一步是自動步驟，立即執行
    step_def = next((s for s in STEPS if s["id"] == next_step), None)
    if step_def and step_def.get("auto"):
        return _run_auto_step(wf, next_step, user_input)

    return {"ok": True, "workflow": wf, "message": f"進入步驟: {step_def['name'] if step_def else next_step}"}


def _run_auto_step(wf: dict, step_id: str, context: str = "") -> dict[str, Any]:
    """執行自動步驟（AI 分析 / MCP 執行 / AI 優化）。"""
    import sys
    sys.path.insert(0, str(ROOT / "Jarvis_Training"))

    role_id = wf["role_id"]
    idea = wf["idea"]

    import role_manager

    if step_id == "analyze":
        return _step_analyze(wf, role_id, idea, context)
    elif step_id == "execute":
        return _step_execute(wf, role_id, idea, context)
    elif step_id == "optimize":
        return _step_optimize(wf, role_id, idea, context)
    else:
        return {"ok": False, "error": f"無法自動執行步驟: {step_id}"}


def _step_analyze(wf: dict, role_id: str, idea: str, extra: str = "") -> dict[str, Any]:
    """步驟 2：AI 分析及提出建議（Gemini Pro 優先，Ollama 備援）。"""
    import role_manager

    role = role_manager.get_role(role_id) or {}
    system_prompt = role.get("system_prompt", "")
    mcp_tools = role.get("mcp_tools", {})

    # 搜尋角色知識庫取得上下文
    hits = role_manager.role_search(role_id, idea, top_k=3)
    context_parts = []
    for i, h in enumerate(hits, 1):
        src = "專業庫" if h.get("from", "").startswith("role:") else "通識庫"
        context_parts.append(f"[{src}] {h.get('question', '')[:60]}: {h.get('answer', '')[:200]}")
    kb_context = "\n".join(context_parts) if context_parts else "（無相關知識）"

    # 可用 MCP 工具描述
    tool_desc = ""
    if mcp_tools:
        tool_lines = []
        for phase, tools in mcp_tools.items():
            tool_lines.append(f"  {phase}: {', '.join(tools)}")
        tool_desc = "可用 MCP 工具：\n" + "\n".join(tool_lines)

    prompt = (
        f"{system_prompt}\n\n"
        f"用戶的想法：{idea}\n"
        f"{'用戶補充：' + extra if extra else ''}\n\n"
        f"相關知識：\n{kb_context}\n\n"
        f"{tool_desc}\n\n"
        "請以此角色的專業視角，提供：\n"
        "1. 【需求分析】理解用戶想要什麼\n"
        "2. 【執行方案】具體步驟（優先使用免費/本地方案）\n"
        "3. 【所需工具】列出會用到的 MCP 工具和原因\n"
        "4. 【預估成本】時間和費用（盡量免費）\n"
        "5. 【風險提醒】可能的問題和備案"
    )
    try:
        analysis = smart_generate(prompt)
    except Exception as e:
        analysis = f"AI 分析暫時不可用：{e}\n\n請手動提供執行方案。"

    wf["steps"]["analyze"]["status"] = "done"
    wf["steps"]["analyze"]["output"] = analysis
    wf["steps"]["analyze"]["ts"] = datetime.now().isoformat(timespec="seconds")
    wf["current_step"] = "confirm"
    wf["updated_at"] = datetime.now().isoformat(timespec="seconds")
    wf["history"].append({"step": "analyze", "action": "done", "ts": datetime.now().isoformat(timespec="seconds")})
    _save_wf(wf)

    return {"ok": True, "workflow": wf, "message": "AI 分析完成，請確認方案"}


def _step_execute(wf: dict, role_id: str, idea: str, extra: str = "") -> dict[str, Any]:
    """步驟 4：MCP 執行。

    產生 MCP 動作計畫（實際 MCP 呼叫由前端/Agent 執行）。
    """
    import role_manager

    role = role_manager.get_role(role_id) or {}
    mcp_tools = role.get("mcp_tools", {})
    analysis = wf["steps"]["analyze"].get("output", "")

    # 產生 MCP 執行計畫
    exec_tools = mcp_tools.get("execute", [])
    research_tools = mcp_tools.get("research", [])

    prompt = (
        f"你是 MCP 工作流執行規劃器。根據以下分析結果，產生具體的 MCP 工具呼叫計畫。\n\n"
        f"用戶需求：{idea}\n"
        f"分析結果：{analysis[:1500]}\n"
        f"{'用戶補充：' + extra if extra else ''}\n\n"
        f"可用執行工具：{', '.join(exec_tools)}\n"
        f"可用研究工具：{', '.join(research_tools)}\n\n"
        "請產生 JSON 格式的執行計畫，每個動作包含：\n"
        '[ {{"tool": "工具名", "action": "動作描述", "params": "參數說明", "cost": "免費/低成本"}} ]\n'
        "優先使用免費方案，最小化外部 API 呼叫。只輸出 JSON 陣列。"
    )
    try:
        raw = exec_generate(prompt)
        # 嘗試解析 JSON
        import re
        json_match = re.search(r'\[.*\]', raw, re.DOTALL)
        if json_match:
            actions = json.loads(json_match.group())
        else:
            actions = [{"tool": "manual", "action": raw[:500], "params": "", "cost": "免費"}]
    except Exception:
        actions = [{"tool": "manual", "action": "AI 規劃失敗，請手動執行", "params": "", "cost": "免費"}]

    wf["mcp_actions"] = actions
    wf["steps"]["execute"]["status"] = "done"
    wf["steps"]["execute"]["output"] = json.dumps(actions, ensure_ascii=False)
    wf["steps"]["execute"]["ts"] = datetime.now().isoformat(timespec="seconds")
    wf["current_step"] = "review"
    wf["updated_at"] = datetime.now().isoformat(timespec="seconds")
    wf["history"].append({"step": "execute", "action": "done", "ts": datetime.now().isoformat(timespec="seconds")})
    _save_wf(wf)

    return {"ok": True, "workflow": wf, "message": "MCP 執行計畫已產生，請確認成果"}


def _step_optimize(wf: dict, role_id: str, idea: str, extra: str = "") -> dict[str, Any]:
    """步驟 6：AI 提出優化建議（Gemini Pro 優先，Ollama 備援）。"""
    import role_manager

    role = role_manager.get_role(role_id) or {}
    analysis = wf["steps"]["analyze"].get("output", "")
    execute_output = wf["steps"]["execute"].get("output", "")

    prompt = (
        f"{role.get('system_prompt', '')}\n\n"
        f"用戶原始需求：{idea}\n"
        f"執行方案：{analysis[:800]}\n"
        f"執行結果：{execute_output[:800]}\n"
        f"{'用戶回饋：' + extra if extra else ''}\n\n"
        "請提出優化建議：\n"
        "1. 【成果評估】目前成果的優缺點\n"
        "2. 【優化方向】可以改進的地方\n"
        "3. 【具體動作】優化的具體步驟\n"
        "4. 【預期效果】優化後的預期改善"
    )
    try:
        optimization = smart_generate(prompt)
    except Exception as e:
        optimization = f"AI 優化分析暫時不可用：{e}"

    wf["steps"]["optimize"]["status"] = "done"
    wf["steps"]["optimize"]["output"] = optimization
    wf["steps"]["optimize"]["ts"] = datetime.now().isoformat(timespec="seconds")
    wf["current_step"] = "finalize"
    wf["updated_at"] = datetime.now().isoformat(timespec="seconds")
    wf["history"].append({"step": "optimize", "action": "done", "ts": datetime.now().isoformat(timespec="seconds")})
    _save_wf(wf)

    return {"ok": True, "workflow": wf, "message": "AI 優化建議已產生，請決定是否結案"}


# ═══════════════════════════════════════════
# 統計
# ═══════════════════════════════════════════

def workflow_stats() -> dict[str, Any]:
    """工作流統計。"""
    all_wf = list_workflows()
    active = sum(1 for w in all_wf if w["status"] == "active")
    completed = sum(1 for w in all_wf if w["status"] == "completed")
    by_role: dict[str, int] = {}
    for w in all_wf:
        rn = w.get("role_name", "未知")
        by_role[rn] = by_role.get(rn, 0) + 1
    return {
        "ok": True,
        "total": len(all_wf),
        "active": active,
        "completed": completed,
        "by_role": by_role,
        "steps": STEPS,
    }

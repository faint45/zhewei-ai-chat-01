# -*- coding: utf-8 -*-
"""築未科技 — 系統健康 + 模式切換 Router"""
import asyncio
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from routers.deps import (
    ROOT, BRAIN_WORKSPACE, STATIC_DIR, PROGRESS_FILE,
    _extract_token, _require_admin, sec_mw, logger,
    _check_http_ok, _check_tcp, _check_any_tcp, _check_any_http,
    gemini_ai, ollama_ai, claude_ai,
)

router = APIRouter(tags=["系統"])


def _resolve_voice_status() -> dict:
    whisper_bin = (os.environ.get("WHISPER_BIN") or "whisper").strip()
    piper_bin = (os.environ.get("PIPER_BIN") or "piper").strip()
    piper_model_path = (os.environ.get("PIPER_MODEL_PATH") or "").strip()
    if not piper_model_path:
        piper_model_path = str((Path(os.environ.get("ZHEWEI_MEMORY_ROOT", str(ROOT / "zhewei_memory"))) / "models" / "piper" / "zh_CN-huayan-medium.onnx").resolve())
    stt_provider = (os.environ.get("STT_PROVIDER") or "whisper").strip()
    import importlib.util
    return {
        "stt_provider": stt_provider,
        "tts_provider": (os.environ.get("TTS_PROVIDER") or "piper").strip(),
        "whisper_bin": whisper_bin,
        "whisper_available": bool(shutil.which(whisper_bin) or importlib.util.find_spec("whisper") or shutil.which("faster-whisper") or importlib.util.find_spec("faster_whisper")),
        "piper_bin": piper_bin,
        "piper_available": bool(shutil.which(piper_bin)),
        "piper_model_path": piper_model_path,
        "piper_model_exists": Path(piper_model_path).exists(),
    }


def _resolve_dependency_status() -> dict:
    qdrant_url = (os.environ.get("QDRANT_URL") or "").strip()
    weaviate_url = (os.environ.get("WEAVIATE_URL") or "").strip()
    n8n_url = (os.environ.get("N8N_URL") or "").strip()
    redis_host = (os.environ.get("REDIS_HOST") or "").strip()
    redis_port = int((os.environ.get("REDIS_PORT") or "6379").strip() or "6379")
    postgres_host = (os.environ.get("POSTGRES_HOST") or "").strip()
    postgres_port = int((os.environ.get("POSTGRES_PORT") or "5432").strip() or "5432")
    qdrant_candidates = [u for u in [qdrant_url, "http://zhewei-qdrant:6333/collections", "http://host.docker.internal:6333/collections", "http://localhost:6333/collections"] if u]
    weaviate_candidates = [u for u in [weaviate_url, "http://weaviate:8080/v1/.well-known/ready", "http://host.docker.internal:8080/v1/.well-known/ready", "http://localhost:8080/v1/.well-known/ready"] if u]
    n8n_candidates = [u for u in [n8n_url, "http://host.docker.internal:5678", "http://localhost:5678"] if u]
    redis_candidates = [(h, redis_port) for h in ([redis_host] if redis_host else []) + ["redis", "host.docker.internal", "localhost"] if h]
    pg_candidates = [(h, postgres_port) for h in ([postgres_host] if postgres_host else []) + ["db_postgres", "db", "host.docker.internal", "localhost"] if h]
    return {
        "qdrant": _check_any_http(qdrant_candidates),
        "weaviate": _check_any_http(weaviate_candidates),
        "n8n": _check_any_http(n8n_candidates),
        "redis": _check_any_tcp(redis_candidates),
        "postgres": _check_any_tcp(pg_candidates),
    }


def _mode_from_dependencies(deps: dict) -> str:
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


# ── 健康檢查 ──
@router.get("/healthz")
async def api_healthz():
    if sec_mw:
        return sec_mw.health_check()
    return {"status": "ok"}


@router.get("/readyz")
async def api_readyz():
    if sec_mw:
        result = sec_mw.readiness_check()
        if result["status"] != "ready":
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=503, content=result)
        return result
    return {"status": "ready"}


@router.get("/health")
def health_check():
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
        "mode": mode, "ollama": ollama_ok,
        "venv_vision": venv_vision.exists(),
        "static_dir": (STATIC_DIR / "index.html").exists(),
        "progress_dir": PROGRESS_FILE.parent.exists(),
        "voice": voice,
        "dependencies": _dependency_display(deps, mode),
        "dependencies_raw": deps,
    }


@router.get("/api/health/summary")
def api_health_summary():
    return health_check()


@router.get("/api/system/mode/status")
def api_mode_status():
    deps = _resolve_dependency_status()
    return {"ok": True, "mode": _mode_from_dependencies(deps), "dependencies": deps}


@router.post("/api/system/mode/switch")
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
        req_file = ROOT / "reports" / "mode_switch_request.json"
        req_file.parent.mkdir(parents=True, exist_ok=True)
        req_file.write_text(json.dumps({"mode": mode, "requested_at": int(time.time()), "source": "brain_server_container"}, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "queued": True, "mode": mode, "hint": "已排入主機切換佇列"}
    try:
        proc = await asyncio.to_thread(subprocess.run, [powershell_cmd, "-ExecutionPolicy", "Bypass", "-File", str(script_ps1), "-Mode", mode], cwd=str(ROOT), capture_output=True, text=True, timeout=180)
        out = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()[-3000:]
        return {"ok": proc.returncode == 0, "mode": mode, "exit_code": int(proc.returncode), "output": out}
    except Exception as e:
        return {"ok": False, "mode": mode, "error": str(e)}


@router.get("/api/system/mode/result")
def api_mode_result():
    res_file = ROOT / "reports" / "mode_switch_result.json"
    if not res_file.exists():
        return {"ok": False, "pending": True, "message": "no result yet"}
    try:
        return json.loads(res_file.read_text(encoding="utf-8", errors="ignore"))
    except Exception as e:
        return {"ok": False, "pending": True, "message": str(e)}


@router.get("/api/agents")
def api_agents():
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


@router.get("/api/progress")
def api_progress():
    try:
        if PROGRESS_FILE.exists():
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8", errors="replace"))
            return {"ok": True, "data": data.get("data", ""), "updated": data.get("updated", "")}
    except (json.JSONDecodeError, OSError):
        pass
    return {"ok": True, "data": "", "updated": ""}

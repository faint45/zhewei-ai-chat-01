"""
築未科技大腦 - 自我學習與修復精進
記錄成敗、調整優先序、修復策略
"""
import json
import threading
import time
from pathlib import Path

from brain_data_config import LEARN_FILE
MAX_RECORDS = 500
DECAY = 0.95

_lock = threading.Lock()


def _load() -> dict:
    if not LEARN_FILE.exists():
        return {"scores": {}, "failures": {}, "success_log": [], "version": 1}
    try:
        with open(LEARN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"scores": {}, "failures": {}, "success_log": [], "version": 1}


def _save(data: dict):
    with _lock:
        try:
            with open(LEARN_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=0)
        except Exception:
            pass


def record_success(provider: str, latency_ms: float = 0):
    data = _load()
    scores = data.setdefault("scores", {})
    base = scores.get(provider, 1.0)
    bonus = 1.0 - min(latency_ms / 5000, 0.5)
    scores[provider] = min(2.0, base * 1.02 + bonus * 0.02)
    data["success_log"] = (data.get("success_log") or [])[-MAX_RECORDS:]
    data["success_log"].append({"provider": provider, "ts": time.time()})
    _save(data)


def record_failure(provider: str):
    data = _load()
    scores = data.setdefault("scores", {})
    failures = data.setdefault("failures", {})
    scores[provider] = max(0.1, (scores.get(provider, 1.0) * DECAY))
    failures[provider] = failures.get(provider, 0) + 1
    _save(data)


def get_provider_order(available: list[str]) -> list[str]:
    data = _load()
    scores = data.get("scores", {})
    scored = [(p, scores.get(p, 1.0)) for p in available]
    scored.sort(key=lambda x: -x[1])
    return [p for p, _ in scored]


def get_health_report() -> dict:
    data = _load()
    return {
        "scores": data.get("scores", {}),
        "failures": data.get("failures", {}),
        "total_success": len(data.get("success_log", [])),
    }


def suggest_repair(provider: str) -> str | None:
    data = _load()
    failures = data.get("failures", {}).get(provider, 0)
    if failures > 3:
        if provider == "Ollama":
            return "請確認 Ollama 已啟動 (ollama serve)"
        if provider in ("Groq", "Gemini", "OpenRouter", "Mistral", "DeepSeek"):
            return f"請檢查 {provider} API Key 是否有效"
    return None

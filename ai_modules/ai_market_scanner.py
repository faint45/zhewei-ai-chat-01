"""
築未科技大腦 - 市面 AI 功能掃描與模仿
定期掃描已知來源，發現新功能並記錄
"""
import json
import re
import time
from pathlib import Path

import httpx

from brain_data_config import DISCOVERY_FILE
SCAN_INTERVAL = 3600

_sources = [
    {"name": "OpenAI", "url": "https://openai.com/blog", "type": "blog"},
    {"name": "Anthropic", "url": "https://www.anthropic.com/news", "type": "blog"},
    {"name": "Google AI", "url": "https://blog.google/technology/ai/", "type": "blog"},
    {"name": "Ollama", "url": "https://github.com/ollama/ollama/releases", "type": "releases"},
    {"name": "Groq", "url": "https://console.groq.com/docs", "type": "docs"},
]


def _load_discoveries() -> dict:
    if not DISCOVERY_FILE.exists():
        return {"features": [], "last_scan": 0, "suggestions": []}
    try:
        with open(DISCOVERY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"features": [], "last_scan": 0, "suggestions": []}


def _save_discoveries(data: dict):
    try:
        with open(DISCOVERY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=0)
    except Exception:
        pass


def _extract_features(html: str, source: str) -> list[dict]:
    features = []
    patterns = [
        (r"function\s*call", "function_calling"),
        (r"vision|image|圖片|圖像", "vision"),
        (r"stream|串流|流式", "streaming"),
        (r"embedding|嵌入", "embedding"),
        (r"tool\s*use|工具", "tools"),
        (r"RAG|retrieval|檢索", "rag"),
        (r"agent|代理", "agent"),
        (r"code\s*interpreter|代碼執行", "code_interpreter"),
        (r"multimodal|多模態", "multimodal"),
        (r"long\s*context|長上下文|128k|1M", "long_context"),
        (r"free\s*tier|免費|free tier", "free_tier"),
        (r"new\s*model|新模型|release", "new_model"),
    ]
    for pat, feat in patterns:
        if re.search(pat, html, re.I):
            features.append({"feature": feat, "source": source, "ts": time.time()})
    return features


async def scan_once() -> dict:
    data = _load_discoveries()
    all_new = []
    async with httpx.AsyncClient(timeout=10) as client:
        for src in _sources:
            try:
                r = await client.get(src["url"])
                if r.status_code == 200:
                    new_feats = _extract_features(r.text[:50000], src["name"])
                    for f in new_feats:
                        if not any(x.get("feature") == f["feature"] and x.get("source") == f["source"]
                                   for x in data.get("features", [])[-100:]):
                            all_new.append(f)
            except Exception:
                pass
    existing = data.get("features", [])[-200:]
    data["features"] = existing + all_new
    data["last_scan"] = time.time()
    if all_new:
        data.setdefault("suggestions", []).extend([
            {"msg": f"發現 {f['feature']} ({f['source']})", "ts": f["ts"]}
            for f in all_new[-10:]
        ])
    _save_discoveries(data)
    return {"scanned": len(_sources), "new": len(all_new), "features": all_new}


def get_discovered_features() -> list[dict]:
    data = _load_discoveries()
    return data.get("features", [])[-50:]


def get_upgrade_suggestions() -> list[str]:
    data = _load_discoveries()
    sugs = data.get("suggestions", [])[-10:]
    return [s["msg"] for s in reversed(sugs)]


def get_system_version() -> str:
    v = _load_discoveries().get("system_version", "1.0")
    return str(v)

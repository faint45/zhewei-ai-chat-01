# -*- coding: utf-8 -*-
"""築未科技 — AI API 代理服務 Router (OpenAI 相容)"""
from fastapi import APIRouter, Request, HTTPException
from routers.deps import _extract_token, _require_admin, _require_superadmin, logger

router = APIRouter(tags=["AI代理"])

try:
    import ai_api_proxy
    AI_API_PROXY_AVAILABLE = True
except ImportError:
    ai_api_proxy = None
    AI_API_PROXY_AVAILABLE = False


def _extract_api_key(request: Request) -> str:
    auth = (request.headers.get("authorization") or "").strip()
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return request.query_params.get("api_key", "")


@router.post("/v1/chat/completions")
async def api_proxy_chat(request: Request):
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    api_key = _extract_api_key(request)
    if not api_key:
        raise HTTPException(401, "Missing API Key")
    body = await request.json()
    return await ai_api_proxy.proxy_chat_completion(
        api_key=api_key, model=body.get("model", "qwen3:8b"), messages=body.get("messages", []),
        temperature=body.get("temperature"), top_p=body.get("top_p"), max_tokens=body.get("max_tokens"),
    )


@router.post("/v1/embeddings")
async def api_proxy_embeddings(request: Request):
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    api_key = _extract_api_key(request)
    if not api_key:
        raise HTTPException(401, "Missing API Key")
    body = await request.json()
    return await ai_api_proxy.proxy_embeddings(api_key=api_key, model=body.get("model", "nomic-embed-text"), input_text=body.get("input", ""))


@router.get("/v1/models")
async def api_proxy_models():
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    return {"ok": True, "models": ai_api_proxy.get_available_models(), "plans": ai_api_proxy.PLANS}


@router.post("/api/proxy/keys/generate")
async def api_proxy_generate_key(request: Request):
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    _require_admin(request)
    body = await request.json()
    return ai_api_proxy.generate_api_key(owner=body.get("owner", ""), email=body.get("email", ""), plan=body.get("plan", "free"), expires_days=body.get("expires_days", 365), note=body.get("note", ""))


@router.get("/api/proxy/keys")
async def api_proxy_list_keys(request: Request):
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    _require_admin(request)
    keys = ai_api_proxy.list_api_keys(active_only=request.query_params.get("all") != "1")
    return {"ok": True, "keys": keys, "count": len(keys)}


@router.post("/api/proxy/keys/revoke")
async def api_proxy_revoke_key(request: Request):
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    _require_superadmin(request)
    body = await request.json()
    return ai_api_proxy.revoke_api_key(body.get("key_id", ""))


@router.post("/api/proxy/keys/upgrade")
async def api_proxy_upgrade_key(request: Request):
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    _require_admin(request)
    body = await request.json()
    return ai_api_proxy.update_key_plan(body.get("key_id", ""), body.get("plan", ""))


@router.get("/api/proxy/usage")
async def api_proxy_usage(request: Request, days: int = 30):
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
    raise HTTPException(401, "需要認證")


@router.get("/api/proxy/revenue")
async def api_proxy_revenue(request: Request):
    if not ai_api_proxy:
        return {"ok": False, "error": "AI API Proxy 未安裝"}
    _require_admin(request)
    return {"ok": True, **ai_api_proxy.get_revenue_summary()}

# -*- coding: utf-8 -*-
"""築未科技 — HTML 頁面路由 Router"""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, FileResponse, PlainTextResponse
from routers.deps import serve_static_page, _require_auth, STATIC_DIR, FALLBACK_STATIC, ROOT

router = APIRouter(tags=["頁面"])

PHOTO_APP_DIR = ROOT / "photo_app"


@router.get("/")
async def get_index():
    return RedirectResponse(url="/jarvis-login", status_code=302)


@router.get("/admin")
async def get_admin(request: Request):
    return RedirectResponse(url="/jarvis", status_code=302)


@router.get("/chat")
async def get_chat(request: Request):
    return serve_static_page("chat.html", require_login=True, request=request)


@router.get("/jarvis")
async def get_jarvis(request: Request):
    return serve_static_page("jarvis.html")


@router.get("/jarvis-login")
async def get_jarvis_login():
    return serve_static_page("jarvis-login.html")


@router.get("/jarvis-register")
async def get_jarvis_register():
    return serve_static_page("jarvis-register.html")


@router.get("/admin-commercial")
async def get_admin_commercial():
    return serve_static_page("admin_commercial.html")


@router.get("/smart-remote")
async def get_smart_remote():
    return serve_static_page("smart-remote.html")


@router.get("/chat-remote")
async def get_chat_remote():
    return serve_static_page("chat-remote.html")


@router.get("/payment")
async def get_payment_page():
    return serve_static_page("payment.html")


@router.get("/construction-ai")
async def get_construction_ai_page():
    return serve_static_page("construction-ai.html")


@router.get("/llm-api")
async def get_llm_api_page():
    return serve_static_page("llm-api.html")


@router.get("/asset-commander")
async def get_asset_commander_page():
    return serve_static_page("asset_commander.html")


@router.get("/vision-edge")
async def get_vision_edge_dashboard(request: Request):
    auth = _require_auth(request)
    if isinstance(auth, RedirectResponse):
        return auth
    import os
    VISION_EDGE_URL = os.environ.get("VISION_EDGE_URL", "http://localhost:8015")
    try:
        import urllib.request
        from fastapi.responses import HTMLResponse
        with urllib.request.urlopen(f"{VISION_EDGE_URL}/", timeout=5) as r:
            html = r.read().decode("utf-8", errors="ignore")
        return HTMLResponse(html)
    except Exception:
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<h1>Vision Edge Service 未啟動</h1><p>請先執行 scripts/start_vision_edge.bat</p>", status_code=503)


@router.get("/agent-hub")
async def get_agent_hub(request: Request):
    return serve_static_page("agent_hub.html", require_login=True, request=request)


@router.get("/push-demo")
async def get_push_demo(request: Request):
    return serve_static_page("push-demo.html", require_login=True, request=request)


@router.get("/health-dashboard")
async def get_health_dashboard(request: Request):
    return serve_static_page("health_dashboard.html", require_login=True, request=request)


@router.get("/usage-dashboard")
async def get_usage_dashboard():
    return serve_static_page("usage-dashboard.html")


@router.get("/favicon.ico")
async def favicon():
    fav = STATIC_DIR / "favicon.svg"
    if fav.exists():
        return FileResponse(str(fav), media_type="image/svg+xml")
    from starlette.responses import Response as RawResponse
    return RawResponse(status_code=204)


@router.get("/pwa")
async def get_pwa():
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "pwa" / "index.html"
        if p.exists():
            return FileResponse(str(p))
    return PlainTextResponse("PWA not found", status_code=404)


@router.get("/pwa/{path:path}")
async def get_pwa_file(path: str):
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "pwa" / path
        if p.exists() and p.is_file():
            media = "text/html"
            if path.endswith(".js"):
                media = "application/javascript"
            elif path.endswith(".json"):
                media = "application/json"
            elif path.endswith(".png"):
                media = "image/png"
            return FileResponse(str(p), media_type=media)
    return PlainTextResponse("not found", status_code=404)


@router.get("/privacy")
async def get_privacy_page():
    return serve_static_page("privacy.html")


@router.get("/terms")
async def get_terms_page():
    return serve_static_page("terms.html")


@router.get("/app")
async def get_app_platform(request: Request):
    return serve_static_page("app.html")


@router.get("/transfer")
async def get_transfer_page(request: Request):
    return serve_static_page("transfer.html", require_login=True, request=request)


@router.get("/transfer-receive.html")
async def get_transfer_receive_page():
    return serve_static_page("transfer-receive.html")

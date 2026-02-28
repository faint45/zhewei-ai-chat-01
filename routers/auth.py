# -*- coding: utf-8 -*-
"""築未科技 — 認證 + 安全 API Router"""
import secrets
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from routers.deps import (
    _extract_token, _require_admin, _require_superadmin,
    auth_manager, sec_mw, logger,
    ADMIN_USER, ADMIN_PASSWORD, SESSION_COOKIE, _sessions,
    _auth_configured, AuthRequest,
)

router = APIRouter(tags=["認證"])


# ── Session 登入 ──
@router.get("/login", response_class=HTMLResponse)
async def get_login(request: Request, err: str = ""):
    if _auth_configured():
        sid = request.cookies.get(SESSION_COOKIE)
        if sid and sid in _sessions:
            return RedirectResponse(url="/admin", status_code=302)
    err_msg = '<p class="text-rose-400 text-sm text-center mb-2">帳號或密碼錯誤</p>' if err else ""
    html = f"""<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>築未科技 — 登入</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-900 text-slate-100 min-h-screen flex items-center justify-center p-4">
<div class="w-full max-w-sm rounded-2xl bg-slate-800/80 border border-slate-600 shadow-xl p-6">
<h1 class="text-xl font-bold text-center text-blue-400 mb-6">築未科技 系統登入</h1>
{err_msg}
<form method="post" action="/login" class="space-y-4">
<input type="text" name="username" placeholder="帳號" required class="w-full px-4 py-3 rounded-lg bg-slate-700 border border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-transparent">
<input type="password" name="password" placeholder="密碼" required class="w-full px-4 py-3 rounded-lg bg-slate-700 border border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-transparent">
<button type="submit" class="w-full py-3 rounded-lg bg-blue-600 hover:bg-blue-500 font-medium transition">登入</button>
</form>
<p class="text-xs text-slate-400 mt-4 text-center">最高權限帳密請存於 .env（ADMIN_USER / ADMIN_PASSWORD）</p>
</div></body></html>"""
    return HTMLResponse(html)


@router.post("/login")
async def post_login(request: Request, username: str = Form(""), password: str = Form("")):
    if not _auth_configured():
        return RedirectResponse(url="/admin", status_code=302)
    if username == ADMIN_USER and password == ADMIN_PASSWORD:
        sid = secrets.token_urlsafe(32)
        _sessions[sid] = username
        r = RedirectResponse(url="/admin", status_code=302)
        r.set_cookie(key=SESSION_COOKIE, value=sid, max_age=24 * 3600, httponly=True, samesite="lax")
        return r
    return RedirectResponse(url="/login?err=1", status_code=302)


@router.get("/logout")
async def logout():
    r = RedirectResponse(url="/login", status_code=302)
    r.delete_cookie(SESSION_COOKIE)
    return r


# ── JWT API ──
@router.post("/api/auth/register")
async def api_auth_register(body: AuthRequest):
    return auth_manager.register_user(body.username, body.password, body.email)


@router.post("/api/auth/login")
async def api_auth_login(body: AuthRequest):
    return auth_manager.login_user(body.username, body.password)


@router.post("/api/auth/subscribe")
async def api_auth_subscribe(request: Request):
    payload = await request.json()
    username = str((payload or {}).get("username", "")).strip()
    plan = str((payload or {}).get("plan", "basic")).strip()
    if not username:
        raise HTTPException(status_code=400, detail="username is required")
    return auth_manager.confirm_subscription(username, plan)


@router.get("/api/auth/me")
async def api_auth_me(request: Request):
    data = _extract_token(request)
    if not data:
        return {"ok": False, "error": "未登入"}
    user = auth_manager.get_user_info(data.get("sub", ""))
    if not user:
        return {"ok": False, "error": "用戶不存在"}
    return {"ok": True, "user": user}


@router.get("/api/auth/users")
async def api_auth_users(request: Request):
    data = _require_admin(request)
    users = auth_manager.list_users(data.get("role", ""))
    return {"ok": True, "users": users}


@router.post("/api/auth/activate")
async def api_auth_activate(request: Request):
    _require_admin(request)
    payload = await request.json()
    user_id = str((payload or {}).get("user_id", "")).strip()
    plan = str((payload or {}).get("plan", "basic")).strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    return auth_manager.activate_subscription(user_id, plan)


@router.get("/api/auth/logout")
async def api_auth_logout():
    return {"ok": True, "message": "已登出，請清除本地 Token"}


# ── 安全管理 API ──
@router.post("/api/security/api-keys")
async def api_create_api_key(request: Request):
    if not sec_mw:
        return {"ok": False, "error": "安全模組未安裝"}
    _require_admin(request)
    payload = await request.json()
    tenant_slug = str((payload or {}).get("tenant_slug", "")).strip()
    description = str((payload or {}).get("description", "")).strip()
    if not tenant_slug:
        raise HTTPException(status_code=400, detail="tenant_slug is required")
    return sec_mw.generate_api_key(tenant_slug, description)


@router.get("/api/security/api-keys")
async def api_list_api_keys(request: Request, tenant_slug: str = ""):
    if not sec_mw:
        return {"ok": False, "error": "安全模組未安裝"}
    _require_admin(request)
    keys = sec_mw.list_api_keys(tenant_slug)
    return {"ok": True, "keys": keys, "count": len(keys)}


@router.post("/api/security/api-keys/revoke")
async def api_revoke_api_key(request: Request):
    if not sec_mw:
        return {"ok": False, "error": "安全模組未安裝"}
    _require_superadmin(request)
    payload = await request.json()
    key_prefix = str((payload or {}).get("key_prefix", "")).strip()
    if not key_prefix:
        raise HTTPException(status_code=400, detail="key_prefix is required")
    return sec_mw.revoke_api_key(key_prefix)


@router.get("/api/security/rate-limits")
async def api_rate_limit_stats(request: Request):
    if not sec_mw:
        return {"ok": False, "error": "安全模組未安裝"}
    _require_admin(request)
    return {"ok": True, **sec_mw.rate_limiter.get_stats()}

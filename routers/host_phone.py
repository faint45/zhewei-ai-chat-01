# -*- coding: utf-8 -*-
"""築未科技 — Host API 代理 + Phone Agent Router"""
import json
import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response, JSONResponse
from routers.deps import logger

router = APIRouter(tags=["主機代理"])

HOST_API = os.environ.get("HOST_API_URL", "http://host.docker.internal:8010").rstrip("/")


def _proxy_host(path: str, params: dict | None = None, method: str = "GET", json_body: dict | None = None) -> dict:
    import urllib.request, urllib.parse
    url = f"{HOST_API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        if method == "POST" and json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        else:
            req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": f"Host API 不可達: {e}"}


# ── Host API ──
@router.get("/api/host/screenshot")
async def api_host_screenshot(format: str = "base64"):
    return _proxy_host("/screenshot", {"format": format})


@router.get("/api/host/screenshot/png")
async def api_host_screenshot_png():
    import urllib.request
    url = f"{HOST_API}/screenshot?format=png"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=15) as resp:
            return Response(content=resp.read(), media_type="image/png")
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)


@router.get("/api/host/sysinfo")
async def api_host_sysinfo():
    return _proxy_host("/sysinfo")


@router.get("/api/host/windows")
async def api_host_windows():
    return _proxy_host("/windows")


@router.get("/api/host/processes")
async def api_host_processes(top: int = 20):
    return _proxy_host("/processes", {"top": top})


@router.post("/api/host/execute")
async def api_host_execute(request: Request):
    return _proxy_host("/execute", method="POST", json_body=await request.json())


@router.post("/api/host/search")
async def api_host_search(request: Request):
    return _proxy_host("/search", method="POST", json_body=await request.json())


@router.post("/api/host/open_terminal")
async def api_host_open_terminal(request: Request):
    return _proxy_host("/open_terminal", method="POST", json_body=await request.json())


@router.post("/api/host/keystroke")
async def api_host_keystroke(request: Request):
    return _proxy_host("/keystroke", method="POST", json_body=await request.json())


@router.post("/api/host/mouse")
async def api_host_mouse(request: Request):
    return _proxy_host("/mouse", method="POST", json_body=await request.json())


# ── Phone Agent ──
@router.get("/api/phone/status")
async def api_phone_status():
    try:
        from phone_agent import ADBController, droidrun_available, PHONE_ADB_HOST, PHONE_ADB_PORT
        adb = ADBController()
        return {"ok": True, "connected": adb.is_connected(), "device": f"{PHONE_ADB_HOST}:{PHONE_ADB_PORT}", "droidrun_available": droidrun_available()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/phone/connect")
async def api_phone_connect(request: Request):
    try:
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    except Exception:
        body = {}
    try:
        from phone_agent import phone_connect
        return phone_connect(body.get("host", ""), body.get("port", ""))
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/api/phone/disconnect")
async def api_phone_disconnect():
    try:
        from phone_agent import phone_disconnect
        return phone_disconnect()
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/api/phone/screenshot")
async def api_phone_screenshot():
    try:
        from phone_agent import phone_screenshot
        return phone_screenshot()
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/api/phone/task")
async def api_phone_task(request: Request):
    body = await request.json()
    task = body.get("task", "").strip()
    if not task:
        return {"success": False, "message": "task 必填"}
    try:
        from phone_agent import phone_task_async
        return await phone_task_async(task, body.get("host", ""), body.get("port", ""))
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/api/phone/line/reply")
async def api_phone_line_reply(request: Request):
    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        return {"success": False, "message": "message 必填"}
    try:
        from phone_agent import line_reply
        return line_reply(message, body.get("contact", ""))
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/api/phone/line/read")
async def api_phone_line_read():
    try:
        from phone_agent import line_read_latest
        return line_read_latest()
    except Exception as e:
        return {"success": False, "message": str(e)}

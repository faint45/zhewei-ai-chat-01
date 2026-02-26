"""
築未科技大腦橋接 API - FastAPI 版（生產部署用）
搭配 gunicorn -k uvicorn.workers.UvicornWorker 使用
支援：API Key 或 帳號/密碼登入 + Session、API 日誌、健康檢查、Session 持久化、依用戶限流
"""
import sys
import hashlib
import json
import os
import secrets
import socket
import time
from collections import defaultdict
from pathlib import Path

# 添加 tools 目录到 Python 路径
tools_dir = str(Path(__file__).parent.parent / "tools")
if tools_dir not in sys.path:
    sys.path.append(tools_dir)

BASE = Path(__file__).parent.resolve()
os.chdir(str(BASE))

try:
    from dotenv import load_dotenv
    load_dotenv()
    _user_env = Path.home() / ".openclaw" / ".env"
    if _user_env.exists():
        load_dotenv(_user_env, override=True)
except ImportError:
    pass

try:
    from fastapi import FastAPI, Request, HTTPException, Depends
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, HTMLResponse
    from starlette.middleware.base import BaseHTTPMiddleware
except ImportError:
    print("請安裝: pip install fastapi uvicorn")
    raise

from guard_core import (
    process_message,
    get_weather,
    get_time,
    grant_auth,
    revoke_auth,
    _is_authorized,
    _can_control,
    run_agent,
)

try:
    from brain_data_config import LOG_DIR, API_LOG_FILE, BRAIN_DATA_DIR, SESSIONS_FILE
except ImportError:
    LOG_DIR = BASE / "logs"
    API_LOG_FILE = LOG_DIR / "brain_bridge_api.ndjson"
    BRAIN_DATA_DIR = Path(os.environ.get("ZHEWEI_BRAIN_DATA_DIR", "D:/zhewei_brain_data"))
    SESSIONS_FILE = BRAIN_DATA_DIR / "brain_sessions.json"
LOG_DIR.mkdir(parents=True, exist_ok=True)

MSG_MAX_LEN = int(os.environ.get("BRAIN_MSG_MAX_LEN", "50000"))
USER_ID_MAX_LEN = int(os.environ.get("BRAIN_USER_ID_MAX_LEN", "200"))

# CORS：商用可設 CORS_ORIGINS=https://your-domain.com,https://app.example.com
CORS_ORIGINS_RAW = os.environ.get("CORS_ORIGINS", "*").strip()
CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS_RAW.split(",") if o.strip()] if CORS_ORIGINS_RAW != "*" else ["*"]

app = FastAPI(title="築未科技大腦橋接 API", version="2.2")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"], allow_credentials=True)

# API 請求日誌 middleware（誰、何時、哪個端點、狀態、耗時）
def _log_user_from_request(req: Request) -> str:
    token = req.headers.get("X-Session-Token") or req.cookies.get("session_token")
    if token and token in _sessions and _sessions[token].get("expires", 0) > time.time():
        return _sessions[token].get("user_id", "") or ""
    return (req.headers.get("X-User-Id") or "").strip()[:USER_ID_MAX_LEN]


class APILogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000)
        try:
            client = request.client.host if request.client else "unknown"
            user = _log_user_from_request(request)
            log_line = json.dumps({
                "ts": time.time(),
                "method": request.method,
                "path": request.url.path,
                "client": client,
                "user_id": user,
                "status": response.status_code,
                "duration_ms": duration_ms,
            }, ensure_ascii=False) + "\n"
            with open(API_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception:
            pass
        return response

app.add_middleware(APILogMiddleware)

API_KEY = os.environ.get("BRAIN_BRIDGE_API_KEY", "").strip()
RATE_LIMIT_PER_MIN = int(os.environ.get("BRAIN_BRIDGE_RATE_LIMIT", "30"))
SESSION_TTL = int(os.environ.get("BRAIN_SESSION_TTL", "86400"))  # 24h
_rate_cache = defaultdict(list)
_RATE_CACHE_MAX_KEYS = 1000

# 帳號密碼：AUTH_USERS="user1:pass1,user2:pass2" 或 "user1:sha256hash"（64 字元 hex）
AUTH_USERS_RAW = os.environ.get("AUTH_USERS", "").strip()
_auth_users: dict[str, str] = {}
if AUTH_USERS_RAW:
    for part in AUTH_USERS_RAW.split(","):
        p = part.strip().split(":", 1)
        if len(p) == 2 and p[0] and p[1]:
            _auth_users[p[0].strip()] = p[1].strip()

_sessions: dict[str, dict] = {}  # token -> {user_id, expires}


def _load_sessions():
    global _sessions
    if not SESSIONS_FILE.exists():
        return
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        now = time.time()
        _sessions = {k: v for k, v in (data or {}).items() if isinstance(v, dict) and v.get("expires", 0) > now}
    except Exception:
        pass


def _save_sessions():
    try:
        BRAIN_DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(_sessions, f, ensure_ascii=False, indent=0)
    except Exception:
        pass


_load_sessions()


def _rate_limit_key(req: Request) -> str:
    """依用戶或 API Key 限流，避免單一用戶佔滿；無則 fallback IP"""
    token = req.headers.get("X-Session-Token") or req.cookies.get("session_token")
    if token and token in _sessions and _sessions[token].get("expires", 0) > time.time():
        return "u:" + (_sessions[token].get("user_id", "") or "web")
    key = req.headers.get("X-API-Key") or req.query_params.get("api_key")
    if key:
        return "k:" + hashlib.sha256(key.encode()).hexdigest()[:16]
    return req.client.host if req.client else "unknown"


def _prune_rate_cache():
    """定期清理過期 key，避免長期運行後 _rate_cache 膨脹"""
    if len(_rate_cache) <= _RATE_CACHE_MAX_KEYS:
        return
    now = time.time()
    cutoff = now - 60
    to_del = [k for k, times in _rate_cache.items() if not times or max(times) < cutoff]
    for k in to_del:
        del _rate_cache[k]


def _check_rate_limit(req: Request) -> None:
    if RATE_LIMIT_PER_MIN <= 0:
        return
    _prune_rate_cache()
    key = _rate_limit_key(req)
    now = time.time()
    cutoff = now - 60
    _rate_cache[key] = [t for t in _rate_cache[key] if t > cutoff]
    if len(_rate_cache[key]) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail=f"速率限制：每分鐘最多 {RATE_LIMIT_PER_MIN} 次")
    _rate_cache[key].append(now)


def _verify_password(username: str, password: str) -> bool:
    if username not in _auth_users:
        return False
    stored = _auth_users[username]
    if len(stored) == 64 and all(c in "0123456789abcdef" for c in stored.lower()):
        return hashlib.sha256(password.encode()).hexdigest() == stored
    return stored == password


def _require_auth(req: Request) -> bool:
    if not API_KEY and not _auth_users:
        return True
    key = req.headers.get("X-API-Key") or req.query_params.get("api_key")
    if API_KEY and key == API_KEY:
        return True
    token = req.headers.get("X-Session-Token") or req.cookies.get("session_token")
    if token and token in _sessions:
        s = _sessions[token]
        if s.get("expires", 0) > time.time():
            return True
        del _sessions[token]
    return False


def _get_user_from_request(req: Request) -> str:
    token = req.headers.get("X-Session-Token") or req.cookies.get("session_token")
    if token and token in _sessions:
        s = _sessions[token]
        if s.get("expires", 0) > time.time():
            return s.get("user_id", "web")
    return req.headers.get("X-User-Id") or "web"


# 靜態頁面（登入、Demo）
_public_dir = BASE / "public"


@app.get("/login", response_class=HTMLResponse)
def serve_login():
    """登入頁面"""
    p = _public_dir / "login.html"
    if p.exists():
        return FileResponse(p)
    return HTMLResponse("<h1>登入</h1><p>請設定 AUTH_USERS 並建立 public/login.html</p>")


@app.get("/demo", response_class=HTMLResponse)
def serve_demo():
    """運算 Demo 頁面（需先登入）"""
    p = _public_dir / "brain-api-demo.html"
    if p.exists():
        return FileResponse(p)
    return HTMLResponse("<h1>Demo</h1><p>brain-api-demo.html 未找到</p>")


@app.get("/chat", response_class=HTMLResponse)
def serve_chat():
    """手機與電腦對話窗口"""
    p = _public_dir / "chat.html"
    if p.exists():
        return FileResponse(p)
    return HTMLResponse("<h1>對話窗口</h1><p>chat.html 未找到</p>")


@app.get("/health")
def health():
    return {"ok": True, "service": "zhewei-brain-bridge", "features": ["chat", "agent", "weather", "time", "auth", "dev", "session"]}


@app.get("/ready")
def ready():
    """健康檢查擴充：含依賴狀態（Ollama 等），維運可依此判斷是否可接流量"""
    deps = {}
    try:
        import requests
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        r = requests.get(f"{ollama_url}/api/tags", timeout=2)
        deps["ollama"] = r.status_code == 200
    except Exception:
        deps["ollama"] = False
    try:
        from brain_data_config import KNOWLEDGE_FILE
        deps["knowledge_file"] = KNOWLEDGE_FILE.exists()
    except Exception:
        deps["knowledge_file"] = True
    ok = True
    return {"ok": ok, "service": "zhewei-brain-bridge", "deps": deps}


def _get_host_ips():
    """取得本機對外 IP（不含 127.x），供遠端連線測試用"""
    ips = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            pass
    return ips or ["127.0.0.1"]


@app.get("/remote-info")
def remote_info():
    """遠端連線測試：回傳本機 IP、登入網址，供手機/另一台電腦開啟"""
    port = int(os.environ.get("BRAIN_BRIDGE_PORT", "5100"))
    ips = _get_host_ips()
    first = ips[0] if ips else "127.0.0.1"
    return {
        "ok": True,
        "port": port,
        "host_ips": ips,
        "login_url": f"http://{first}:{port}/login",
        "demo_url": f"http://{first}:{port}/demo",
        "health_url": f"http://{first}:{port}/health",
        "message": "從同一網路的手機或電腦開啟 login_url 即可測試遠端登入。",
    }


def _validate_message(msg: str) -> None:
    if not msg or not msg.strip():
        raise HTTPException(status_code=400, detail="message is required")
    if len(msg) > MSG_MAX_LEN:
        raise HTTPException(status_code=400, detail=f"message too long (max {MSG_MAX_LEN})")


def _validate_user_id(uid: str) -> str:
    uid = str(uid or "").strip()[:USER_ID_MAX_LEN]
    return uid or "web"


@app.post("/chat")
async def chat(req: Request):
    if not _require_auth(req):
        raise HTTPException(status_code=401, detail="API key required")
    _check_rate_limit(req)
    data = await req.json() if req.headers.get("content-type", "").startswith("application/json") else {}
    msg = (data.get("message") or "").strip()
    _validate_message(msg)
    user_id = _validate_user_id(data.get("user_id") or "mobile")
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    try:
        result, msg_type = process_message(msg, user_id, base_url, model)
        return {"reply": result, "type": msg_type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent")
async def agent_chat(req: Request):
    if not _require_auth(req):
        raise HTTPException(status_code=401, detail="API key required")
    _check_rate_limit(req)
    data = await req.json() if req.headers.get("content-type", "").startswith("application/json") else {}
    msg = (data.get("message") or "").strip()
    _validate_message(msg)
    user_id = _validate_user_id(data.get("user_id") or "mobile")
    try:
        result = run_agent(msg, user_id)
        return {"reply": result, "type": "agent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/weather")
def weather(city: str = ""):
    w = get_weather(city)
    return {"weather": w or "無法取得天氣", "city": city or "嘉義"}


@app.get("/time")
def time_now():
    return {"time": get_time()}


@app.post("/auth/grant")
async def auth_grant(req: Request):
    if not _require_auth(req):
        raise HTTPException(status_code=401, detail="API key required")
    data = await req.json() if req.headers.get("content-type", "").startswith("application/json") else {}
    user_id = str(data.get("user_id") or "mobile")
    if not _can_control(user_id):
        raise HTTPException(status_code=403, detail="本機操作僅限授權用戶")
    grant_auth(user_id)
    return {"reply": "✅ 已授權。接下來 10 分鐘內可執行本機指令。"}


@app.post("/auth/revoke")
async def auth_revoke(req: Request):
    if not _require_auth(req):
        raise HTTPException(status_code=401, detail="API key required")
    data = await req.json() if req.headers.get("content-type", "").startswith("application/json") else {}
    user_id = str(data.get("user_id") or "mobile")
    revoke_auth(user_id)
    return {"reply": "✅ 已關閉授權。"}


@app.get("/auth/status")
def auth_status(user_id: str = "mobile"):
    return {"authorized": _is_authorized(user_id), "user_id": user_id}


# ========== 帳號/密碼登入 + Session ==========

@app.post("/auth/login")
async def auth_login(req: Request):
    """
    帳號密碼登入，回傳 session_token。
    Body: { "username": str, "password": str }
    """
    if not _auth_users:
        raise HTTPException(status_code=503, detail="未設定 AUTH_USERS，請在 .env 設定")
    data = await req.json() if req.headers.get("content-type", "").startswith("application/json") else {}
    username = (data.get("username") or "").strip()
    password = data.get("password", "")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username 與 password 為必填")
    if not _verify_password(username, password):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    token = secrets.token_urlsafe(32)
    _sessions[token] = {"user_id": username, "expires": time.time() + SESSION_TTL}
    _save_sessions()
    return {"session_token": token, "user_id": username, "expires_in": SESSION_TTL}


@app.post("/auth/logout")
async def auth_logout(req: Request):
    """登出，使 Session 失效"""
    data = await req.json() if req.headers.get("content-type", "").startswith("application/json") else {}
    token = data.get("session_token") or req.headers.get("X-Session-Token")
    if token and token in _sessions:
        del _sessions[token]
        _save_sessions()
    return {"reply": "已登出"}


@app.get("/auth/me")
async def auth_me(req: Request):
    """取得目前登入使用者（需 Session）"""
    token = req.headers.get("X-Session-Token") or req.cookies.get("session_token")
    if token and token in _sessions:
        s = _sessions[token]
        if s.get("expires", 0) > time.time():
            return {"user_id": s.get("user_id"), "authenticated": True}
    return {"authenticated": False}


# ========== 外部接入：設備、軟件、網頁運算介面 ==========

@app.post("/compute")
async def compute(req: Request):
    """
    統一運算介面：供設備、軟件、網頁接入
    Body: { "message": str, "user_id": str?, "source": "device"|"software"|"web", "device_id": str? }
    """
    if not _require_auth(req):
        raise HTTPException(status_code=401, detail="API key required")
    _check_rate_limit(req)
    data = await req.json() if req.headers.get("content-type", "").startswith("application/json") else {}
    msg = (data.get("message") or "").strip()
    _validate_message(msg)
    user_id = _validate_user_id(data.get("user_id") or data.get("device_id") or "external")
    source = data.get("source", "web")
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    try:
        result, msg_type = process_message(msg, user_id, base_url, model)
        try:
            from ai_cost_tracker import record
            record(msg, result or "", "api", actor_id=user_id)
        except Exception:
            pass
        return {"reply": result, "type": msg_type, "source": source}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/integrations/info")
def integrations_info():
    """接入資訊：端點、版本、支援來源"""
    return {
        "service": "zhewei-brain-bridge",
        "version": "2.2",
        "base_url": os.environ.get("BRAIN_BRIDGE_BASE_URL", "http://127.0.0.1:5100"),
        "endpoints": {
            "compute": "POST /compute",
            "chat": "POST /chat",
            "agent": "POST /agent",
            "weather": "GET /weather",
            "time": "GET /time",
            "health": "GET /health",
            "ready": "GET /ready",
            "usage": "GET /usage",
        },
        "sources": ["device", "software", "web"],
    }


@app.get("/usage")
def usage():
    """當月用量與預算（供 Demo 頁顯示）；不需認證"""
    try:
        from ai_cost_tracker import get_month_total_twd, BUDGET_TWD, format_cost_twd
        month_twd = get_month_total_twd()
        return {"ok": True, "month_twd": month_twd, "budget_twd": BUDGET_TWD, "formatted": format_cost_twd(month_twd) + " / " + format_cost_twd(BUDGET_TWD)}
    except Exception:
        return {"ok": True, "month_twd": 0, "budget_twd": 1000, "formatted": "NT$0 / NT$1,000"}


@app.post("/integrations/query")
async def integrations_query(req: Request):
    """知識庫查詢：供外部軟件/網頁查詢"""
    if not _require_auth(req):
        raise HTTPException(status_code=401, detail="API key required")
    _check_rate_limit(req)
    data = await req.json() if req.headers.get("content-type", "").startswith("application/json") else {}
    q = (data.get("query") or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="query is required")
    if len(q) > MSG_MAX_LEN:
        raise HTTPException(status_code=400, detail=f"query too long (max {MSG_MAX_LEN})")
    limit = min(int(data.get("limit", 8)), 20)
    try:
        from brain_knowledge import search
        text = search(q, limit=limit)
        results = [text] if (text and text.strip()) else []
        return {"query": q, "results": results}
    except Exception as e:
        return {"query": q, "results": [], "error": str(e)}

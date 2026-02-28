# -*- coding: utf-8 -*-
"""
築未科技 — 用戶認證管理模組
─────────────────────────────
- PostgreSQL 優先，JSON 檔案備援（PG 不可用時自動降級）
- JWT Token 簽發與驗證
- 角色：superadmin / admin / subscriber / pending
- 訂閱狀態：active / pending / expired
"""
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from pathlib import Path

# ── 設定 ──
ROOT = Path(__file__).resolve().parent
USERS_FILE = ROOT / "brain_workspace" / "auth" / "users.json"
_JWT_FALLBACK = "zhewei-jarvis-secret-2026-CHANGE-ME-IN-ENV"
JWT_SECRET = os.environ.get("JWT_SECRET", "").strip() or _JWT_FALLBACK
if JWT_SECRET == _JWT_FALLBACK:
    import logging as _logging
    _logging.getLogger("zhewei.auth").warning("JWT_SECRET not set in .env — using insecure fallback. Set JWT_SECRET for production!")
JWT_EXPIRY = int(os.environ.get("JWT_EXPIRY", 86400 * 7))  # 預設 7 天

# ── PostgreSQL 支援（商用模式）──
_pg_available = False
_db_pg = None
try:
    import db_postgres as _db_pg
    _db_pg._get_conn().close()
    _pg_available = True
except Exception:
    _db_pg = None

# ── 密碼雜湊 ──
def _hash_password(password: str, salt: str = "") -> tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return h.hex(), salt

def _verify_password(password: str, hashed: str, salt: str) -> bool:
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return hmac.compare_digest(h.hex(), hashed)

# ── JWT（輕量自製，不依賴外部套件）──
import base64

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _b64url_decode(s: str) -> bytes:
    s += "=" * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)

def create_token(user_id: str, username: str, role: str, subscription: str) -> str:
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload_data = {
        "sub": user_id,
        "usr": username,
        "role": role,
        "sub_status": subscription,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRY,
    }
    payload = _b64url_encode(json.dumps(payload_data).encode())
    signature = hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    sig = _b64url_encode(signature)
    return f"{header}.{payload}.{sig}"

def verify_token(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, sig = parts
        expected_sig = _b64url_encode(
            hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig, expected_sig):
            return None
        data = json.loads(_b64url_decode(payload))
        if data.get("exp", 0) < time.time():
            return None
        return data
    except Exception:
        return None

# ── 用戶資料庫（JSON 檔案）──
def _load_users() -> dict:
    if not USERS_FILE.exists():
        return {}
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_users(users: dict):
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")

def _ensure_superadmin():
    """確保超級管理員帳號存在。"""
    users = _load_users()
    sa_username = "allen34556"
    # 檢查是否已存在
    for uid, u in users.items():
        if u.get("username") == sa_username:
            # 確保角色和訂閱狀態正確
            if u.get("role") != "superadmin" or u.get("subscription") != "active":
                u["role"] = "superadmin"
                u["subscription"] = "active"
                _save_users(users)
            return
    # 建立超級管理員
    uid = str(uuid.uuid4())
    hashed, salt = _hash_password("Rr124243084")
    users[uid] = {
        "id": uid,
        "username": sa_username,
        "email": "",
        "password_hash": hashed,
        "password_salt": salt,
        "role": "superadmin",          # superadmin / admin / subscriber / pending
        "subscription": "active",      # active / pending / expired
        "subscription_plan": "unlimited",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    _save_users(users)

# ── 公開 API ──
def register_user(username: str, password: str, email: str = "") -> dict:
    """註冊新用戶（預設 pending 狀態，需訂閱後才能使用）。"""
    # PG 優先
    if _pg_available and _db_pg:
        try:
            result = _db_pg.register_user(username, password, email)
            if result.get("ok"):
                # 同步寫入 JSON 備份
                _register_json_fallback(username, password, email, result.get("user_id"))
            return result
        except Exception:
            pass  # PG 失敗，降級 JSON

    username = (username or "").strip()
    password = (password or "").strip()
    email = (email or "").strip()
    if not username or not password:
        return {"ok": False, "error": "帳號和密碼為必填"}
    if len(username) < 4:
        return {"ok": False, "error": "帳號至少 4 個字元"}
    if len(password) < 6:
        return {"ok": False, "error": "密碼至少 6 個字元"}

    users = _load_users()
    for uid, u in users.items():
        if u.get("username") == username:
            return {"ok": False, "error": "此帳號已被使用"}
        if email and u.get("email") == email:
            return {"ok": False, "error": "此 Email 已被使用"}

    uid = str(uuid.uuid4())
    hashed, salt = _hash_password(password)
    users[uid] = {
        "id": uid,
        "username": username,
        "email": email,
        "password_hash": hashed,
        "password_salt": salt,
        "role": "pending",
        "subscription": "pending",
        "subscription_plan": "",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    _save_users(users)
    return {"ok": True, "user_id": uid, "username": username}


def _register_json_fallback(username, password, email, uid):
    """PG 成功後同步寫入 JSON 備份。"""
    try:
        users = _load_users()
        hashed, salt = _hash_password(password)
        users[uid] = {
            "id": uid, "username": username, "email": email,
            "password_hash": hashed, "password_salt": salt,
            "role": "pending", "subscription": "pending", "subscription_plan": "",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        _save_users(users)
    except Exception:
        pass

def login_user(username: str, password: str) -> dict:
    """登入驗證，成功回傳 JWT Token。"""
    # PG 優先
    if _pg_available and _db_pg:
        try:
            return _db_pg.login_user(username, password)
        except Exception:
            pass  # PG 失敗，降級 JSON

    username = (username or "").strip()
    password = (password or "").strip()
    if not username or not password:
        return {"ok": False, "error": "帳號和密碼為必填"}

    users = _load_users()
    for uid, u in users.items():
        if u.get("username") == username:
            if _verify_password(password, u.get("password_hash", ""), u.get("password_salt", "")):
                token = create_token(uid, username, u.get("role", "pending"), u.get("subscription", "pending"))
                return {
                    "ok": True,
                    "token": token,
                    "user": {
                        "id": uid,
                        "username": username,
                        "role": u.get("role", "pending"),
                        "subscription": u.get("subscription", "pending"),
                        "subscription_plan": u.get("subscription_plan", ""),
                    },
                }
            else:
                return {"ok": False, "error": "密碼錯誤"}
    return {"ok": False, "error": "帳號不存在"}

def get_user_info(user_id: str) -> dict | None:
    """取得用戶資訊（不含密碼）。"""
    # PG 優先
    if _pg_available and _db_pg:
        try:
            info = _db_pg.get_user_info(user_id)
            if info:
                return info
        except Exception:
            pass

    users = _load_users()
    u = users.get(user_id)
    if not u:
        return None
    return {
        "id": u.get("id"),
        "username": u.get("username"),
        "email": u.get("email"),
        "role": u.get("role"),
        "subscription": u.get("subscription"),
        "subscription_plan": u.get("subscription_plan"),
        "created_at": u.get("created_at"),
    }

def activate_subscription(user_id: str, plan: str = "basic") -> dict:
    """啟用訂閱（管理員或付款確認後呼叫）。"""
    # PG 優先
    if _pg_available and _db_pg:
        try:
            result = _db_pg.activate_subscription(user_id, plan)
            if result.get("ok"):
                # 同步更新 JSON
                users = _load_users()
                if user_id in users:
                    users[user_id]["subscription"] = "active"
                    users[user_id]["subscription_plan"] = plan
                    _save_users(users)
            return result
        except Exception:
            pass

    users = _load_users()
    u = users.get(user_id)
    if not u:
        return {"ok": False, "error": "用戶不存在"}
    u["subscription"] = "active"
    u["subscription_plan"] = plan
    u["role"] = "subscriber" if u.get("role") == "pending" else u.get("role")
    u["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _save_users(users)
    return {"ok": True, "user_id": user_id, "subscription": "active", "plan": plan}

def confirm_subscription(username: str, plan: str = "basic") -> dict:
    """透過用戶名確認訂閱。"""
    users = _load_users()
    for uid, u in users.items():
        if u.get("username") == username:
            return activate_subscription(uid, plan)
    return {"ok": False, "error": "用戶不存在"}

def list_users(requester_role: str = "") -> list[dict]:
    """列出所有用戶（僅 superadmin/admin 可用）。"""
    # PG 優先
    if _pg_available and _db_pg:
        try:
            return _db_pg.list_users(requester_role)
        except Exception:
            pass

    if requester_role not in ("superadmin", "admin"):
        return []
    users = _load_users()
    result = []
    for uid, u in users.items():
        result.append({
            "id": uid,
            "username": u.get("username"),
            "email": u.get("email"),
            "role": u.get("role"),
            "subscription": u.get("subscription"),
            "subscription_plan": u.get("subscription_plan"),
            "created_at": u.get("created_at"),
        })
    return result

def is_authorized(token_data: dict) -> bool:
    """檢查用戶是否已授權（superadmin/admin 永遠通過，subscriber 需 active 訂閱）。"""
    if not token_data:
        return False
    role = token_data.get("role", "")
    if role in ("superadmin", "admin"):
        return True
    if role == "subscriber" and token_data.get("sub_status") == "active":
        return True
    return False

# ── 初始化 ──
_ensure_superadmin()

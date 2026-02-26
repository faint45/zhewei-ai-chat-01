# -*- coding: utf-8 -*-
"""
築未科技 — 安全 & 可靠性中間件

商用核心安全層：
  1. Rate Limiting（全域 + 每用戶 + 每 IP）
  2. API Key 認證（租戶級別）
  3. ECPay Callback IP 白名單
  4. 請求日誌 & 異常追蹤
  5. 優雅關機信號處理

設計原則：
  - 零依賴（僅用標準庫 + FastAPI）
  - 記憶體內限流（高效能，無外部 Redis 依賴）
  - 可選 Redis 升級路徑
"""
import hashlib
import hmac
import os
import time
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent

# ── Rate Limiting 設定 ──
# 格式：(max_requests, window_seconds)
RATE_LIMITS = {
    "global": (500, 60),          # 全域：500 req/min
    "per_ip": (60, 60),           # 每 IP：60 req/min
    "per_user": (120, 60),        # 每用戶：120 req/min
    "auth": (10, 60),             # 登入/註冊：10 req/min（防暴力破解）
    "payment": (5, 60),           # 付款：5 req/min
    "ai_chat": (30, 60),          # AI 對話：30 req/min
    "learn": (20, 60),            # 學習寫入：20 req/min
}

# 可透過環境變數覆蓋
for key in RATE_LIMITS:
    env_key = f"RATE_LIMIT_{key.upper()}"
    env_val = os.environ.get(env_key, "").strip()
    if env_val and "," in env_val:
        parts = env_val.split(",")
        try:
            RATE_LIMITS[key] = (int(parts[0]), int(parts[1]))
        except ValueError:
            pass


class RateLimiter:
    """記憶體內滑動窗口限流器。"""

    def __init__(self):
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._last_cleanup = time.time()

    def is_allowed(self, key: str, category: str = "per_ip") -> tuple[bool, dict]:
        """
        檢查是否允許請求。
        Returns: (allowed, info_dict)
        """
        max_req, window = RATE_LIMITS.get(category, (100, 60))
        now = time.time()
        bucket_key = f"{category}:{key}"

        with self._lock:
            # 清理過期記錄
            self._buckets[bucket_key] = [
                t for t in self._buckets[bucket_key] if t > now - window
            ]
            current = len(self._buckets[bucket_key])

            if current >= max_req:
                retry_after = int(self._buckets[bucket_key][0] + window - now) + 1
                return False, {
                    "limit": max_req,
                    "remaining": 0,
                    "retry_after": retry_after,
                    "category": category,
                }

            self._buckets[bucket_key].append(now)
            # 定期清理（每 5 分鐘）
            if now - self._last_cleanup > 300:
                self._cleanup(now)
                self._last_cleanup = now

            return True, {
                "limit": max_req,
                "remaining": max_req - current - 1,
                "category": category,
            }

    def _cleanup(self, now: float):
        """清理所有過期 bucket。"""
        expired = []
        for key, timestamps in self._buckets.items():
            self._buckets[key] = [t for t in timestamps if t > now - 120]
            if not self._buckets[key]:
                expired.append(key)
        for key in expired:
            del self._buckets[key]

    def get_stats(self) -> dict:
        """取得限流統計。"""
        with self._lock:
            return {
                "total_buckets": len(self._buckets),
                "categories": {
                    cat: {"limit": lim, "window_sec": win}
                    for cat, (lim, win) in RATE_LIMITS.items()
                },
            }


# 全域限流器實例
rate_limiter = RateLimiter()


# ── API Key 管理 ──

def generate_api_key(tenant_slug: str, description: str = "") -> dict:
    """為租戶生成 API Key。"""
    import secrets
    key = f"zw_{tenant_slug}_{secrets.token_hex(16)}"
    key_hash = hashlib.sha256(key.encode()).hexdigest()

    try:
        import db_postgres
        conn = db_postgres._get_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO api_keys (tenant_id, key_hash, key_prefix, description, status)
               SELECT t.id, %s, %s, %s, 'active'
               FROM tenants t WHERE t.slug = %s
               RETURNING id""",
            (key_hash, key[:12], description or f"API Key for {tenant_slug}", tenant_slug),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if row:
            return {"ok": True, "api_key": key, "key_prefix": key[:12], "key_id": str(row[0])}
        return {"ok": False, "error": "租戶不存在"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def verify_api_key(api_key: str) -> dict | None:
    """
    驗證 API Key，回傳租戶資訊。
    Returns: {"tenant_id": ..., "tenant_slug": ..., "plan": ...} or None
    """
    if not api_key or not api_key.startswith("zw_"):
        return None
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    try:
        import db_postgres
        conn = db_postgres._get_conn()
        cur = conn.cursor()
        cur.execute(
            """SELECT ak.tenant_id, t.slug, t.plan, t.name, ak.id
               FROM api_keys ak
               JOIN tenants t ON ak.tenant_id = t.id
               WHERE ak.key_hash = %s AND ak.status = 'active'""",
            (key_hash,),
        )
        row = cur.fetchone()
        if row:
            # 更新最後使用時間
            cur.execute("UPDATE api_keys SET last_used_at = NOW() WHERE id = %s", (row[4],))
            conn.commit()
        cur.close()
        conn.close()
        if row:
            return {
                "tenant_id": str(row[0]),
                "tenant_slug": row[1],
                "plan": row[2],
                "tenant_name": row[3],
            }
        return None
    except Exception:
        return None


def revoke_api_key(key_prefix: str) -> dict:
    """撤銷 API Key（用 prefix 識別）。"""
    try:
        import db_postgres
        conn = db_postgres._get_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE api_keys SET status = 'revoked' WHERE key_prefix = %s",
            (key_prefix,),
        )
        affected = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        return {"ok": True, "revoked": affected}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_api_keys(tenant_slug: str = "") -> list[dict]:
    """列出 API Keys。"""
    try:
        import db_postgres
        conn = db_postgres._get_conn()
        cur = conn.cursor()
        if tenant_slug:
            cur.execute(
                """SELECT ak.id, ak.key_prefix, ak.description, ak.status, ak.created_at, ak.last_used_at, t.slug
                   FROM api_keys ak JOIN tenants t ON ak.tenant_id = t.id
                   WHERE t.slug = %s ORDER BY ak.created_at DESC""",
                (tenant_slug,),
            )
        else:
            cur.execute(
                """SELECT ak.id, ak.key_prefix, ak.description, ak.status, ak.created_at, ak.last_used_at, t.slug
                   FROM api_keys ak JOIN tenants t ON ak.tenant_id = t.id
                   ORDER BY ak.created_at DESC LIMIT 100""",
            )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "id": str(r[0]), "key_prefix": r[1], "description": r[2],
                "status": r[3], "created_at": r[4].isoformat() if r[4] else None,
                "last_used_at": r[5].isoformat() if r[5] else None, "tenant_slug": r[6],
            }
            for r in rows
        ]
    except Exception:
        return []


# ── ECPay IP 白名單 ──

ECPAY_ALLOWED_IPS = {
    # 綠界正式環境 IP（需從綠界文件確認最新 IP）
    "175.99.72.1", "175.99.72.2", "175.99.72.3",
    "211.23.128.214", "211.23.128.215",
    "59.125.88.130", "59.125.88.131",
    # 測試環境（較寬鬆）
    "127.0.0.1", "::1",
}

# 可透過環境變數追加
_extra_ips = os.environ.get("ECPAY_ALLOWED_IPS", "").strip()
if _extra_ips:
    ECPAY_ALLOWED_IPS.update(ip.strip() for ip in _extra_ips.split(",") if ip.strip())

ECPAY_SANDBOX = os.environ.get("ECPAY_SANDBOX", "true").strip().lower() in ("true", "1", "yes")


def is_ecpay_ip_allowed(client_ip: str) -> bool:
    """檢查是否為綠界允許的 IP。Sandbox 模式下放行所有。"""
    if ECPAY_SANDBOX:
        return True
    return client_ip in ECPAY_ALLOWED_IPS


# ── 路由分類（用於限流）──

def classify_route(path: str, method: str = "GET") -> str:
    """根據路由分類限流等級。"""
    p = path.lower()
    if "/auth/login" in p or "/auth/register" in p:
        return "auth"
    if "/payment/" in p:
        return "payment"
    if "/remote/chat" in p or "/api/agent/" in p:
        return "ai_chat"
    if "/learn" in p or "/ask-and-learn" in p:
        return "learn"
    return "per_ip"


def get_client_ip(request) -> str:
    """從 Request 取得真實客戶端 IP（支援反向代理）。"""
    # X-Forwarded-For（Cloudflare / Nginx）
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    # X-Real-IP
    real_ip = request.headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()
    # 直連
    if hasattr(request, "client") and request.client:
        return request.client.host
    return "unknown"


# ── 健康檢查 ──

_startup_time = time.time()
_shutdown_requested = False


def request_shutdown():
    """標記系統正在關機。"""
    global _shutdown_requested
    _shutdown_requested = True


def health_check() -> dict:
    """
    /healthz — 存活檢查（Liveness）。
    只要進程在跑就回 OK。
    """
    return {
        "status": "ok" if not _shutdown_requested else "shutting_down",
        "uptime_seconds": int(time.time() - _startup_time),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def readiness_check() -> dict:
    """
    /readyz — 就緒檢查（Readiness）。
    確認關鍵依賴可用。
    """
    checks = {}

    # PG 連線
    try:
        import db_postgres
        conn = db_postgres._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {str(e)[:80]}"

    # ChromaDB
    try:
        import chromadb
        db_dir = ROOT / "Jarvis_Training" / "chroma_db"
        client = chromadb.PersistentClient(path=str(db_dir))
        client.heartbeat()
        checks["chromadb"] = "ok"
    except Exception as e:
        checks["chromadb"] = f"error: {str(e)[:80]}"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ready" if all_ok and not _shutdown_requested else "not_ready",
        "checks": checks,
        "shutdown_requested": _shutdown_requested,
    }

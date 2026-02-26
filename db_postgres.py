# -*- coding: utf-8 -*-
"""
築未科技 — PostgreSQL 資料庫模組

商用核心：用戶、訂閱、用量、租戶資料統一存放 PostgreSQL。
取代原本的 JSON 檔案儲存，支援並發、事務、索引查詢。

連線設定：
  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/jarvis
  或分開設定 PG_HOST / PG_PORT / PG_USER / PG_PASSWORD / PG_DATABASE
"""
import json
import os
import time
import uuid
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# ── 連線設定 ──
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if not DATABASE_URL:
    PG_HOST = os.environ.get("PG_HOST", "localhost")
    PG_PORT = os.environ.get("PG_PORT", "5432")
    PG_USER = os.environ.get("PG_USER", "postgres")
    PG_PASSWORD = os.environ.get("PG_PASSWORD", "postgres")
    PG_DATABASE = os.environ.get("PG_DATABASE", "jarvis")
    DATABASE_URL = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"

# JWT 設定（與 auth_manager.py 一致）
JWT_SECRET = os.environ.get("JWT_SECRET", "zhewei-jarvis-secret-2025").strip()
JWT_EXPIRY = int(os.environ.get("JWT_EXPIRY", "86400"))


_pool = None
_pool_lock = __import__("threading").Lock()


def _get_pool():
    """取得或建立連線池（ThreadedConnectionPool，支援高併發）。"""
    global _pool
    if _pool and not _pool.closed:
        return _pool
    with _pool_lock:
        if _pool and not _pool.closed:
            return _pool
        import psycopg2.pool
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=int(os.environ.get("PG_POOL_MAX", "20")),
            dsn=DATABASE_URL,
        )
        return _pool


def _get_conn():
    """從連線池取得 PostgreSQL 連線（用完務必歸還）。"""
    try:
        pool = _get_pool()
        conn = pool.getconn()
        conn.autocommit = False
        return conn
    except Exception:
        # 連線池故障時降級為直連
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        conn._from_pool = False
        return conn


def _put_conn(conn):
    """歸還連線到連線池。"""
    if conn is None:
        return
    try:
        if hasattr(conn, "_from_pool") and not conn._from_pool:
            conn.close()
            return
        pool = _get_pool()
        pool.putconn(conn)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass


def init_schema():
    """建立所有資料表（冪等，可重複執行）。"""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        -- 租戶（企業客戶）
        CREATE TABLE IF NOT EXISTS tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            plan TEXT NOT NULL DEFAULT 'free',
            status TEXT NOT NULL DEFAULT 'active',
            settings JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- 用戶
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'pending',
            subscription TEXT NOT NULL DEFAULT 'pending',
            subscription_plan TEXT DEFAULT '',
            subscription_expires_at TIMESTAMPTZ,
            last_login_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- 用量記錄
        CREATE TABLE IF NOT EXISTS usage_records (
            id BIGSERIAL PRIMARY KEY,
            ts DOUBLE PRECISION NOT NULL,
            date DATE NOT NULL,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            task_type TEXT NOT NULL DEFAULT 'chat',
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            duration_ms INTEGER NOT NULL DEFAULT 0,
            estimated_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0,
            success BOOLEAN NOT NULL DEFAULT TRUE,
            error_msg TEXT,
            metadata JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- 每日彙總（加速查詢）
        CREATE TABLE IF NOT EXISTS usage_daily_summary (
            date DATE NOT NULL,
            user_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
            tenant_id UUID,
            provider TEXT NOT NULL,
            total_calls INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            total_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0,
            success_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            avg_duration_ms REAL NOT NULL DEFAULT 0,
            PRIMARY KEY (date, user_id, provider)
        );

        -- 訂閱方案
        CREATE TABLE IF NOT EXISTS subscription_plans (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            monthly_calls INTEGER NOT NULL DEFAULT 100,
            monthly_tokens INTEGER NOT NULL DEFAULT 50000,
            price_ntd INTEGER NOT NULL DEFAULT 0,
            features JSONB DEFAULT '{}',
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- API Keys（租戶/用戶的 API 存取金鑰）
        CREATE TABLE IF NOT EXISTS api_keys (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
            key_hash TEXT NOT NULL,
            key_prefix TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT 'default',
            scopes TEXT[] DEFAULT '{}',
            rate_limit_per_min INTEGER DEFAULT 30,
            expires_at TIMESTAMPTZ,
            last_used_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- 付款記錄
        CREATE TABLE IF NOT EXISTS payments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
            amount_ntd INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'TWD',
            payment_method TEXT NOT NULL DEFAULT 'ecpay',
            payment_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            plan TEXT,
            period_start DATE,
            period_end DATE,
            metadata JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- 索引
        CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_usage_records_date ON usage_records(date);
        CREATE INDEX IF NOT EXISTS idx_usage_records_user ON usage_records(user_id, date);
        CREATE INDEX IF NOT EXISTS idx_usage_records_tenant ON usage_records(tenant_id, date);
        CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
        CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
        CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
    """)
    conn.commit()

    # 插入預設訂閱方案
    cur.execute("""
        INSERT INTO subscription_plans (id, name, monthly_calls, monthly_tokens, price_ntd, features)
        VALUES
            ('free',       '免費版',   100,    50000,    0,    '{"roles": 3, "kb_size": 2000}'),
            ('basic',      '基礎版',   1000,   500000,   499,  '{"roles": 9, "kb_size": 20000, "workflow": true}'),
            ('pro',        '專業版',   5000,   2000000,  999,  '{"roles": 15, "kb_size": 50000, "workflow": true, "vision": true}'),
            ('enterprise', '企業版',   -1,     -1,       4999, '{"roles": -1, "kb_size": -1, "workflow": true, "vision": true, "api": true, "support": true}'),
            ('unlimited',  '無限版',   -1,     -1,       0,    '{"roles": -1, "kb_size": -1, "internal": true}')
        ON CONFLICT (id) DO NOTHING;
    """)
    conn.commit()
    cur.close()
    _put_conn(conn)
    print("✅ PostgreSQL schema 初始化完成")


# ── 用戶管理 ──

def _hash_password(password: str) -> tuple[str, str]:
    salt = os.urandom(16).hex()
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return hashed, salt


def _verify_password(password: str, stored_hash: str, salt: str) -> bool:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex() == stored_hash


def register_user(username: str, password: str, email: str = "", tenant_id: str = None) -> dict:
    """註冊新用戶。"""
    username = (username or "").strip()
    password = (password or "").strip()
    email = (email or "").strip()
    if not username or not password:
        return {"ok": False, "error": "帳號和密碼為必填"}
    if len(username) < 4:
        return {"ok": False, "error": "帳號至少 4 個字元"}
    if len(password) < 6:
        return {"ok": False, "error": "密碼至少 6 個字元"}

    hashed, salt = _hash_password(password)
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO users (username, email, password_hash, password_salt, tenant_id, role, subscription)
               VALUES (%s, %s, %s, %s, %s, 'pending', 'pending')
               RETURNING id""",
            (username, email or None, hashed, salt, tenant_id),
        )
        uid = str(cur.fetchone()[0])
        conn.commit()
        return {"ok": True, "user_id": uid, "username": username}
    except Exception as e:
        conn.rollback()
        if "unique" in str(e).lower():
            return {"ok": False, "error": "此帳號或 Email 已被使用"}
        return {"ok": False, "error": str(e)}
    finally:
        cur.close()
        _put_conn(conn)


def login_user(username: str, password: str) -> dict:
    """登入驗證，成功回傳 JWT Token。"""
    username = (username or "").strip()
    password = (password or "").strip()
    if not username or not password:
        return {"ok": False, "error": "帳號和密碼為必填"}

    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, password_hash, password_salt, role, subscription, subscription_plan FROM users WHERE username = %s",
            (username,),
        )
        row = cur.fetchone()
        if not row:
            return {"ok": False, "error": "帳號不存在"}
        uid, stored_hash, salt, role, sub, plan = row
        if not _verify_password(password, stored_hash, salt):
            return {"ok": False, "error": "密碼錯誤"}
        # 更新最後登入時間
        cur.execute("UPDATE users SET last_login_at = NOW() WHERE id = %s", (uid,))
        conn.commit()
        # 產生 JWT
        from auth_manager import create_token
        token = create_token(str(uid), username, role, sub)
        return {
            "ok": True,
            "token": token,
            "user": {"id": str(uid), "username": username, "role": role, "subscription": sub, "subscription_plan": plan or ""},
        }
    finally:
        cur.close()
        _put_conn(conn)


def get_user_info(user_id: str) -> dict | None:
    """取得用戶資訊。"""
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT id, username, email, role, subscription, subscription_plan,
                      tenant_id, created_at, last_login_at
               FROM users WHERE id = %s::UUID""",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": str(row[0]), "username": row[1], "email": row[2],
            "role": row[3], "subscription": row[4], "subscription_plan": row[5] or "",
            "tenant_id": str(row[6]) if row[6] else None,
            "created_at": row[7].isoformat() if row[7] else None,
            "last_login_at": row[8].isoformat() if row[8] else None,
        }
    finally:
        cur.close()
        _put_conn(conn)


def activate_subscription(user_id: str, plan: str = "basic") -> dict:
    """啟用訂閱。"""
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """UPDATE users SET subscription = 'active', subscription_plan = %s,
                      role = CASE WHEN role = 'pending' THEN 'subscriber' ELSE role END,
                      subscription_expires_at = NOW() + INTERVAL '30 days',
                      updated_at = NOW()
               WHERE id = %s::UUID RETURNING id""",
            (plan, user_id),
        )
        if cur.fetchone() is None:
            conn.rollback()
            return {"ok": False, "error": "用戶不存在"}
        conn.commit()
        return {"ok": True, "user_id": user_id, "subscription": "active", "plan": plan}
    finally:
        cur.close()
        _put_conn(conn)


def list_users(requester_role: str = "") -> list[dict]:
    """列出所有用戶（僅 admin）。"""
    if requester_role not in ("superadmin", "admin"):
        return []
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT id, username, email, role, subscription, subscription_plan, tenant_id, created_at
               FROM users ORDER BY created_at DESC LIMIT 200"""
        )
        return [
            {"id": str(r[0]), "username": r[1], "email": r[2], "role": r[3],
             "subscription": r[4], "subscription_plan": r[5] or "",
             "tenant_id": str(r[6]) if r[6] else None,
             "created_at": r[7].isoformat() if r[7] else None}
            for r in cur.fetchall()
        ]
    finally:
        cur.close()
        _put_conn(conn)


# ── 租戶管理 ──

def create_tenant(name: str, slug: str, plan: str = "free") -> dict:
    """建立租戶。"""
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO tenants (name, slug, plan) VALUES (%s, %s, %s) RETURNING id",
            (name, slug, plan),
        )
        tid = str(cur.fetchone()[0])
        conn.commit()
        return {"ok": True, "tenant_id": tid, "name": name, "slug": slug}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        cur.close()
        _put_conn(conn)


def get_tenant(tenant_id: str) -> dict | None:
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, slug, plan, status, settings, created_at FROM tenants WHERE id = %s::UUID", (tenant_id,))
        r = cur.fetchone()
        if not r:
            return None
        return {"id": str(r[0]), "name": r[1], "slug": r[2], "plan": r[3], "status": r[4],
                "settings": r[5], "created_at": r[6].isoformat() if r[6] else None}
    finally:
        cur.close()
        _put_conn(conn)


def list_tenants() -> list[dict]:
    """列出所有租戶。"""
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, slug, plan, status, created_at FROM tenants ORDER BY created_at DESC")
        rows = cur.fetchall()
        return [
            {"id": str(r[0]), "name": r[1], "slug": r[2], "plan": r[3], "status": r[4],
             "created_at": r[5].isoformat() if r[5] else None}
            for r in rows
        ]
    finally:
        cur.close()
        _put_conn(conn)


def get_tenant_by_slug(slug: str) -> dict | None:
    """用 slug 查詢租戶。"""
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, slug, plan, status, settings, created_at FROM tenants WHERE slug = %s", (slug,))
        r = cur.fetchone()
        if not r:
            return None
        return {"id": str(r[0]), "name": r[1], "slug": r[2], "plan": r[3], "status": r[4],
                "settings": r[5], "created_at": r[6].isoformat() if r[6] else None}
    finally:
        cur.close()
        _put_conn(conn)


# ── 用量記錄（PG 版）──

def record_usage_pg(
    provider: str, model: str,
    input_tokens: int = 0, output_tokens: int = 0,
    duration_ms: int = 0, success: bool = True, error_msg: str = "",
    user_id: str = None, tenant_id: str = None, task_type: str = "chat",
    metadata: dict = None,
) -> bool:
    """記錄一筆用量到 PostgreSQL。"""
    from usage_metering import MODEL_COSTS
    now = time.time()
    date_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
    total_tokens = input_tokens + output_tokens
    cost_info = MODEL_COSTS.get(model, {"input": 0.0, "output": 0.0})
    cost = (input_tokens / 1000 * cost_info["input"]) + (output_tokens / 1000 * cost_info["output"])

    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO usage_records
               (ts, date, user_id, tenant_id, provider, model, task_type,
                input_tokens, output_tokens, total_tokens, duration_ms,
                estimated_cost_usd, success, error_msg, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (now, date_str,
             user_id if user_id and user_id != "anonymous" else None,
             tenant_id if tenant_id else None,
             provider, model, task_type,
             input_tokens, output_tokens, total_tokens, duration_ms,
             round(cost, 6), success, error_msg or None,
             json.dumps(metadata, ensure_ascii=False) if metadata else None),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        cur.close()
        _put_conn(conn)


# ── 資料遷移工具 ──

def migrate_users_from_json(json_path: str = None):
    """從 auth_manager 的 JSON 檔案遷移用戶到 PostgreSQL。"""
    if json_path is None:
        json_path = str(Path(__file__).resolve().parent / "brain_workspace" / "auth" / "users.json")
    p = Path(json_path)
    if not p.exists():
        print(f"⚠️ 用戶 JSON 不存在: {json_path}")
        return {"migrated": 0, "skipped": 0}

    users = json.loads(p.read_text(encoding="utf-8"))
    conn = _get_conn()
    cur = conn.cursor()
    migrated = 0
    skipped = 0
    for uid, u in users.items():
        try:
            cur.execute(
                """INSERT INTO users (id, username, email, password_hash, password_salt,
                          role, subscription, subscription_plan, created_at)
                   VALUES (%s::UUID, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (username) DO NOTHING""",
                (uid, u.get("username"), u.get("email") or None,
                 u.get("password_hash", ""), u.get("password_salt", ""),
                 u.get("role", "pending"), u.get("subscription", "pending"),
                 u.get("subscription_plan", ""),
                 u.get("created_at", datetime.now().isoformat())),
            )
            if cur.rowcount > 0:
                migrated += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ⚠️ 跳過 {u.get('username')}: {e}")
            conn.rollback()
            skipped += 1
            conn = _get_conn()
            cur = conn.cursor()
    conn.commit()
    cur.close()
    _put_conn(conn)
    print(f"✅ 用戶遷移完成: {migrated} 筆遷移, {skipped} 筆跳過")
    return {"migrated": migrated, "skipped": skipped}


# ── CLI ──

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "init"
    if cmd == "init":
        init_schema()
    elif cmd == "migrate":
        init_schema()
        migrate_users_from_json()
    elif cmd == "test":
        init_schema()
        print("Testing connection...")
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        print(f"  Users: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM tenants")
        print(f"  Tenants: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM subscription_plans")
        print(f"  Plans: {cur.fetchone()[0]}")
        cur.close()
        _put_conn(conn)
        print("✅ 連線測試通過")
    else:
        print(f"Usage: python db_postgres.py [init|migrate|test]")

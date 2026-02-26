"""
AI API 代理服務 — 對外提供本地 Ollama 模型 API，按 token 計費
主力收入源：比 OpenAI 便宜 50-80%，吸引小型開發者
"""

import asyncio
import json
import os
import time
import uuid
import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent / "brain_workspace" / "api_proxy_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "api_proxy.db"
KEYS_DIR = DATA_DIR / "keys"
KEYS_DIR.mkdir(exist_ok=True)

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# ── 定價（NT$/1K tokens）──
PRICING = {
    "qwen3:8b":          {"input": 0.02, "output": 0.06},
    "qwen3:4b":          {"input": 0.01, "output": 0.03},
    "gemma3:4b":          {"input": 0.01, "output": 0.03},
    "zhewei-brain":       {"input": 0.02, "output": 0.06},
    "nomic-embed-text":   {"input": 0.005, "output": 0.0},
    "_default":           {"input": 0.03, "output": 0.08},
}

# ── 方案 ──
PLANS = {
    "free":       {"name": "免費體驗", "monthly_tokens": 50_000,   "rate_limit": 10,  "price_ntd": 0},
    "starter":    {"name": "入門版",   "monthly_tokens": 500_000,  "rate_limit": 30,  "price_ntd": 299},
    "pro":        {"name": "專業版",   "monthly_tokens": 5_000_000, "rate_limit": 60,  "price_ntd": 999},
    "business":   {"name": "商務版",   "monthly_tokens": 50_000_000, "rate_limit": 120, "price_ntd": 4999},
    "unlimited":  {"name": "無限版",   "monthly_tokens": -1,       "rate_limit": 200, "price_ntd": 9999},
}


def _init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS api_keys (
        id TEXT PRIMARY KEY,
        key_hash TEXT UNIQUE NOT NULL,
        key_prefix TEXT NOT NULL,
        owner TEXT NOT NULL,
        email TEXT DEFAULT '',
        plan TEXT DEFAULT 'free',
        created_at TEXT NOT NULL,
        expires_at TEXT DEFAULT '',
        active INTEGER DEFAULT 1,
        monthly_tokens INTEGER DEFAULT 50000,
        rate_limit INTEGER DEFAULT 10,
        note TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS usage_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        model TEXT NOT NULL,
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        cost_ntd REAL DEFAULT 0,
        latency_ms INTEGER DEFAULT 0,
        endpoint TEXT DEFAULT '',
        status TEXT DEFAULT 'ok'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS monthly_usage (
        key_id TEXT NOT NULL,
        month TEXT NOT NULL,
        total_input_tokens INTEGER DEFAULT 0,
        total_output_tokens INTEGER DEFAULT 0,
        total_cost_ntd REAL DEFAULT 0,
        request_count INTEGER DEFAULT 0,
        PRIMARY KEY (key_id, month)
    )""")
    conn.commit()
    conn.close()

_init_db()


def _hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key(owner: str, email: str = "", plan: str = "free", 
                     expires_days: int = 365, note: str = "") -> dict:
    """生成新的 API Key"""
    plan_info = PLANS.get(plan, PLANS["free"])
    key_id = str(uuid.uuid4())[:8]
    raw_key = f"zw-{uuid.uuid4().hex}"
    key_hash = _hash_key(raw_key)
    key_prefix = raw_key[:10]
    
    created = datetime.now().isoformat()
    expires = (datetime.now() + timedelta(days=expires_days)).isoformat() if expires_days > 0 else ""
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""INSERT INTO api_keys 
        (id, key_hash, key_prefix, owner, email, plan, created_at, expires_at, active, monthly_tokens, rate_limit, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)""",
        (key_id, key_hash, key_prefix, owner, email, plan, created, expires,
         plan_info["monthly_tokens"], plan_info["rate_limit"], note))
    conn.commit()
    conn.close()
    
    return {
        "ok": True,
        "key_id": key_id,
        "api_key": raw_key,
        "key_prefix": key_prefix,
        "owner": owner,
        "plan": plan,
        "plan_name": plan_info["name"],
        "monthly_tokens": plan_info["monthly_tokens"],
        "rate_limit": plan_info["rate_limit"],
        "price_ntd": plan_info["price_ntd"],
        "created_at": created,
        "expires_at": expires,
        "message": "請妥善保管 API Key，遺失無法找回"
    }


def validate_api_key(api_key: str) -> dict:
    """驗證 API Key，回傳用戶資訊"""
    key_hash = _hash_key(api_key)
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT * FROM api_keys WHERE key_hash = ?", (key_hash,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return {"ok": False, "error": "無效的 API Key"}
    
    cols = ["id", "key_hash", "key_prefix", "owner", "email", "plan", 
            "created_at", "expires_at", "active", "monthly_tokens", "rate_limit", "note"]
    key_data = dict(zip(cols, row))
    
    if not key_data["active"]:
        return {"ok": False, "error": "API Key 已停用"}
    
    if key_data["expires_at"]:
        try:
            if datetime.fromisoformat(key_data["expires_at"]) < datetime.now():
                return {"ok": False, "error": "API Key 已過期"}
        except:
            pass
    
    return {"ok": True, **key_data}


def check_quota(key_id: str, monthly_tokens: int) -> dict:
    """檢查月配額"""
    if monthly_tokens == -1:
        return {"ok": True, "remaining": -1, "used": 0}
    
    month = datetime.now().strftime("%Y-%m")
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT total_input_tokens, total_output_tokens FROM monthly_usage WHERE key_id = ? AND month = ?",
              (key_id, month))
    row = c.fetchone()
    conn.close()
    
    used = (row[0] + row[1]) if row else 0
    remaining = monthly_tokens - used
    
    if remaining <= 0:
        return {"ok": False, "error": "月配額已用完", "used": used, "limit": monthly_tokens}
    
    return {"ok": True, "remaining": remaining, "used": used, "limit": monthly_tokens}


def record_usage(key_id: str, model: str, input_tokens: int, output_tokens: int,
                 latency_ms: int = 0, endpoint: str = "", status: str = "ok"):
    """記錄用量"""
    pricing = PRICING.get(model, PRICING["_default"])
    cost = (input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"]
    
    month = datetime.now().strftime("%Y-%m")
    timestamp = datetime.now().isoformat()
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    c.execute("""INSERT INTO usage_log (key_id, timestamp, model, input_tokens, output_tokens, cost_ntd, latency_ms, endpoint, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (key_id, timestamp, model, input_tokens, output_tokens, cost, latency_ms, endpoint, status))
    
    c.execute("""INSERT INTO monthly_usage (key_id, month, total_input_tokens, total_output_tokens, total_cost_ntd, request_count)
        VALUES (?, ?, ?, ?, ?, 1)
        ON CONFLICT(key_id, month) DO UPDATE SET
            total_input_tokens = total_input_tokens + ?,
            total_output_tokens = total_output_tokens + ?,
            total_cost_ntd = total_cost_ntd + ?,
            request_count = request_count + 1""",
        (key_id, month, input_tokens, output_tokens, cost,
         input_tokens, output_tokens, cost))
    
    conn.commit()
    conn.close()
    
    # Revenue Platform — 同步用量記錄
    try:
        from revenue_platform import get_platform as _get_rev
        total_tokens = input_tokens + output_tokens
        _get_rev().log_usage("llm_api", key_id, f"api_call:{model}", total_tokens)
        if cost > 0:
            rev_conn = sqlite3.connect(str(Path(__file__).resolve().parent / "brain_workspace" / "revenue_data" / "revenue.db"))
            rev_conn.execute(
                "INSERT INTO revenue_log (product, plan, amount, source, user_id, description) VALUES (?,?,?,?,?,?)",
                ("llm_api", "api_usage", cost, "api_call", key_id, f"{model} {input_tokens}+{output_tokens} tokens")
            )
            rev_conn.commit()
            rev_conn.close()
    except Exception:
        pass
    
    return cost


def get_usage_stats(key_id: str = "", days: int = 30) -> dict:
    """取得用量統計"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    if key_id:
        c.execute("""SELECT COUNT(*), SUM(input_tokens), SUM(output_tokens), SUM(cost_ntd)
            FROM usage_log WHERE key_id = ? AND timestamp > ?""", (key_id, cutoff))
    else:
        c.execute("""SELECT COUNT(*), SUM(input_tokens), SUM(output_tokens), SUM(cost_ntd)
            FROM usage_log WHERE timestamp > ?""", (cutoff,))
    
    row = c.fetchone()
    
    if key_id:
        c.execute("""SELECT model, COUNT(*), SUM(input_tokens + output_tokens), SUM(cost_ntd)
            FROM usage_log WHERE key_id = ? AND timestamp > ? GROUP BY model ORDER BY SUM(cost_ntd) DESC""",
            (key_id, cutoff))
    else:
        c.execute("""SELECT model, COUNT(*), SUM(input_tokens + output_tokens), SUM(cost_ntd)
            FROM usage_log WHERE timestamp > ? GROUP BY model ORDER BY SUM(cost_ntd) DESC""",
            (cutoff,))
    
    by_model = [{"model": r[0], "requests": r[1], "tokens": r[2], "cost_ntd": round(r[3], 2)} for r in c.fetchall()]
    
    conn.close()
    
    return {
        "period_days": days,
        "total_requests": row[0] or 0,
        "total_input_tokens": row[1] or 0,
        "total_output_tokens": row[2] or 0,
        "total_cost_ntd": round(row[3] or 0, 2),
        "by_model": by_model
    }


def get_revenue_summary() -> dict:
    """取得收入摘要"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    today = datetime.now().date().isoformat()
    month = datetime.now().strftime("%Y-%m")
    
    c.execute("SELECT SUM(cost_ntd) FROM usage_log WHERE timestamp >= ?", (today,))
    today_revenue = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(total_cost_ntd), SUM(request_count) FROM monthly_usage WHERE month = ?", (month,))
    row = c.fetchone()
    month_revenue = row[0] or 0
    month_requests = row[1] or 0
    
    c.execute("SELECT COUNT(*) FROM api_keys WHERE active = 1")
    active_keys = c.fetchone()[0]
    
    c.execute("SELECT plan, COUNT(*) FROM api_keys WHERE active = 1 GROUP BY plan")
    by_plan = {r[0]: r[1] for r in c.fetchall()}
    
    # 訂閱收入 = 各方案人數 × 月費
    subscription_revenue = sum(
        count * PLANS.get(plan, {}).get("price_ntd", 0)
        for plan, count in by_plan.items()
    )
    
    conn.close()
    
    return {
        "today_api_revenue": round(today_revenue, 2),
        "month_api_revenue": round(month_revenue, 2),
        "month_subscription_revenue": subscription_revenue,
        "month_total_revenue": round(month_revenue + subscription_revenue, 2),
        "month_requests": month_requests,
        "active_keys": active_keys,
        "by_plan": by_plan,
        "month": month
    }


def list_api_keys(active_only: bool = True) -> list:
    """列出所有 API Keys"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    if active_only:
        c.execute("SELECT id, key_prefix, owner, email, plan, created_at, expires_at, active, monthly_tokens, rate_limit, note FROM api_keys WHERE active = 1")
    else:
        c.execute("SELECT id, key_prefix, owner, email, plan, created_at, expires_at, active, monthly_tokens, rate_limit, note FROM api_keys")
    
    cols = ["id", "key_prefix", "owner", "email", "plan", "created_at", "expires_at", "active", "monthly_tokens", "rate_limit", "note"]
    keys = [dict(zip(cols, row)) for row in c.fetchall()]
    conn.close()
    return keys


def revoke_api_key(key_id: str) -> dict:
    """撤銷 API Key"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("UPDATE api_keys SET active = 0 WHERE id = ?", (key_id,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    
    if affected:
        return {"ok": True, "message": f"Key {key_id} 已撤銷"}
    return {"ok": False, "error": "Key 不存在"}


def update_key_plan(key_id: str, plan: str) -> dict:
    """升級/降級方案"""
    plan_info = PLANS.get(plan)
    if not plan_info:
        return {"ok": False, "error": "方案不存在"}
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("UPDATE api_keys SET plan = ?, monthly_tokens = ?, rate_limit = ? WHERE id = ?",
              (plan, plan_info["monthly_tokens"], plan_info["rate_limit"], key_id))
    affected = c.rowcount
    conn.commit()
    conn.close()
    
    if affected:
        return {"ok": True, "message": f"已升級到 {plan_info['name']}"}
    return {"ok": False, "error": "Key 不存在"}


def get_available_models() -> list:
    """取得可用模型列表（含定價）"""
    models = []
    for model, price in PRICING.items():
        if model == "_default":
            continue
        models.append({
            "model": model,
            "input_price_per_1k": price["input"],
            "output_price_per_1k": price["output"],
            "currency": "NTD"
        })
    return models


async def proxy_chat_completion(api_key: str, model: str, messages: list, 
                                 stream: bool = False, **kwargs) -> dict:
    """代理 Chat Completion 請求到本地 Ollama"""
    import aiohttp
    
    key_info = validate_api_key(api_key)
    if not key_info["ok"]:
        return key_info
    
    quota = check_quota(key_info["id"], key_info["monthly_tokens"])
    if not quota["ok"]:
        return quota
    
    start_time = time.time()
    
    try:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            **{k: v for k, v in kwargs.items() if k in ("temperature", "top_p", "max_tokens")}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_BASE}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return {"ok": False, "error": f"模型回應錯誤: {error_text[:200]}"}
                
                result = await resp.json()
        
        latency = int((time.time() - start_time) * 1000)
        
        input_tokens = result.get("prompt_eval_count", len(str(messages)) // 4)
        output_tokens = result.get("eval_count", len(result.get("message", {}).get("content", "")) // 4)
        
        cost = record_usage(
            key_id=key_info["id"],
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency,
            endpoint="/v1/chat/completions"
        )
        
        return {
            "ok": True,
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": result.get("message", {"role": "assistant", "content": ""}),
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            },
            "cost_ntd": round(cost, 4),
            "latency_ms": latency
        }
    except asyncio.TimeoutError:
        return {"ok": False, "error": "請求超時（120秒）"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


async def proxy_embeddings(api_key: str, model: str, input_text) -> dict:
    """代理 Embeddings 請求"""
    import aiohttp
    
    key_info = validate_api_key(api_key)
    if not key_info["ok"]:
        return key_info
    
    quota = check_quota(key_info["id"], key_info["monthly_tokens"])
    if not quota["ok"]:
        return quota
    
    start_time = time.time()
    
    if isinstance(input_text, str):
        input_text = [input_text]
    
    try:
        embeddings = []
        total_tokens = 0
        
        for text in input_text:
            payload = {"model": model or "nomic-embed-text", "input": text}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{OLLAMA_BASE}/api/embed",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status != 200:
                        return {"ok": False, "error": "Embedding 失敗"}
                    result = await resp.json()
            
            embedding = result.get("embeddings", [[]])[0]
            if not embedding:
                embedding = result.get("embedding", [])
            
            embeddings.append(embedding)
            total_tokens += len(text) // 4
        
        latency = int((time.time() - start_time) * 1000)
        
        cost = record_usage(
            key_id=key_info["id"],
            model=model or "nomic-embed-text",
            input_tokens=total_tokens,
            output_tokens=0,
            latency_ms=latency,
            endpoint="/v1/embeddings"
        )
        
        return {
            "ok": True,
            "object": "list",
            "data": [
                {"object": "embedding", "index": i, "embedding": emb}
                for i, emb in enumerate(embeddings)
            ],
            "model": model or "nomic-embed-text",
            "usage": {"prompt_tokens": total_tokens, "total_tokens": total_tokens},
            "cost_ntd": round(cost, 4),
            "latency_ms": latency
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}

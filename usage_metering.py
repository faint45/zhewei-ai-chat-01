# -*- coding: utf-8 -*-
"""
築未科技 — 用量計量系統（Usage Metering）

商用核心模組：記錄每次 AI 呼叫的用戶、模型、token 數、耗時、成本。
支援：
  - 即時記錄（append-only NDJSON 日誌 + SQLite 彙總）
  - 用量查詢（按用戶/日期/模型）
  - Quota 檢查（訂閱方案配額）
  - 成本估算（各模型單價）

未來遷移 PostgreSQL 時，只需替換 _db_* 函數即可。
"""
import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "brain_workspace" / "usage"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = DATA_DIR / "usage_log.ndjson"
DB_FILE = DATA_DIR / "usage.db"

# ── 模型成本估算（每 1K token，單位 USD）──
# Gemini Pro 訂閱已付費，邊際成本為 0；但記錄「等效成本」方便評估價值
MODEL_COSTS = {
    # Gemini（Pro 訂閱，實際免費，記錄等效市價）
    "gemini-2.5-flash":  {"input": 0.00015, "output": 0.0006},
    "gemini-2.5-pro":    {"input": 0.00125, "output": 0.005},
    "gemini-2.0-flash":  {"input": 0.0001,  "output": 0.0004},
    "gemini-1.5-flash":  {"input": 0.0001,  "output": 0.0004},
    # Claude（API 付費）
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "claude-3-5-sonnet":        {"input": 0.003, "output": 0.015},
    # Ollama 本地（免費，記錄電力等效成本）
    "qwen3:8b":           {"input": 0.0, "output": 0.0},
    "qwen3:4b":           {"input": 0.0, "output": 0.0},
    "gemma3:4b":          {"input": 0.0, "output": 0.0},
    "zhewei-brain:latest": {"input": 0.0, "output": 0.0},
}

# ── 訂閱方案配額（每月）──
PLAN_QUOTAS = {
    "free":      {"monthly_calls": 100,   "monthly_tokens": 50_000},
    "basic":     {"monthly_calls": 1000,  "monthly_tokens": 500_000},
    "pro":       {"monthly_calls": 5000,  "monthly_tokens": 2_000_000},
    "unlimited": {"monthly_calls": -1,    "monthly_tokens": -1},  # -1 = 無限
}

# ── SQLite 初始化 ──
_db_lock = threading.Lock()


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_FILE), timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    with _db_lock:
        conn = _get_db()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS usage_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                date TEXT NOT NULL,
                user_id TEXT NOT NULL DEFAULT 'anonymous',
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                task_type TEXT NOT NULL DEFAULT 'chat',
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                duration_ms INTEGER NOT NULL DEFAULT 0,
                estimated_cost_usd REAL NOT NULL DEFAULT 0.0,
                success INTEGER NOT NULL DEFAULT 1,
                error_msg TEXT,
                metadata TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_usage_user_date
                ON usage_records(user_id, date);
            CREATE INDEX IF NOT EXISTS idx_usage_date
                ON usage_records(date);
            CREATE INDEX IF NOT EXISTS idx_usage_provider
                ON usage_records(provider);

            CREATE TABLE IF NOT EXISTS usage_daily_summary (
                date TEXT NOT NULL,
                user_id TEXT NOT NULL DEFAULT 'anonymous',
                provider TEXT NOT NULL,
                total_calls INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                total_cost_usd REAL NOT NULL DEFAULT 0.0,
                success_count INTEGER NOT NULL DEFAULT 0,
                error_count INTEGER NOT NULL DEFAULT 0,
                avg_duration_ms REAL NOT NULL DEFAULT 0.0,
                PRIMARY KEY (date, user_id, provider)
            );
        """)
        conn.commit()
        conn.close()


_init_db()


# ── 核心：記錄一筆用量 ──

def record_usage(
    provider: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    duration_ms: int = 0,
    success: bool = True,
    error_msg: str = "",
    user_id: str = "anonymous",
    task_type: str = "chat",
    metadata: dict | None = None,
) -> dict:
    """
    記錄一筆 AI 用量。

    Returns: 記錄摘要 dict
    """
    now = time.time()
    date_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
    total_tokens = input_tokens + output_tokens

    # 成本估算
    cost_info = MODEL_COSTS.get(model, {"input": 0.0, "output": 0.0})
    estimated_cost = (input_tokens / 1000 * cost_info["input"]) + (output_tokens / 1000 * cost_info["output"])

    record = {
        "ts": now,
        "date": date_str,
        "user_id": user_id,
        "provider": provider,
        "model": model,
        "task_type": task_type,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "duration_ms": duration_ms,
        "estimated_cost_usd": round(estimated_cost, 6),
        "success": success,
        "error_msg": error_msg,
        "metadata": metadata,
    }

    # 1. Append to NDJSON log（快速、不會丟失）
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass

    # 2. Insert into SQLite
    try:
        with _db_lock:
            conn = _get_db()
            conn.execute(
                """INSERT INTO usage_records
                   (ts, date, user_id, provider, model, task_type,
                    input_tokens, output_tokens, total_tokens,
                    duration_ms, estimated_cost_usd, success, error_msg, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (now, date_str, user_id, provider, model, task_type,
                 input_tokens, output_tokens, total_tokens,
                 duration_ms, round(estimated_cost, 6),
                 1 if success else 0, error_msg or None,
                 json.dumps(metadata, ensure_ascii=False) if metadata else None),
            )
            # 更新每日彙總
            conn.execute(
                """INSERT INTO usage_daily_summary
                   (date, user_id, provider, total_calls, total_tokens, total_cost_usd,
                    success_count, error_count, avg_duration_ms)
                   VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)
                   ON CONFLICT(date, user_id, provider) DO UPDATE SET
                    total_calls = total_calls + 1,
                    total_tokens = total_tokens + excluded.total_tokens,
                    total_cost_usd = total_cost_usd + excluded.total_cost_usd,
                    success_count = success_count + excluded.success_count,
                    error_count = error_count + excluded.error_count,
                    avg_duration_ms = (avg_duration_ms * (total_calls - 1) + excluded.avg_duration_ms) / total_calls
                """,
                (date_str, user_id, provider, total_tokens, round(estimated_cost, 6),
                 1 if success else 0, 0 if success else 1, duration_ms),
            )
            conn.commit()
            conn.close()
    except Exception:
        pass

    return record


# ── Token 估算（簡易版：中文 ~1.5 token/字，英文 ~0.75 token/word）──

def estimate_tokens(text: str) -> int:
    """粗估 token 數。"""
    if not text:
        return 0
    # 混合語言估算
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 1.5 + other_chars * 0.3)


# ── 查詢 API ──

def get_user_usage(user_id: str, days: int = 30) -> dict:
    """查詢用戶近 N 天用量。"""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        with _db_lock:
            conn = _get_db()
            rows = conn.execute(
                """SELECT date, provider,
                          SUM(total_calls) as calls,
                          SUM(total_tokens) as tokens,
                          SUM(total_cost_usd) as cost,
                          SUM(success_count) as successes,
                          SUM(error_count) as errors,
                          AVG(avg_duration_ms) as avg_ms
                   FROM usage_daily_summary
                   WHERE user_id = ? AND date >= ?
                   GROUP BY date, provider
                   ORDER BY date DESC""",
                (user_id, since),
            ).fetchall()
            conn.close()
        return {
            "user_id": user_id,
            "days": days,
            "records": [dict(r) for r in rows],
            "totals": _aggregate_rows(rows),
        }
    except Exception as e:
        return {"user_id": user_id, "error": str(e)}


def get_system_usage(days: int = 30) -> dict:
    """查詢系統整體用量（管理員用）。"""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        with _db_lock:
            conn = _get_db()
            # 按日彙總
            daily = conn.execute(
                """SELECT date,
                          SUM(total_calls) as calls,
                          SUM(total_tokens) as tokens,
                          SUM(total_cost_usd) as cost
                   FROM usage_daily_summary
                   WHERE date >= ?
                   GROUP BY date
                   ORDER BY date DESC""",
                (since,),
            ).fetchall()
            # 按 provider 彙總
            by_provider = conn.execute(
                """SELECT provider,
                          SUM(total_calls) as calls,
                          SUM(total_tokens) as tokens,
                          SUM(total_cost_usd) as cost
                   FROM usage_daily_summary
                   WHERE date >= ?
                   GROUP BY provider""",
                (since,),
            ).fetchall()
            # 按用戶彙總（Top 20）
            by_user = conn.execute(
                """SELECT user_id,
                          SUM(total_calls) as calls,
                          SUM(total_tokens) as tokens,
                          SUM(total_cost_usd) as cost
                   FROM usage_daily_summary
                   WHERE date >= ?
                   GROUP BY user_id
                   ORDER BY calls DESC
                   LIMIT 20""",
                (since,),
            ).fetchall()
            conn.close()
        return {
            "days": days,
            "daily": [dict(r) for r in daily],
            "by_provider": [dict(r) for r in by_provider],
            "by_user": [dict(r) for r in by_user],
            "totals": _aggregate_daily(daily),
        }
    except Exception as e:
        return {"error": str(e)}


def check_quota(user_id: str, plan: str = "free") -> dict:
    """
    檢查用戶本月是否超過配額。

    Returns: {"allowed": bool, "usage": {...}, "quota": {...}, "remaining": {...}}
    """
    quota = PLAN_QUOTAS.get(plan, PLAN_QUOTAS["free"])
    if quota["monthly_calls"] == -1:
        return {"allowed": True, "plan": plan, "quota": "unlimited"}

    month_start = datetime.now().strftime("%Y-%m-01")
    try:
        with _db_lock:
            conn = _get_db()
            row = conn.execute(
                """SELECT COALESCE(SUM(total_calls), 0) as calls,
                          COALESCE(SUM(total_tokens), 0) as tokens
                   FROM usage_daily_summary
                   WHERE user_id = ? AND date >= ?""",
                (user_id, month_start),
            ).fetchone()
            conn.close()
        used_calls = row["calls"] if row else 0
        used_tokens = row["tokens"] if row else 0
        calls_ok = used_calls < quota["monthly_calls"]
        tokens_ok = quota["monthly_tokens"] == -1 or used_tokens < quota["monthly_tokens"]
        return {
            "allowed": calls_ok and tokens_ok,
            "plan": plan,
            "usage": {"calls": used_calls, "tokens": used_tokens},
            "quota": quota,
            "remaining": {
                "calls": max(0, quota["monthly_calls"] - used_calls),
                "tokens": max(0, quota["monthly_tokens"] - used_tokens) if quota["monthly_tokens"] != -1 else -1,
            },
        }
    except Exception as e:
        # 查詢失敗時放行（不因計量故障阻斷服務）
        return {"allowed": True, "plan": plan, "error": str(e)}


def get_today_summary() -> dict:
    """取得今日摘要（快速概覽）。"""
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with _db_lock:
            conn = _get_db()
            row = conn.execute(
                """SELECT COALESCE(SUM(total_calls), 0) as calls,
                          COALESCE(SUM(total_tokens), 0) as tokens,
                          COALESCE(SUM(total_cost_usd), 0) as cost,
                          COALESCE(SUM(success_count), 0) as successes,
                          COALESCE(SUM(error_count), 0) as errors
                   FROM usage_daily_summary
                   WHERE date = ?""",
                (today,),
            ).fetchone()
            conn.close()
        return {
            "date": today,
            "calls": row["calls"] if row else 0,
            "tokens": row["tokens"] if row else 0,
            "cost_usd": round(row["cost"], 4) if row else 0,
            "success_rate": round(row["successes"] / max(1, row["successes"] + row["errors"]) * 100, 1) if row else 0,
        }
    except Exception as e:
        return {"date": today, "error": str(e)}


# ── 內部工具 ──

def _aggregate_rows(rows) -> dict:
    total_calls = sum(r["calls"] for r in rows)
    total_tokens = sum(r["tokens"] for r in rows)
    total_cost = sum(r["cost"] for r in rows)
    return {"calls": total_calls, "tokens": total_tokens, "cost_usd": round(total_cost, 4)}


def _aggregate_daily(rows) -> dict:
    total_calls = sum(r["calls"] for r in rows)
    total_tokens = sum(r["tokens"] for r in rows)
    total_cost = sum(r["cost"] for r in rows)
    return {"calls": total_calls, "tokens": total_tokens, "cost_usd": round(total_cost, 4)}

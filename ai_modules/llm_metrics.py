# -*- coding: utf-8 -*-
"""
築未科技 — LLM Metrics + Budget 控制
借鑑 OpenHands Metrics 模式，追蹤每次 LLM 呼叫的 cost/latency/tokens

用法：
    from ai_modules.llm_metrics import llm_metrics

    # 記錄一次呼叫
    llm_metrics.record_call(
        model="qwen3:32b", provider="ollama",
        prompt_tokens=1200, completion_tokens=350,
        latency_ms=2800, cost_usd=0.0,
    )

    # 檢查預算
    if llm_metrics.is_over_budget():
        raise Exception("AI 預算超限")

    # 取得摘要
    summary = llm_metrics.get_summary()
"""
import json
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

log = logging.getLogger("ai_modules.llm_metrics")


@dataclass
class TokenUsage:
    """單次呼叫的 token 用量"""
    model: str = ""
    provider: str = ""                # ollama / gemini / claude / deepseek
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    total_tokens: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.prompt_tokens + self.completion_tokens


@dataclass
class CallCost:
    """單次呼叫的費用"""
    model: str
    provider: str
    cost_usd: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ResponseLatency:
    """單次呼叫的延遲"""
    model: str
    provider: str
    latency_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# 模型定價表（USD per 1M tokens）
MODEL_PRICING = {
    # Ollama 本地 — 免費
    "qwen3:32b": {"input": 0, "output": 0},
    "qwen3:8b": {"input": 0, "output": 0},
    "gemma3:4b": {"input": 0, "output": 0},
    "zhewei-brain": {"input": 0, "output": 0},
    "nomic-embed-text": {"input": 0, "output": 0},
    # Gemini
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    # Claude
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 1.00, "output": 5.00},
    # DeepSeek
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
}


class LLMMetrics:
    """
    LLM 用量追蹤 + 預算控制

    特性：
    1. 每次呼叫記錄 model/tokens/cost/latency
    2. 預算上限控制（日/月）
    3. SQLite 持久化
    4. 即時統計摘要
    5. 與 EventBus 整合
    """

    def __init__(self, db_path: str = ""):
        if not db_path:
            db_path = os.path.join(
                os.environ.get("BRAIN_DATA_DIR", "brain_workspace"),
                "usage", "llm_metrics.db",
            )
        self.db_path = db_path
        self._lock = threading.Lock()

        # 記憶體快取（當天）
        self._today_calls: List[dict] = []
        self._today_cost: float = 0.0
        self._today_tokens: int = 0

        # 預算（USD）
        self.daily_budget = float(os.environ.get("LLM_DAILY_BUDGET", "5.0"))
        self.monthly_budget = float(os.environ.get("LLM_MONTHLY_BUDGET", "50.0"))

        self._init_db()

    def _init_db(self):
        """建立資料庫表"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                model TEXT NOT NULL,
                provider TEXT DEFAULT '',
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                cache_read_tokens INTEGER DEFAULT 0,
                cache_write_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                latency_ms REAL DEFAULT 0,
                task_type TEXT DEFAULT '',
                success INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_calls_ts ON llm_calls(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_calls_model ON llm_calls(model)
        """)
        conn.commit()
        conn.close()

    def record_call(self, model: str, provider: str = "",
                    prompt_tokens: int = 0, completion_tokens: int = 0,
                    cache_read_tokens: int = 0, cache_write_tokens: int = 0,
                    latency_ms: float = 0, cost_usd: float = -1,
                    task_type: str = "", success: bool = True):
        """
        記錄一次 LLM 呼叫

        Args:
            model: 模型名稱
            provider: 提供者 (ollama/gemini/claude/deepseek)
            prompt_tokens: 輸入 token 數
            completion_tokens: 輸出 token 數
            cache_read_tokens: 快取讀取 token
            cache_write_tokens: 快取寫入 token
            latency_ms: 延遲（毫秒）
            cost_usd: 費用（-1 = 自動計算）
            task_type: 任務類型（think/execute/embed）
            success: 是否成功
        """
        total_tokens = prompt_tokens + completion_tokens
        now = datetime.now().isoformat()

        # 自動計算費用
        if cost_usd < 0:
            cost_usd = self._estimate_cost(model, prompt_tokens, completion_tokens)

        record = {
            "timestamp": now, "model": model, "provider": provider,
            "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_write_tokens": cache_write_tokens,
            "cost_usd": cost_usd, "latency_ms": latency_ms,
            "task_type": task_type, "success": 1 if success else 0,
        }

        # 寫入 DB
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute("""
                    INSERT INTO llm_calls
                    (timestamp, model, provider, prompt_tokens, completion_tokens,
                     total_tokens, cache_read_tokens, cache_write_tokens,
                     cost_usd, latency_ms, task_type, success)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    now, model, provider, prompt_tokens, completion_tokens,
                    total_tokens, cache_read_tokens, cache_write_tokens,
                    cost_usd, latency_ms, task_type, 1 if success else 0,
                ))
                conn.commit()
                conn.close()
            except Exception as e:
                log.error(f"LLM Metrics 寫入失敗: {e}")

            # 更新記憶體快取
            self._today_calls.append(record)
            self._today_cost += cost_usd
            self._today_tokens += total_tokens

        # 預算告警
        if self._today_cost > self.daily_budget * 0.8:
            log.warning(f"AI 日預算用量 {self._today_cost:.2f}/{self.daily_budget} USD (80%+)")
            self._emit_budget_warning()

    def is_over_budget(self, period: str = "daily") -> bool:
        """檢查是否超出預算"""
        if period == "daily":
            return self._today_cost >= self.daily_budget
        elif period == "monthly":
            monthly_cost = self._get_monthly_cost()
            return monthly_cost >= self.monthly_budget
        return False

    def get_remaining_budget(self, period: str = "daily") -> float:
        """取得剩餘預算（USD）"""
        if period == "daily":
            return max(0, self.daily_budget - self._today_cost)
        elif period == "monthly":
            return max(0, self.monthly_budget - self._get_monthly_cost())
        return 0

    def get_summary(self, hours: int = 24) -> dict:
        """取得用量摘要"""
        try:
            conn = sqlite3.connect(self.db_path)
            since = (datetime.now() - timedelta(hours=hours)).isoformat()

            # 總計
            row = conn.execute("""
                SELECT COUNT(*), COALESCE(SUM(total_tokens), 0),
                       COALESCE(SUM(cost_usd), 0), COALESCE(AVG(latency_ms), 0),
                       COALESCE(SUM(prompt_tokens), 0), COALESCE(SUM(completion_tokens), 0)
                FROM llm_calls WHERE timestamp >= ?
            """, (since,)).fetchone()

            # 按 model 分組
            model_rows = conn.execute("""
                SELECT model, provider, COUNT(*), SUM(total_tokens), SUM(cost_usd), AVG(latency_ms)
                FROM llm_calls WHERE timestamp >= ?
                GROUP BY model, provider ORDER BY SUM(total_tokens) DESC
            """, (since,)).fetchall()

            # 按 task_type 分組
            task_rows = conn.execute("""
                SELECT task_type, COUNT(*), SUM(total_tokens), SUM(cost_usd)
                FROM llm_calls WHERE timestamp >= ? AND task_type != ''
                GROUP BY task_type
            """, (since,)).fetchall()

            conn.close()

            return {
                "period_hours": hours,
                "total_calls": row[0],
                "total_tokens": row[1],
                "total_cost_usd": round(row[2], 4),
                "avg_latency_ms": round(row[3], 1),
                "prompt_tokens": row[4],
                "completion_tokens": row[5],
                "by_model": [
                    {
                        "model": r[0], "provider": r[1], "calls": r[2],
                        "tokens": r[3], "cost_usd": round(r[4], 4),
                        "avg_latency_ms": round(r[5], 1),
                    }
                    for r in model_rows
                ],
                "by_task": [
                    {"task_type": r[0], "calls": r[1], "tokens": r[2], "cost_usd": round(r[3], 4)}
                    for r in task_rows
                ],
                "budget": {
                    "daily_used": round(self._today_cost, 4),
                    "daily_limit": self.daily_budget,
                    "daily_remaining": round(self.get_remaining_budget("daily"), 4),
                    "monthly_used": round(self._get_monthly_cost(), 4),
                    "monthly_limit": self.monthly_budget,
                },
            }
        except Exception as e:
            log.error(f"LLM Metrics 查詢失敗: {e}")
            return {"error": str(e)}

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """估算費用"""
        pricing = MODEL_PRICING.get(model)
        if not pricing:
            # 嘗試部分匹配
            for key, val in MODEL_PRICING.items():
                if key in model or model in key:
                    pricing = val
                    break
        if not pricing:
            return 0.0
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def _get_monthly_cost(self) -> float:
        """取得本月費用"""
        try:
            conn = sqlite3.connect(self.db_path)
            first_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0).isoformat()
            row = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM llm_calls WHERE timestamp >= ?",
                (first_of_month,),
            ).fetchone()
            conn.close()
            return row[0]
        except Exception:
            return 0.0

    def _emit_budget_warning(self):
        """透過 EventBus 發送預算告警"""
        try:
            from core.event_bus import event_bus, EventTypes
            event_bus.publish(EventTypes.LLM_BUDGET_WARNING, {
                "daily_used": self._today_cost,
                "daily_limit": self.daily_budget,
                "pct": round(self._today_cost / self.daily_budget * 100, 1),
            }, source="llm_metrics")
        except ImportError:
            pass


# 全局單例
llm_metrics = LLMMetrics()

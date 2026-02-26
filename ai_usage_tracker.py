# -*- coding: utf-8 -*-
"""
築未科技 AI API 用量追蹤器
追蹤各 AI 提供者的 API 調用次數、tokens 消耗、成本估算
"""
import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional
from collections import defaultdict

USAGE_DIR = Path("brain_workspace/usage")
USAGE_DIR.mkdir(parents=True, exist_ok=True)

class AIUsageTracker:
    """AI API 用量追蹤器"""

    # 成本配置 (USD per 1M tokens)
    COSTS = {
        "deepseek": {"input": 0.55, "output": 2.19},
        "minimax": {"input": 0.15, "output": 1.20},
        "gemini": {"input": 0.075, "output": 0.30},
        "claude": {"input": 3.00, "output": 15.00},
        "groq": {"input": 0.00, "output": 0.00},  # 免費
        "ollama": {"input": 0.00, "output": 0.00},  # 本地免費
    }

    def __init__(self):
        self.db_path = USAGE_DIR / "usage.db"
        self.log_path = USAGE_DIR / "usage_log.ndjson"
        self._init_db()

    def _init_db(self):
        """初始化 SQLite 資料庫"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                provider TEXT,
                model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                cost REAL,
                user_id TEXT,
                task_type TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                provider TEXT,
                total_requests INTEGER,
                total_input_tokens INTEGER,
                total_output_tokens REAL,
                total_cost REAL
            )
        ''')
        conn.commit()
        conn.close()

    def log_request(self, provider: str, model: str, input_tokens: int,
                    output_tokens: int, user_id: str = "default", task_type: str = "chat"):
        """記錄 API 調用"""
        import sqlite3
        cost = self._calculate_cost(provider, input_tokens, output_tokens)
        timestamp = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO usage_log
            (timestamp, provider, model, input_tokens, output_tokens, cost, user_id, task_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, provider, model, input_tokens, output_tokens, cost, user_id, task_type))
        conn.commit()
        conn.close()

        # 寫入 NDJSON 日誌
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                "timestamp": timestamp,
                "provider": provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "user_id": user_id,
                "task_type": task_type
            }, ensure_ascii=False) + "\n")

    def _calculate_cost(self, provider: str, input_tokens: int, output_tokens: int) -> float:
        """計算成本 (USD)"""
        costs = self.COSTS.get(provider, {"input": 0, "output": 0})
        input_cost = (input_tokens / 1_000_000) * costs.get("input", 0)
        output_cost = (output_tokens / 1_000_000) * costs.get("output", 0)
        return round(input_cost + output_cost, 6)

    def get_today_stats(self) -> Dict:
        """取得今日統計"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        today = date.today().isoformat()

        cursor.execute('''
            SELECT provider,
                   COUNT(*) as requests,
                   SUM(input_tokens) as input_tokens,
                   SUM(output_tokens) as output_tokens,
                   SUM(cost) as cost
            FROM usage_log
            WHERE date(timestamp) = ?
            GROUP BY provider
        ''', (today,))

        rows = cursor.fetchall()
        conn.close()

        stats = {
            "date": today,
            "providers": {},
            "total_cost": 0,
            "total_requests": 0
        }

        for row in rows:
            provider, requests, input_tokens, output_tokens, cost = row
            stats["providers"][provider] = {
                "requests": requests or 0,
                "input_tokens": input_tokens or 0,
                "output_tokens": output_tokens or 0,
                "cost": cost or 0
            }
            stats["total_cost"] += cost or 0
            stats["total_requests"] += requests or 0

        return stats

    def get_weekly_stats(self) -> Dict:
        """取得本週統計"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT date(timestamp) as day, provider,
                   COUNT(*) as requests, SUM(cost) as cost
            FROM usage_log
            WHERE timestamp >= datetime('now', '-7 days')
            GROUP BY day, provider
            ORDER BY day
        ''')

        rows = cursor.fetchall()
        conn.close()

        weekly = {"days": {}, "providers": defaultdict(lambda: {"requests": 0, "cost": 0})}
        for row in rows:
            day, provider, requests, cost = row
            if day not in weekly["days"]:
                weekly["days"][day] = {"total": 0, "providers": {}}
            weekly["days"][day]["providers"][provider] = {"requests": requests, "cost": cost}
            weekly["days"][day]["total"] += cost or 0
            weekly["providers"][provider]["requests"] += requests
            weekly["providers"][provider]["cost"] += cost or 0

        return dict(weekly)

    def export_report(self) -> str:
        """匯出今日報告"""
        stats = self.get_today_stats()
        report = f"""
=== AI API 用量報告 - {stats['date']} ===

總請求數: {stats['total_requests']}
總成本: ${stats['total_cost']:.4f}

各提供者詳情:
"""
        for provider, data in stats["providers"].items():
            report += f"""
{provider}:
  - 請求次數: {data['requests']}
  - 輸入 tokens: {data['input_tokens']:,}
  - 輸出 tokens: {data['output_tokens']:,}
  - 成本: ${data['cost']:.4f}
"""
        return report


# 全域追蹤器實例
usage_tracker = AIUsageTracker()


def track_api_call(provider: str, model: str, input_tokens: int,
                   output_tokens: int, user_id: str = "default", task_type: str = "chat"):
    """便捷函數：追蹤 API 調用"""
    usage_tracker.log_request(provider, model, input_tokens, output_tokens, user_id, task_type)


if __name__ == "__main__":
    # 測試：顯示今日統計
    stats = usage_tracker.get_today_stats()
    print(usage_tracker.export_report())

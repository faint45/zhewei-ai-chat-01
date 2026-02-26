"""
築未科技 — 統一收入平台模組
整合三大收入線：
1. AI 創作平台 SaaS（成人模式 + 生圖/生影片）
2. 營建 AI 助手 SaaS（知識庫 + CMS）
3. 大模型 API 服務（70B 模型 + 本地推理）

硬體：i7-14700 20核 / 64GB RAM / RTX 4060 Ti 8GB / 15TB HDD
"""

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

DATA_DIR = Path(__file__).resolve().parent / "brain_workspace" / "revenue_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "revenue.db"

# ── 三大產品定義 ──

PRODUCTS = {
    "ai_creator": {
        "name": "AI 創作工作室",
        "icon": "🎨",
        "description": "無限 AI 生圖 · 圖片生影片 · 文字生影片 · 成人模式",
        "url": "/ai-studio",
        "plans": {
            "creator_free":  {"name": "免費體驗", "price": 0,    "monthly_images": 20,   "monthly_videos": 5,   "nsfw": False, "local_models": False},
            "creator_basic": {"name": "基礎版",   "price": 299,  "monthly_images": 200,  "monthly_videos": 30,  "nsfw": False, "local_models": False},
            "creator_pro":   {"name": "專業版",   "price": 799,  "monthly_images": -1,   "monthly_videos": 100, "nsfw": True,  "local_models": True},
            "creator_ultra": {"name": "無限版",   "price": 1999, "monthly_images": -1,   "monthly_videos": -1,  "nsfw": True,  "local_models": True},
        },
        "features": [
            "DALL·E 3 / GPT Image / Flux / SDXL / Imagen 4 / Ideogram 3 / Seedream 4",
            "Sora 2 圖片生影片 / 文字生影片",
            "本地 Forge + NoobAI-XL 無審查生圖",
            "本地 ComfyUI 自訂工作流",
            "作品庫 + 下載 + 歷史記錄",
        ],
    },
    "construction_ai": {
        "name": "營建 AI 助手",
        "icon": "🏗️",
        "description": "14,600+ 筆營建知識庫 · 9 種專業角色 · 施工日誌 · 自主檢查",
        "url": "/cms",
        "plans": {
            "cms_free":       {"name": "免費體驗", "price": 0,    "kb_entries": 100,   "roles": 1,  "voice": False, "vision": False},
            "cms_pro":        {"name": "專業版",   "price": 1500, "kb_entries": 50000, "roles": 15, "voice": True,  "vision": True},
            "cms_enterprise": {"name": "企業版",   "price": 8000, "kb_entries": -1,    "roles": -1, "voice": True,  "vision": True},
        },
        "features": [
            "14,600+ 筆台灣營建法規知識庫",
            "9 種專業角色（營建工程師、土木技師、結構技師...）",
            "施工日誌 + 自主檢查表 + 拍照記錄",
            "語音辨識自動填報（Whisper + AI 結構化）",
            "AI 視覺辨識（安全帽/反光背心偵測）",
            "施工前後比對 + OCR 文字辨識",
        ],
    },
    "llm_api": {
        "name": "大模型 API",
        "icon": "🧠",
        "description": "本地 70B 大模型推理 · OpenAI 相容 API · 比 GPT-4 便宜 80%",
        "url": "/v1",
        "plans": {
            "api_free":     {"name": "免費體驗", "price": 0,    "monthly_tokens": 50000,     "rate_limit": 10,  "models": ["qwen3:4b", "gemma3:4b"]},
            "api_starter":  {"name": "入門版",   "price": 299,  "monthly_tokens": 500000,    "rate_limit": 30,  "models": ["qwen3:8b", "qwen3:4b", "gemma3:4b"]},
            "api_pro":      {"name": "專業版",   "price": 999,  "monthly_tokens": 5000000,   "rate_limit": 60,  "models": "all"},
            "api_business": {"name": "商務版",   "price": 4999, "monthly_tokens": 50000000,  "rate_limit": 120, "models": "all"},
            "api_unlimited":{"name": "無限版",   "price": 9999, "monthly_tokens": -1,        "rate_limit": 200, "models": "all"},
        },
        "features": [
            "OpenAI 相容 API（/v1/chat/completions）",
            "本地 Qwen3 8B / 4B + Gemma3 4B",
            "64GB RAM 支援 70B 模型 CPU offload",
            "Embedding API（nomic-embed-text 768 維）",
            "比 GPT-4 便宜 80%，延遲更低",
        ],
    },
}

# ── 硬體規格 ──
HARDWARE = {
    "cpu": "Intel i7-14700 (20C/28T)",
    "ram": "64 GB DDR5",
    "gpu": "RTX 4060 Ti 8GB",
    "ssd": "Kingston 1TB NVMe",
    "hdd": "WD 4TB + Toshiba 1TB + Lenovo 10TB (15TB total)",
    "gpu_power_watts": 160,
    "idle_power_watts": 80,
    "electricity_rate": 4.0,
}


def _init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS subscriptions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        product TEXT NOT NULL,
        plan TEXT NOT NULL,
        price REAL NOT NULL,
        status TEXT DEFAULT 'active',
        started_at TEXT NOT NULL,
        expires_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS revenue_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT NOT NULL,
        plan TEXT NOT NULL,
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'NTD',
        source TEXT DEFAULT 'subscription',
        user_id TEXT,
        description TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS usage_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT NOT NULL,
        user_id TEXT,
        action TEXT NOT NULL,
        quantity INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

_init_db()


class RevenuePlatform:
    """統一收入平台"""

    def __init__(self):
        self.db_path = str(DB_PATH)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    # ── 訂閱管理 ──

    def create_subscription(self, user_id: str, product: str, plan: str) -> Dict:
        """建立訂閱"""
        if product not in PRODUCTS:
            return {"ok": False, "error": f"Unknown product: {product}"}
        plans = PRODUCTS[product]["plans"]
        if plan not in plans:
            return {"ok": False, "error": f"Unknown plan: {plan}"}

        plan_info = plans[plan]
        sub_id = f"sub_{int(time.time())}_{user_id[:8]}"
        now = datetime.now().isoformat()
        expires = (datetime.now() + timedelta(days=30)).isoformat()

        conn = self._conn()
        conn.execute(
            "INSERT INTO subscriptions (id, user_id, product, plan, price, started_at, expires_at) VALUES (?,?,?,?,?,?,?)",
            (sub_id, user_id, product, plan, plan_info["price"], now, expires)
        )
        if plan_info["price"] > 0:
            conn.execute(
                "INSERT INTO revenue_log (product, plan, amount, source, user_id, description) VALUES (?,?,?,?,?,?)",
                (product, plan, plan_info["price"], "subscription", user_id, f"New subscription: {plan}")
            )
        conn.commit()
        conn.close()
        return {"ok": True, "subscription_id": sub_id, "plan": plan, "price": plan_info["price"]}

    def get_active_subscriptions(self, product: Optional[str] = None) -> List[Dict]:
        """取得活躍訂閱"""
        conn = self._conn()
        if product:
            rows = conn.execute(
                "SELECT id, user_id, product, plan, price, started_at, expires_at FROM subscriptions WHERE status='active' AND product=?",
                (product,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, user_id, product, plan, price, started_at, expires_at FROM subscriptions WHERE status='active'"
            ).fetchall()
        conn.close()
        return [{"id": r[0], "user_id": r[1], "product": r[2], "plan": r[3], "price": r[4], "started_at": r[5], "expires_at": r[6]} for r in rows]

    # ── 收入統計 ──

    def get_revenue_summary(self, days: int = 30) -> Dict:
        """取得收入摘要"""
        conn = self._conn()
        since = (datetime.now() - timedelta(days=days)).isoformat()

        # 各產品收入
        product_rev = {}
        for product in PRODUCTS:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM revenue_log WHERE product=? AND created_at>=?",
                (product, since)
            ).fetchone()
            product_rev[product] = row[0] if row else 0

        # 各產品活躍訂閱數
        product_subs = {}
        for product in PRODUCTS:
            row = conn.execute(
                "SELECT COUNT(*) FROM subscriptions WHERE product=? AND status='active'",
                (product,)
            ).fetchone()
            product_subs[product] = row[0] if row else 0

        # 總收入
        total_row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM revenue_log WHERE created_at>=?",
            (since,)
        ).fetchone()
        total_revenue = total_row[0] if total_row else 0

        # 被動收入估算（GPU/頻寬/HDD）
        passive_monthly = self._estimate_passive_income()

        conn.close()

        # 月目標計算
        goal = 10000
        subscription_monthly = sum(product_rev.values())
        total_monthly = subscription_monthly + passive_monthly["total"]
        day_of_month = datetime.now().day
        days_in_month = 30
        projected = (total_monthly / max(day_of_month, 1)) * days_in_month if day_of_month > 0 else 0

        return {
            "ok": True,
            "period_days": days,
            "total_revenue": total_revenue,
            "subscription_revenue": subscription_monthly,
            "passive_revenue": passive_monthly,
            "by_product": {
                k: {
                    "name": PRODUCTS[k]["name"],
                    "icon": PRODUCTS[k]["icon"],
                    "revenue": product_rev.get(k, 0),
                    "active_subs": product_subs.get(k, 0),
                }
                for k in PRODUCTS
            },
            "goal": {
                "target": goal,
                "current": total_monthly,
                "projected": projected,
                "gap": max(goal - total_monthly, 0),
                "pct": min((total_monthly / goal) * 100, 100) if goal > 0 else 0,
            },
            "hardware": HARDWARE,
        }

    def _estimate_passive_income(self) -> Dict:
        """估算被動收入（GPU/頻寬/HDD）"""
        gpu_monthly = 1500   # IO.net/Salad 估算
        bandwidth_monthly = 400  # Grass + Honeygain
        hdd_monthly = 750    # 10TB × $1.5/TB/月 × 50% 利用率
        return {
            "gpu_rental": gpu_monthly,
            "bandwidth": bandwidth_monthly,
            "hdd_storage": hdd_monthly,
            "total": gpu_monthly + bandwidth_monthly + hdd_monthly,
        }

    # ── 用量追蹤 ──

    def log_usage(self, product: str, user_id: str, action: str, quantity: int = 1):
        """記錄用量"""
        conn = self._conn()
        conn.execute(
            "INSERT INTO usage_log (product, user_id, action, quantity) VALUES (?,?,?,?)",
            (product, user_id, action, quantity)
        )
        conn.commit()
        conn.close()

    def get_usage_stats(self, product: Optional[str] = None, days: int = 30) -> Dict:
        """取得用量統計"""
        conn = self._conn()
        since = (datetime.now() - timedelta(days=days)).isoformat()

        if product:
            rows = conn.execute(
                "SELECT action, SUM(quantity) FROM usage_log WHERE product=? AND created_at>=? GROUP BY action",
                (product, since)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT product, action, SUM(quantity) FROM usage_log WHERE created_at>=? GROUP BY product, action",
                (since,)
            ).fetchall()
        conn.close()

        if product:
            return {"ok": True, "product": product, "usage": {r[0]: r[1] for r in rows}}
        else:
            result = {}
            for r in rows:
                if r[0] not in result:
                    result[r[0]] = {}
                result[r[0]][r[1]] = r[2]
            return {"ok": True, "usage": result}

    # ── 產品資訊 ──

    def get_products(self) -> Dict:
        """取得所有產品資訊"""
        return {"ok": True, "products": PRODUCTS}

    def get_product_plans(self, product: str) -> Dict:
        """取得產品方案"""
        if product not in PRODUCTS:
            return {"ok": False, "error": f"Unknown product: {product}"}
        return {"ok": True, "product": product, "plans": PRODUCTS[product]["plans"]}

    # ── 達標路徑建議 ──

    def get_growth_suggestions(self) -> List[Dict]:
        """取得成長建議"""
        summary = self.get_revenue_summary()
        subs = self.get_active_subscriptions()
        suggestions = []

        # AI 創作平台
        creator_subs = len([s for s in subs if s["product"] == "ai_creator"])
        if creator_subs < 5:
            suggestions.append({
                "priority": "high",
                "icon": "🎨",
                "title": "推廣 AI 創作工作室",
                "description": f"目前 {creator_subs} 個訂閱。成人內容生成是剛需市場，在 Twitter/Reddit 推廣可快速獲客。",
                "potential": "10 個 Pro 用戶 = NT$7,990/月",
                "action": "在 AI 繪圖社群發布作品展示 + 免費試用連結",
            })

        # 營建 AI
        cms_subs = len([s for s in subs if s["product"] == "construction_ai"])
        if cms_subs < 3:
            suggestions.append({
                "priority": "high",
                "icon": "🏗️",
                "title": "開發營建客戶",
                "description": f"目前 {cms_subs} 個訂閱。台灣營建 AI 市場幾乎空白，你的 14,600 筆知識庫是護城河。",
                "potential": "2 Pro + 1 Enterprise = NT$11,000/月",
                "action": "聯繫認識的營建公司，提供 1 個月免費試用",
            })

        # 大模型 API
        api_subs = len([s for s in subs if s["product"] == "llm_api"])
        if api_subs < 3:
            suggestions.append({
                "priority": "medium",
                "icon": "🧠",
                "title": "推廣大模型 API",
                "description": f"目前 {api_subs} 個訂閱。64GB RAM 可跑 70B 模型，這是你的硬體優勢。",
                "potential": "3 Pro + 1 Business = NT$7,996/月",
                "action": "在 PTT/Dcard 技術版發文，強調比 OpenAI 便宜 80%",
            })

        # 被動收入
        suggestions.append({
            "priority": "medium",
            "icon": "💰",
            "title": "啟動被動收入",
            "description": "GPU 出租 + 頻寬出租 + HDD 儲存，零額外人力成本。",
            "potential": "NT$2,650/月（GPU $1,500 + 頻寬 $400 + HDD $750）",
            "action": "安裝 Grass.io + Honeygain + 設定 Storj 10TB 節點",
        })

        # 70B 模型
        suggestions.append({
            "priority": "low",
            "icon": "🚀",
            "title": "下載 70B 模型提升競爭力",
            "description": "64GB RAM 可跑 Qwen3 70B（CPU offload, 4-6 tok/s）。大部分競爭者只有 16-32GB 跑不了。",
            "potential": "差異化定價，70B 模型 API 可收更高費用",
            "action": "ollama pull qwen3:70b（約 40GB，需數小時下載）",
        })

        return suggestions


# 全域單例
_platform = None

def get_platform() -> RevenuePlatform:
    global _platform
    if _platform is None:
        _platform = RevenuePlatform()
    return _platform

"""
築未科技大腦 - AI 使用成本追蹤
估算各提供者的 token 消耗與費用（USD），支援每月預算上限（新台幣）
"""
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

# 各提供者定價：每百萬 tokens (input, output) USD，免費則 0
# 參考：DeepSeek ~$0.14/$0.28, Gemini 免費額度外 ~$0.075/$0.30, 千尋 約 $0.5/$0.5
PRICING = {
    "Ollama": (0, 0),
    "Groq": (0, 0),
    "Gemini": (0, 0),           # 免費額度
    "OpenRouter": (0, 0),       # free 模型
    "Grok": (2.0, 10.0),        # xAI 按量計費
    "Mistral": (0, 0),          # 免費額度
    "DeepSeek": (0.14, 0.28),   # 每百萬 token
    "千尋": (0.5, 0.5),
    "無": (0, 0),
    "api": (0, 0),              # API 呼叫（由 Brain Bridge 記錄，僅計次/依 actor 統計）
}

# 每月預算上限（新台幣）；超過後僅使用免費提供者
BUDGET_TWD = float(os.environ.get("AI_BUDGET_TWD", "1000"))
USD_TO_TWD = float(os.environ.get("USD_TO_TWD", "32"))

from brain_data_config import COST_FILE
_lock = threading.Lock()


def _estimate_tokens(text: str) -> int:
    """粗略估算 token 數：中文 ~1.5 字/token，英文 ~4 字/token"""
    if not text:
        return 0
    # 簡化：約 3 字符/token
    return max(1, len(text) // 3)


def _this_month() -> str:
    return datetime.now().strftime("%Y-%m")


def _load() -> dict:
    if not COST_FILE.exists():
        return {"total_usd": 0, "by_provider": {}, "calls": 0, "monthly_usd": {}, "monthly_by_actor": {}}
    try:
        with open(COST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "monthly_usd" not in data:
            data["monthly_usd"] = {}
        if "monthly_by_actor" not in data:
            data["monthly_by_actor"] = {}
        return data
    except Exception:
        return {"total_usd": 0, "by_provider": {}, "calls": 0, "monthly_usd": {}, "monthly_by_actor": {}}


def _save(data: dict):
    try:
        with open(COST_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _record_impl(prompt: str, response: str, provider: str, actor_id: Optional[str] = None) -> float:
    """實際寫入一筆費用（USD）並更新當月累計；若 actor_id 有值則同時更新依用戶用量（供訂閱制）。"""
    inp_tok = _estimate_tokens(prompt)
    out_tok = _estimate_tokens(response)
    price_in, price_out = PRICING.get(provider, (0, 0))
    cost = (inp_tok / 1_000_000 * price_in) + (out_tok / 1_000_000 * price_out)

    with _lock:
        data = _load()
        data["total_usd"] = data.get("total_usd", 0) + cost
        data["calls"] = data.get("calls", 0) + 1
        monthly = data.get("monthly_usd", {})
        m = _this_month()
        monthly[m] = monthly.get(m, 0) + cost
        data["monthly_usd"] = monthly
        if actor_id and str(actor_id).strip():
            aid = str(actor_id).strip()[:200]
            by_actor = data.get("monthly_by_actor", {})
            if m not in by_actor:
                by_actor[m] = {}
            by_actor[m][aid] = by_actor[m].get(aid, 0) + cost
            data["monthly_by_actor"] = by_actor
        by_prov = data.get("by_provider", {})
        p = by_prov.get(provider, {"usd": 0, "calls": 0})
        p["usd"] = p.get("usd", 0) + cost
        p["calls"] = p.get("calls", 0) + 1
        by_prov[provider] = p
        data["by_provider"] = by_prov
        _save(data)

    return cost


def record(prompt: str, response: str = None, provider: str = None, actor_id: Optional[str] = None) -> float:
    """
    記錄一次 AI 呼叫，回傳本次估算費用 (USD)。
    支援兩種呼叫：record(prompt, response, provider) 或 record(provider, prompt_len)。
    同時更新當月累計（monthly_usd），供預算檢查用。
    """
    if provider is None and isinstance(response, (int, float)) and isinstance(prompt, str):
        # 舊介面：record(provider, prompt_len) 或 record(provider, prompt_len, actor_id=...)
        prov, plen = prompt, int(response)
        fake_prompt = "x" * min(plen, 50000)
        fake_response = "x" * min(plen * 2, 100000)
        return _record_impl(fake_prompt, fake_response, prov, actor_id=actor_id)
    return _record_impl(prompt, response or "", provider or "無", actor_id=actor_id)


def get_total() -> float:
    """回傳累計花費 (USD)"""
    with _lock:
        return _load().get("total_usd", 0)


def get_month_total_usd(actor_id: Optional[str] = None) -> float:
    """回傳當月累計花費 (USD)；若 actor_id 有值則回傳該用戶/Key 當月用量"""
    with _lock:
        data = _load()
        m = _this_month()
        if actor_id and str(actor_id).strip():
            by_actor = data.get("monthly_by_actor", {}).get(m, {})
            return by_actor.get(str(actor_id).strip()[:200], 0)
        return data.get("monthly_usd", {}).get(m, 0)


def get_month_total_twd(actor_id: Optional[str] = None) -> float:
    """回傳當月累計花費 (新台幣)；若 actor_id 有值則回傳該用戶/Key 當月用量"""
    return get_month_total_usd(actor_id) * USD_TO_TWD


def is_budget_exceeded() -> bool:
    """當月花費（新台幣）是否已達或超過預算上限"""
    return get_month_total_twd() >= BUDGET_TWD


def get_summary() -> dict:
    """回傳完整摘要：total_usd, monthly_usd, by_provider, calls"""
    with _lock:
        return _load()


def format_cost(usd: float) -> str:
    """格式化金額顯示 (USD)"""
    if usd < 0.0001:
        return "$0.00"
    if usd < 0.01:
        return f"${usd:.4f}"
    return f"${usd:.2f}"


def format_cost_twd(twd: float) -> str:
    """格式化金額顯示 (新台幣)"""
    if twd < 0.01:
        return "NT$0"
    return f"NT${twd:,.0f}"

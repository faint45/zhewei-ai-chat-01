# -*- coding: utf-8 -*-
"""
築未科技 — 智能管家（Task Butler）
接續全通訊訊息：讀取 → 分類 → 建議 → 低風險自動執行、高風險送確認。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

POLICY_FILE = ROOT / "configs" / "task_butler_risk_policy.json"
BUTLER_RESULT_DIR = ROOT / "reports" / "task_butler"
PENDING_CONFIRM_FILE = ROOT / "reports" / "task_butler_pending_confirm.json"


def _load_policy() -> dict[str, Any]:
    if not POLICY_FILE.exists():
        return {
            "default_policy": "auto_safe_escalate",
            "risk_levels": {},
            "keyword_hints": {"high": [], "critical": []},
        }
    try:
        return json.loads(POLICY_FILE.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {"risk_levels": {}, "keyword_hints": {"high": [], "critical": []}}


def classify_risk(text: str, policy: dict[str, Any]) -> str:
    """依關鍵字與政策將訊息分級：low | normal | high | critical。"""
    t = (text or "").strip().lower()
    hints = policy.get("keyword_hints", {})
    for level in ("critical", "high"):
        for kw in hints.get(level, []):
            if kw.lower() in t:
                return level
    if any(k in t for k in ("緊急", "urgent", "asap", "立刻")):
        return "high"
    return "normal"


def fetch_all_inbox(limit_per_channel: int = 20) -> list[dict[str, Any]]:
    """從各適配器拉取近期訊息，回傳統一格式 dict 列表。含 Phase A（Email/Discord/Telegram）與 Phase B 佔位（WeChat/IG/FB/Threads）。"""
    try:
        from brain_modules.message_adapters import (
            DiscordAdapter,
            EmailAdapter,
            TelegramAdapter,
            WeChatAdapter,
            SocialAdapter,
        )
    except Exception:
        return []

    adapters = [
        DiscordAdapter(),
        EmailAdapter(),
        TelegramAdapter(),
        WeChatAdapter(),
        SocialAdapter("ig"),
        SocialAdapter("facebook"),
        SocialAdapter("threads"),
    ]
    out: list[dict[str, Any]] = []
    for adapter in adapters:
        try:
            msgs = adapter.fetch_recent(limit=limit_per_channel)
            for m in msgs:
                out.append(m.to_dict() if hasattr(m, "to_dict") else m)
        except Exception:
            continue
    # 依 timestamp 排序（新到舊）
    out.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return out[: limit_per_channel * 5]


def run_one_round(
    limit_per_channel: int = 20,
    enqueue_auto_tasks: bool = True,
    brain_api_base: str = "http://127.0.0.1:8002",
) -> dict[str, Any]:
    """
    執行一輪管家流程：收件 → 分類 → 建議 → 依風險決定自動派工或寫入待確認。
    enqueue_auto_tasks=True 時會對低/一般風險呼叫 brain_server 建立任務；
    高/關鍵風險寫入 task_butler_pending_confirm.json 供人工確認後再派工。
    """
    BUTLER_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    policy = _load_policy()

    inbox = fetch_all_inbox(limit_per_channel=limit_per_channel)
    classified: list[dict[str, Any]] = []
    auto_tasks_created: list[str] = []
    pending_confirm: list[dict[str, Any]] = []

    for item in inbox:
        text = item.get("text", "")
        risk = classify_risk(text, policy)
        item["risk"] = risk
        item["auto_execute"] = policy.get("risk_levels", {}).get(risk, {}).get("auto_execute", risk == "low" or risk == "normal")
        classified.append(item)

        if item.get("auto_execute") and enqueue_auto_tasks:
            # 可在此呼叫 brain_server 建立 semantic-route 或 smart-gui 任務
            task_id = _enqueue_butler_task(brain_api_base, item)
            if task_id:
                auto_tasks_created.append(task_id)
        else:
            pending_confirm.append({
                "channel": item.get("channel"),
                "sender": item.get("sender"),
                "text": text[:500],
                "risk": risk,
                "message_id": item.get("message_id"),
                "suggested_action": "請確認後再派工",
            })

    if pending_confirm:
        PENDING_CONFIRM_FILE.parent.mkdir(parents=True, exist_ok=True)
        PENDING_CONFIRM_FILE.write_text(
            json.dumps({"pending": pending_confirm, "updated": _now_iso()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    result = {
        "ok": True,
        "inbox_count": len(inbox),
        "classified": classified,
        "auto_tasks_created": auto_tasks_created,
        "pending_confirm_count": len(pending_confirm),
        "pending_confirm_file": str(PENDING_CONFIRM_FILE),
    }
    return result


def _now_iso() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _enqueue_butler_task(base_url: str, item: dict[str, Any]) -> str | None:
    """依訊息內容向 brain_server 建立一筆後續任務（語義路由或 smart-gui）。"""
    import urllib.request
    import urllib.error

    text = (item.get("text") or "").strip()[:500]
    channel = item.get("channel", "")
    sender = item.get("sender", "")
    if not text:
        return None
    # 組一句自然語給語義路由
    prompt = f"[{channel}] {sender}：{text}。請整理摘要並建議是否需回覆或派工。"
    url = f"{base_url.rstrip('/')}/api/agent/tasks/semantic-route"
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps({"text": prompt, "auto_run": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        tasks = data.get("tasks", [])
        if tasks:
            return tasks[0].get("id")
    except Exception:
        pass
    return None


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Task Butler one-shot run")
    p.add_argument("--limit", type=int, default=20, help="per-channel message limit")
    p.add_argument("--no-enqueue", action="store_true", help="do not enqueue auto tasks")
    p.add_argument("--base", default="http://127.0.0.1:8002", help="brain_server base URL")
    args = p.parse_args()
    r = run_one_round(
        limit_per_channel=args.limit,
        enqueue_auto_tasks=not args.no_enqueue,
        brain_api_base=args.base,
    )
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

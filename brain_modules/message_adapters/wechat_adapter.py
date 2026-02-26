# -*- coding: utf-8 -*-
"""
Phase B：WeChat 適配器（佔位）。
官方 API 或 GUI 自動化代理寫入 reports/wechat_inbox_cache.json 後，由此讀取並轉成 UnifiedMessage。
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .base import BaseMessageAdapter

if TYPE_CHECKING:
    from brain_modules.unified_messages import UnifiedMessage

ROOT = Path(__file__).resolve().parent.parent.parent
CACHE = ROOT / "reports" / "wechat_inbox_cache.json"


class WeChatAdapter(BaseMessageAdapter):
    channel_name = "wechat"

    def fetch_recent(self, limit: int = 20, since_ts: str | None = None) -> list["UnifiedMessage"]:
        from brain_modules.unified_messages import UnifiedMessage

        out: list[UnifiedMessage] = []
        if not CACHE.exists():
            return out
        try:
            import json
            raw = json.loads(CACHE.read_text(encoding="utf-8", errors="ignore"))
            items = raw.get("messages", []) if isinstance(raw, dict) else []
            for item in items[:limit]:
                if not isinstance(item, dict):
                    continue
                out.append(UnifiedMessage(
                    channel="wechat",
                    sender=str(item.get("sender", item.get("from", ""))),
                    sender_id=str(item.get("sender_id", item.get("from_id", ""))),
                    text=str(item.get("text", item.get("content", ""))),
                    thread_id=str(item.get("thread_id", item.get("chat_id", ""))),
                    message_id=str(item.get("message_id", item.get("id", ""))),
                    timestamp=str(item.get("timestamp", item.get("date", ""))),
                    priority=str(item.get("priority", "normal")),
                    attachments=list(item.get("attachments", [])),
                    raw_meta=dict(item.get("raw_meta", item)),
                ))
        except Exception:
            pass
        return out

    def health_check(self) -> tuple[bool, str]:
        return CACHE.exists(), "wechat adapter (cache)" if CACHE.exists() else "wechat adapter (no cache)"

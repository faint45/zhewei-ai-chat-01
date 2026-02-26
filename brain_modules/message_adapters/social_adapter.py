# -*- coding: utf-8 -*-
"""
Phase B：IG / 臉書 / Threads 適配器（佔位）。
Meta API 或代理寫入對應快取後，由此讀取並轉成 UnifiedMessage。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from .base import BaseMessageAdapter

if TYPE_CHECKING:
    from brain_modules.unified_messages import UnifiedMessage

ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_MAP = {
    "ig": ROOT / "reports" / "ig_inbox_cache.json",
    "facebook": ROOT / "reports" / "facebook_inbox_cache.json",
    "threads": ROOT / "reports" / "threads_inbox_cache.json",
}


class SocialAdapter(BaseMessageAdapter):
    """單一適配器可讀 ig / facebook / threads 任一路徑（channel 由檔名決定）。"""
    channel_name = "social"

    def __init__(self, channel: str = "ig"):
        self._channel = channel
        self._cache = CACHE_MAP.get(channel, CACHE_MAP["ig"])

    def fetch_recent(self, limit: int = 20, since_ts: str | None = None) -> list["UnifiedMessage"]:
        from brain_modules.unified_messages import UnifiedMessage

        out: list[UnifiedMessage] = []
        if not self._cache.exists():
            return out
        try:
            raw = json.loads(self._cache.read_text(encoding="utf-8", errors="ignore"))
            items = raw.get("messages", raw.get("comments", [])) if isinstance(raw, dict) else []
            for item in items[:limit]:
                if not isinstance(item, dict):
                    continue
                out.append(UnifiedMessage(
                    channel=self._channel,
                    sender=str(item.get("from", item.get("sender", ""))),
                    sender_id=str(item.get("from_id", item.get("sender_id", ""))),
                    text=str(item.get("text", item.get("content", item.get("message", "")))),
                    thread_id=str(item.get("thread_id", item.get("post_id", ""))),
                    message_id=str(item.get("message_id", item.get("id", ""))),
                    timestamp=str(item.get("timestamp", item.get("created_time", ""))),
                    priority=str(item.get("priority", "normal")),
                    attachments=list(item.get("attachments", [])),
                    raw_meta=dict(item.get("raw_meta", item)),
                ))
        except Exception:
            pass
        return out

    def health_check(self) -> tuple[bool, str]:
        return self._cache.exists(), f"{self._channel} adapter (cache)" if self._cache.exists() else f"{self._channel} adapter (no cache)"

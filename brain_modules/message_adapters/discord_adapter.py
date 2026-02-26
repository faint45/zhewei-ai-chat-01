# -*- coding: utf-8 -*-
"""
Discord 適配器：透過 brain_server / Jarvis Discord Bot 或 API 取得近期訊息。
若無即時 API，可讀取本地快取或透過 bot 輪詢結果檔。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brain_modules.unified_messages import UnifiedMessage

from .base import BaseMessageAdapter

ROOT = Path(__file__).resolve().parent.parent.parent
DISCORD_CACHE = ROOT / "reports" / "discord_inbox_cache.json"


class DiscordAdapter(BaseMessageAdapter):
    """Discord 訊息適配：優先讀取 brain 回寫的快取；無則回傳空列表。"""

    channel_name = "discord"

    def fetch_recent(self, limit: int = 20, since_ts: str | None = None) -> list["UnifiedMessage"]:
        from brain_modules.unified_messages import UnifiedMessage

        out: list[UnifiedMessage] = []
        if not DISCORD_CACHE.exists():
            return out
        try:
            raw = json.loads(DISCORD_CACHE.read_text(encoding="utf-8", errors="ignore"))
            items = raw.get("messages", []) if isinstance(raw, dict) else []
            for item in items[:limit]:
                if not isinstance(item, dict):
                    continue
                msg = UnifiedMessage(
                    channel="discord",
                    sender=str(item.get("author", item.get("sender", ""))),
                    sender_id=str(item.get("author_id", item.get("sender_id", ""))),
                    text=str(item.get("content", item.get("text", ""))),
                    thread_id=str(item.get("channel_id", item.get("thread_id", ""))),
                    message_id=str(item.get("id", item.get("message_id", ""))),
                    timestamp=str(item.get("timestamp", item.get("created_at", ""))),
                    priority=str(item.get("priority", "normal")),
                    attachments=list(item.get("attachments", [])),
                    raw_meta=dict(item.get("raw_meta", item)),
                )
                out.append(msg)
        except Exception:
            pass
        return out

    def health_check(self) -> tuple[bool, str]:
        return True, "discord adapter (cache)"

# -*- coding: utf-8 -*-
"""
Telegram 適配器：Bot API 或快取讀取近期訊息，轉成 UnifiedMessage。
未設定 token 時讀取本地快取；無則空。
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brain_modules.unified_messages import UnifiedMessage

from .base import BaseMessageAdapter

ROOT = Path(__file__).resolve().parent.parent.parent
TELEGRAM_CACHE = ROOT / "reports" / "telegram_inbox_cache.json"


class TelegramAdapter(BaseMessageAdapter):
    """Telegram 訊息適配：優先讀取回寫的快取；無則回傳空列表。"""

    channel_name = "telegram"

    def fetch_recent(self, limit: int = 20, since_ts: str | None = None) -> list["UnifiedMessage"]:
        from brain_modules.unified_messages import UnifiedMessage

        out: list[UnifiedMessage] = []
        if not TELEGRAM_CACHE.exists():
            return out
        try:
            import json
            raw = json.loads(TELEGRAM_CACHE.read_text(encoding="utf-8", errors="ignore"))
            items = raw.get("messages", []) if isinstance(raw, dict) else []
            for item in items[:limit]:
                if not isinstance(item, dict):
                    continue
                msg = UnifiedMessage(
                    channel="telegram",
                    sender=str(item.get("from", item.get("sender", ""))),
                    sender_id=str(item.get("from_id", item.get("sender_id", ""))),
                    text=str(item.get("text", item.get("content", ""))),
                    thread_id=str(item.get("chat_id", item.get("thread_id", ""))),
                    message_id=str(item.get("message_id", item.get("id", ""))),
                    timestamp=str(item.get("date", item.get("timestamp", ""))),
                    priority=str(item.get("priority", "normal")),
                    attachments=list(item.get("attachments", [])),
                    raw_meta=dict(item.get("raw_meta", item)),
                )
                out.append(msg)
        except Exception:
            pass
        return out

    def health_check(self) -> tuple[bool, str]:
        return True, "telegram adapter (cache)"

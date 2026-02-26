# -*- coding: utf-8 -*-
"""
Email 適配器：Gmail/Outlook API 或 IMAP 讀取近期郵件，轉成 UnifiedMessage。
未設定認證時僅回傳空列表並標記不可用。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brain_modules.unified_messages import UnifiedMessage

from .base import BaseMessageAdapter

ROOT = Path(__file__).resolve().parent.parent.parent
EMAIL_CACHE = ROOT / "reports" / "email_inbox_cache.json"


class EmailAdapter(BaseMessageAdapter):
    """Email 訊息適配：優先讀取 brain 回寫的快取（由排程或 webhook 寫入）；無則空。"""

    channel_name = "email"

    def fetch_recent(self, limit: int = 20, since_ts: str | None = None) -> list["UnifiedMessage"]:
        from brain_modules.unified_messages import UnifiedMessage

        out: list[UnifiedMessage] = []
        if not EMAIL_CACHE.exists():
            return out
        try:
            import json
            raw = json.loads(EMAIL_CACHE.read_text(encoding="utf-8", errors="ignore"))
            items = raw.get("messages", raw.get("emails", [])) if isinstance(raw, dict) else []
            for item in items[:limit]:
                if not isinstance(item, dict):
                    continue
                msg = UnifiedMessage(
                    channel="email",
                    sender=str(item.get("from", item.get("sender", ""))),
                    sender_id=str(item.get("from_id", item.get("sender_id", ""))),
                    text=str(item.get("body", item.get("text", item.get("snippet", "")))),
                    thread_id=str(item.get("thread_id", item.get("conversation_id", ""))),
                    message_id=str(item.get("id", item.get("message_id", ""))),
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
        return True, "email adapter (cache)"

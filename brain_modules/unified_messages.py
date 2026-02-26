# -*- coding: utf-8 -*-
"""
築未科技 — 全通訊統一訊息格式
所有通道（Email、Discord、Telegram、WeChat、IG 等）適配後皆輸出此格式，
供 Task Butler 分類、建議、執行。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 統一欄位：sender, channel, text, attachments, thread_id, timestamp, priority, raw_meta
@dataclass
class UnifiedMessage:
    """單一訊息統一格式。"""
    channel: str          # email | discord | telegram | wechat | ig | facebook | threads
    sender: str           # 顯示名稱或 ID
    sender_id: str        # 平台原生 ID（可選）
    text: str             # 正文
    thread_id: str        # 對話/串 ID
    message_id: str       # 平台原生訊息 ID
    timestamp: str        # ISO 或可排序字串
    priority: str         # low | normal | high | urgent（適配層可設，Butler 可覆寫）
    attachments: list[dict[str, Any]] = field(default_factory=list)  # [{ "type", "url", "name" }]
    raw_meta: dict[str, Any] = field(default_factory=dict)        # 平台專用欄位

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "sender": self.sender,
            "sender_id": self.sender_id,
            "text": self.text,
            "thread_id": self.thread_id,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "priority": self.priority,
            "attachments": self.attachments,
            "raw_meta": self.raw_meta,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "UnifiedMessage":
        return cls(
            channel=str(d.get("channel", "")),
            sender=str(d.get("sender", "")),
            sender_id=str(d.get("sender_id", "")),
            text=str(d.get("text", "")),
            thread_id=str(d.get("thread_id", "")),
            message_id=str(d.get("message_id", "")),
            timestamp=str(d.get("timestamp", "")),
            priority=str(d.get("priority", "normal")),
            attachments=list(d.get("attachments", [])),
            raw_meta=dict(d.get("raw_meta", {})),
        )

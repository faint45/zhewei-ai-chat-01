# -*- coding: utf-8 -*-
"""適配層基底：各通道實作 fetch_recent() 回傳 UnifiedMessage 列表。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brain_modules.unified_messages import UnifiedMessage  # noqa: F401


class BaseMessageAdapter(ABC):
    """單一通道適配器：讀取近期訊息並轉成統一格式。"""

    channel_name: str = "base"

    @abstractmethod
    def fetch_recent(self, limit: int = 20, since_ts: str | None = None) -> list["UnifiedMessage"]:
        """取得近期訊息，轉成 UnifiedMessage。limit 預設 20；since_ts 可選 ISO 時間篩選。"""
        pass

    def health_check(self) -> tuple[bool, str]:
        """檢查此通道是否可用。回傳 (ok, detail)。"""
        return True, "ok"

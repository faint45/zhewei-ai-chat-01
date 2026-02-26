# -*- coding: utf-8 -*-
"""全通訊訊息適配層：各平台轉成 UnifiedMessage。"""
from __future__ import annotations

import sys
from pathlib import Path

_parent = Path(__file__).resolve().parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))
from brain_modules.unified_messages import UnifiedMessage  # noqa: E402

from .base import BaseMessageAdapter
from .discord_adapter import DiscordAdapter
from .email_adapter import EmailAdapter
from .telegram_adapter import TelegramAdapter
from .wechat_adapter import WeChatAdapter
from .social_adapter import SocialAdapter

__all__ = [
    "BaseMessageAdapter",
    "UnifiedMessage",
    "DiscordAdapter",
    "EmailAdapter",
    "TelegramAdapter",
    "WeChatAdapter",
    "SocialAdapter",
]

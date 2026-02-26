# -*- coding: utf-8 -*-
"""
築未科技大腦 — 擴充接入閘道（預留）
供後續設備、軟件、網頁接入運算的註冊與擴充介面。
產品架構：一套遠端/本地皆可運行的 AI 模組，後續軟件/APP 皆接入此模組做運算，商用化供訂閱。
詳見：築未科技大腦_產品架構與商用訂閱.md

目前主介面已由 brain_bridge_fastapi 提供（/compute、/integrations/*）。
本模組為擴充預留，可於未來加入：
- 設備註冊與心跳
- 軟件授權驗證、訂閱方案與用量額度
- 網頁 Token 管理
"""
import os
from pathlib import Path
from typing import Optional

BASE = Path(__file__).parent.resolve()
_REGISTERED_DEVICES: dict = {}


def register_device(device_id: str, source: str = "device", metadata: dict = None) -> bool:
    """預留：設備註冊"""
    _REGISTERED_DEVICES[device_id] = {"source": source, "metadata": metadata or {}}
    return True


def is_registered(device_id: str) -> bool:
    """預留：檢查設備是否已註冊"""
    return device_id in _REGISTERED_DEVICES


def get_registered() -> dict:
    """預留：取得已註冊設備列表"""
    return dict(_REGISTERED_DEVICES)

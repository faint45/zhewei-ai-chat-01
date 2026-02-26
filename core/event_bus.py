# -*- coding: utf-8 -*-
"""
築未科技 — EventStream 事件匯流排
借鑑 OpenHands EventStream 模式，所有元件透過事件通訊，完全解耦

用法：
    from core.event_bus import event_bus, Event

    # 訂閱
    def on_water_level(event: Event):
        print(f"水位: {event.data['level_m']}")
    event_bus.subscribe("water_level.reading", on_water_level)

    # 發布
    event_bus.publish("water_level.reading", {"station_id": "WA-001", "level_m": 2.5})

    # 非同步
    await event_bus.publish_async("decision.alert", {"level": 3})
"""
import asyncio
import logging
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("core.event_bus")


class EventPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """事件資料結構"""
    event_type: str                          # 事件類型（dot-separated namespace）
    data: Dict[str, Any]                     # 事件資料
    source: str = ""                         # 來源模組
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    priority: EventPriority = EventPriority.NORMAL

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
            "priority": self.priority.name,
        }


@dataclass
class Subscription:
    """訂閱記錄"""
    callback: Callable
    event_pattern: str       # 支援 wildcard: "water_level.*", "*"
    subscriber_id: str = ""
    is_async: bool = False


class EventBus:
    """
    輕量事件匯流排

    特性：
    1. 同步/非同步 publish
    2. Wildcard 訂閱（water_level.* 匹配 water_level.reading）
    3. 事件優先級
    4. 事件歷史（ring buffer）
    5. 錯誤隔離（一個 subscriber 失敗不影響其他）
    6. 執行緒安全
    """

    def __init__(self, history_size: int = 500):
        self._subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        self._lock = threading.RLock()
        self._history: List[Event] = []
        self._history_size = history_size
        self._stats = {
            "total_published": 0,
            "total_delivered": 0,
            "total_errors": 0,
        }

    # ===== 訂閱 =====

    def subscribe(self, event_pattern: str, callback: Callable,
                  subscriber_id: str = "") -> str:
        """
        訂閱事件

        Args:
            event_pattern: 事件模式，支援 wildcard
                - "water_level.reading" — 精確匹配
                - "water_level.*" — 匹配 water_level 下所有子事件
                - "*.alert" — 匹配所有 alert 結尾的事件
                - "*" — 匹配所有事件
            callback: 回呼函數，接收 Event 參數
            subscriber_id: 訂閱者 ID（用於取消訂閱）

        Returns:
            subscriber_id
        """
        if not subscriber_id:
            subscriber_id = f"sub_{uuid.uuid4().hex[:8]}"

        is_async = asyncio.iscoroutinefunction(callback)
        sub = Subscription(
            callback=callback,
            event_pattern=event_pattern,
            subscriber_id=subscriber_id,
            is_async=is_async,
        )

        with self._lock:
            self._subscriptions[event_pattern].append(sub)

        log.debug(f"訂閱: {subscriber_id} → {event_pattern}")
        return subscriber_id

    def unsubscribe(self, subscriber_id: str):
        """取消訂閱"""
        with self._lock:
            for pattern in list(self._subscriptions.keys()):
                self._subscriptions[pattern] = [
                    s for s in self._subscriptions[pattern]
                    if s.subscriber_id != subscriber_id
                ]
                if not self._subscriptions[pattern]:
                    del self._subscriptions[pattern]

    def unsubscribe_all(self, event_pattern: str = ""):
        """取消所有訂閱（或指定 pattern）"""
        with self._lock:
            if event_pattern:
                self._subscriptions.pop(event_pattern, None)
            else:
                self._subscriptions.clear()

    # ===== 發布 =====

    def publish(self, event_type: str, data: Dict[str, Any] = None,
                source: str = "", priority: EventPriority = EventPriority.NORMAL) -> Event:
        """
        同步發布事件

        Args:
            event_type: 事件類型（如 "water_level.reading"）
            data: 事件資料
            source: 來源模組名稱
            priority: 優先級

        Returns:
            Event 物件
        """
        event = Event(
            event_type=event_type,
            data=data or {},
            source=source,
            priority=priority,
        )

        # 記錄歷史
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._history_size:
                self._history = self._history[-self._history_size:]
            self._stats["total_published"] += 1

        # 分發給匹配的訂閱者
        matched = self._match_subscribers(event_type)
        for sub in matched:
            try:
                if sub.is_async:
                    # 同步 context 中呼叫 async callback
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(sub.callback(event))
                    except RuntimeError:
                        asyncio.run(sub.callback(event))
                else:
                    sub.callback(event)
                self._stats["total_delivered"] += 1
            except Exception as e:
                self._stats["total_errors"] += 1
                log.error(f"事件處理錯誤 [{sub.subscriber_id}] {event_type}: {e}")

        return event

    async def publish_async(self, event_type: str, data: Dict[str, Any] = None,
                            source: str = "", priority: EventPriority = EventPriority.NORMAL) -> Event:
        """非同步發布事件"""
        event = Event(
            event_type=event_type,
            data=data or {},
            source=source,
            priority=priority,
        )

        with self._lock:
            self._history.append(event)
            if len(self._history) > self._history_size:
                self._history = self._history[-self._history_size:]
            self._stats["total_published"] += 1

        matched = self._match_subscribers(event_type)
        for sub in matched:
            try:
                if sub.is_async:
                    await sub.callback(event)
                else:
                    sub.callback(event)
                self._stats["total_delivered"] += 1
            except Exception as e:
                self._stats["total_errors"] += 1
                log.error(f"事件處理錯誤 [{sub.subscriber_id}] {event_type}: {e}")

        return event

    # ===== 查詢 =====

    def get_history(self, event_type: str = "", limit: int = 50) -> List[Event]:
        """查詢事件歷史"""
        with self._lock:
            if event_type:
                filtered = [e for e in self._history if self._pattern_match(event_type, e.event_type)]
            else:
                filtered = list(self._history)
        return filtered[-limit:]

    def get_stats(self) -> dict:
        """取得統計"""
        with self._lock:
            return {
                **self._stats,
                "active_subscriptions": sum(len(v) for v in self._subscriptions.values()),
                "history_size": len(self._history),
            }

    def get_subscribers(self) -> Dict[str, int]:
        """取得各 pattern 的訂閱數"""
        with self._lock:
            return {k: len(v) for k, v in self._subscriptions.items()}

    # ===== 內部 =====

    def _match_subscribers(self, event_type: str) -> List[Subscription]:
        """找出匹配的訂閱者，按優先級排序"""
        matched = []
        with self._lock:
            for pattern, subs in self._subscriptions.items():
                if self._pattern_match(pattern, event_type):
                    matched.extend(subs)
        return matched

    @staticmethod
    def _pattern_match(pattern: str, event_type: str) -> bool:
        """
        Wildcard 匹配
        - "*" 匹配所有
        - "water_level.*" 匹配 "water_level.reading", "water_level.alert"
        - "*.alert" 匹配 "water_level.alert", "decision.alert"
        - "water_level.reading" 精確匹配
        """
        if pattern == "*":
            return True
        if pattern == event_type:
            return True
        if "*" in pattern:
            parts = pattern.split("*")
            if len(parts) == 2:
                prefix, suffix = parts
                return event_type.startswith(prefix) and event_type.endswith(suffix)
        return False


# ===== 全局單例 =====
event_bus = EventBus()


# ===== 預定義事件類型 =====

class EventTypes:
    """標準事件類型常數"""

    # 水情
    WATER_LEVEL_READING = "water_level.reading"
    WATER_LEVEL_ALERT = "water_level.alert"
    WATER_DECISION = "water_level.decision"
    WATER_BROADCAST = "water_level.broadcast"

    # 感測器
    SENSOR_DHT = "sensor.dht"
    SENSOR_CLOUD = "sensor.cloud"
    SENSOR_RADAR = "sensor.radar"
    SENSOR_LORA = "sensor.lora"

    # AI 決策
    DECISION_FLOOD = "decision.flood"
    DECISION_SAFETY = "decision.safety"

    # 警報
    ALERT_NTFY = "alert.ntfy"
    ALERT_BROADCAST = "alert.broadcast"
    ALERT_LINE = "alert.line"

    # LLM
    LLM_REQUEST = "llm.request"
    LLM_RESPONSE = "llm.response"
    LLM_ERROR = "llm.error"
    LLM_BUDGET_WARNING = "llm.budget_warning"

    # 營建
    CONSTRUCTION_VOICE = "construction.voice"
    CONSTRUCTION_PHOTO = "construction.photo"
    CONSTRUCTION_EVENT = "construction.event"
    CONSTRUCTION_REPORT = "construction.report"
    CONSTRUCTION_SAFETY = "construction.safety"

    # 系統
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_HEALTH = "system.health"

# -*- coding: utf-8 -*-
"""
水情預警系統 — 五源加權 AI 決策引擎
40% 雷達水位 + 25% 視覺水位 + 15% 雲量 + 10% 溫濕度 + 10% 氣象預報

複用：
  - prediction_modules/prediction_engine.py: PredictionEngine 基類
  - prediction_modules/alert_manager.py: NationalAlertManager
"""
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

log = logging.getLogger("water_alert.decision")

# 確保能 import 主專案
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from water_alert.config import StationConfig, SystemConfig, DEFAULT_SYSTEM


@dataclass
class SensorInput:
    """單一感測源輸入"""
    source: str              # radar / vision / cloud / dht / forecast
    value: float             # 正規化值 0-100（0=安全, 100=最危險）
    raw_value: float = 0.0   # 原始值
    unit: str = ""           # 原始單位
    confidence: float = 1.0  # 信心度 0-1
    timestamp: str = ""
    valid: bool = True
    error: str = ""


@dataclass
class FloodDecision:
    """洪水決策結果"""
    timestamp: str
    station_id: str
    # 五源加權
    weighted_score: float    # 0-100 加權分數
    alert_level: int         # 0=安全, 1=注意, 2=警戒, 3=危險, 4=撤離
    alert_name: str          # "安全" / "注意" / "警戒" / "危險" / "撤離"
    # 各源詳情
    inputs: List[SensorInput] = field(default_factory=list)
    # 建議行動
    actions: List[str] = field(default_factory=list)
    # 趨勢
    trend: str = "stable"    # rising / stable / falling
    rate_of_change: float = 0.0  # 水位變化率 (m/hr)
    # 預估到達時間
    eta_warning_min: Optional[float] = None   # 預估幾分鐘後到警戒水位
    eta_critical_min: Optional[float] = None  # 預估幾分鐘後到危險水位

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "station_id": self.station_id,
            "weighted_score": round(self.weighted_score, 1),
            "alert_level": self.alert_level,
            "alert_name": self.alert_name,
            "inputs": [{"source": i.source, "value": round(i.value, 1),
                         "raw_value": i.raw_value, "unit": i.unit,
                         "confidence": i.confidence, "valid": i.valid}
                        for i in self.inputs],
            "actions": self.actions,
            "trend": self.trend,
            "rate_of_change": round(self.rate_of_change, 3),
            "eta_warning_min": self.eta_warning_min,
            "eta_critical_min": self.eta_critical_min,
        }


# ===== 警報等級定義 =====
ALERT_LEVELS = {
    0: {"name": "安全", "color": "green", "threshold": 25},
    1: {"name": "注意", "color": "yellow", "threshold": 50},
    2: {"name": "警戒", "color": "orange", "threshold": 70},
    3: {"name": "危險", "color": "red", "threshold": 85},
    4: {"name": "撤離", "color": "darkred", "threshold": 100},
}


class FloodDecisionEngine:
    """
    五源加權 AI 決策引擎

    權重分配：
    - 雷達水位 40% — 最直接、最精確
    - 視覺水位 25% — YOLO/VLM 水面辨識
    - 雲量    15% — 魚眼鏡頭雲型分析
    - 溫濕度  10% — DHT22 環境監測
    - 氣象預報 10% — CWB 降雨預報
    """

    def __init__(self, station: StationConfig, system: SystemConfig = None):
        self.station = station
        self.system = system or DEFAULT_SYSTEM
        self._history: list = []  # 歷史決策（用於趨勢分析）
        self._max_history = 120   # 保留最近 120 筆（約 1 小時 @30s 間隔）

    def decide(self, inputs: List[SensorInput]) -> FloodDecision:
        """
        核心決策：五源加權計算 + 趨勢分析 + 警報等級判定

        Args:
            inputs: 各感測源輸入列表

        Returns:
            FloodDecision 決策結果
        """
        now = datetime.now().isoformat()

        # 1. 加權計算
        weights = {
            "radar": self.system.weight_radar,
            "vision": self.system.weight_vision,
            "cloud": self.system.weight_cloud,
            "dht": self.system.weight_dht,
            "forecast": self.system.weight_forecast,
        }

        total_weight = 0.0
        weighted_sum = 0.0
        for inp in inputs:
            w = weights.get(inp.source, 0)
            if inp.valid and w > 0:
                # 信心度加權
                effective_w = w * inp.confidence
                weighted_sum += inp.value * effective_w
                total_weight += effective_w

        score = weighted_sum / total_weight if total_weight > 0 else 0

        # 2. 判定警報等級
        alert_level = 0
        for lvl in sorted(ALERT_LEVELS.keys(), reverse=True):
            if score >= ALERT_LEVELS[lvl]["threshold"]:
                alert_level = lvl
                break

        # 3. 趨勢分析
        trend, rate = self._analyze_trend(score)

        # 4. ETA 預估
        eta_warning = None
        eta_critical = None
        radar_input = next((i for i in inputs if i.source == "radar" and i.valid), None)
        if radar_input and rate > 0:
            current_level = radar_input.raw_value
            warning_level = self.station.water_level_warning_m
            critical_level = self.station.water_level_critical_m
            if current_level < warning_level:
                eta_warning = round((warning_level - current_level) / rate * 60, 0)
            if current_level < critical_level:
                eta_critical = round((critical_level - current_level) / rate * 60, 0)

        # 5. 建議行動
        actions = self._suggest_actions(alert_level, trend, rate)

        decision = FloodDecision(
            timestamp=now,
            station_id=self.station.station_id,
            weighted_score=score,
            alert_level=alert_level,
            alert_name=ALERT_LEVELS[alert_level]["name"],
            inputs=inputs,
            actions=actions,
            trend=trend,
            rate_of_change=rate,
            eta_warning_min=eta_warning,
            eta_critical_min=eta_critical,
        )

        # 記錄歷史
        self._history.append({"ts": time.time(), "score": score, "level": alert_level})
        if len(self._history) > self._max_history:
            self._history.pop(0)

        return decision

    def normalize_radar(self, water_level_m: float) -> SensorInput:
        """正規化雷達水位到 0-100 分數"""
        s = self.station
        if water_level_m <= 0:
            score = 0
        elif water_level_m <= s.water_level_warning_m:
            score = (water_level_m / s.water_level_warning_m) * 25
        elif water_level_m <= s.water_level_alert_m:
            ratio = (water_level_m - s.water_level_warning_m) / (s.water_level_alert_m - s.water_level_warning_m)
            score = 25 + ratio * 25
        elif water_level_m <= s.water_level_critical_m:
            ratio = (water_level_m - s.water_level_alert_m) / (s.water_level_critical_m - s.water_level_alert_m)
            score = 50 + ratio * 20
        elif water_level_m <= s.water_level_evacuate_m:
            ratio = (water_level_m - s.water_level_critical_m) / (s.water_level_evacuate_m - s.water_level_critical_m)
            score = 70 + ratio * 15
        else:
            score = min(100, 85 + (water_level_m - s.water_level_evacuate_m) * 10)

        return SensorInput(
            source="radar", value=score, raw_value=water_level_m,
            unit="m", timestamp=datetime.now().isoformat(),
        )

    def normalize_cloud(self, cloud_cover_pct: float, cloud_type: str = "") -> SensorInput:
        """正規化雲量到 0-100"""
        # 厚雲 > 80% → 高分；積雨雲加倍
        score = cloud_cover_pct * 0.5  # 基本 0-50
        if cloud_type in ("cumulonimbus", "nimbostratus", "積雨雲", "雨層雲"):
            score *= 1.8
        score = min(100, score)
        return SensorInput(
            source="cloud", value=score, raw_value=cloud_cover_pct,
            unit="%", timestamp=datetime.now().isoformat(),
        )

    def normalize_dht(self, temperature: float, humidity: float) -> SensorInput:
        """正規化溫濕度"""
        # 高濕度 + 降溫 → 降雨可能性高
        score = 0
        if humidity > 90:
            score = 60 + (humidity - 90) * 4
        elif humidity > 80:
            score = 30 + (humidity - 80) * 3
        elif humidity > 70:
            score = (humidity - 70) * 3
        score = min(100, score)
        return SensorInput(
            source="dht", value=score, raw_value=humidity,
            unit="%RH", timestamp=datetime.now().isoformat(),
        )

    def normalize_forecast(self, rainfall_mm: float, hours_ahead: int = 6) -> SensorInput:
        """正規化氣象預報"""
        # 6 小時累積雨量
        if rainfall_mm <= 10:
            score = rainfall_mm * 2
        elif rainfall_mm <= 40:
            score = 20 + (rainfall_mm - 10) * 1.5
        elif rainfall_mm <= 80:
            score = 65 + (rainfall_mm - 40) * 0.5
        else:
            score = min(100, 85 + (rainfall_mm - 80) * 0.2)
        return SensorInput(
            source="forecast", value=score, raw_value=rainfall_mm,
            unit="mm", timestamp=datetime.now().isoformat(),
        )

    def _analyze_trend(self, current_score: float) -> tuple:
        """分析趨勢（rising/stable/falling）和變化率"""
        if len(self._history) < 3:
            return "stable", 0.0

        recent = self._history[-10:]  # 最近 10 筆
        scores = [h["score"] for h in recent]
        times = [h["ts"] for h in recent]

        # 線性回歸斜率
        n = len(scores)
        sum_t = sum(times)
        sum_s = sum(scores)
        sum_ts = sum(t * s for t, s in zip(times, scores))
        sum_t2 = sum(t * t for t in times)
        denom = n * sum_t2 - sum_t * sum_t
        if abs(denom) < 1e-10:
            return "stable", 0.0

        slope = (n * sum_ts - sum_t * sum_s) / denom  # 分數/秒
        rate_per_hour = slope * 3600

        if rate_per_hour > 2:
            trend = "rising"
        elif rate_per_hour < -2:
            trend = "falling"
        else:
            trend = "stable"

        return trend, rate_per_hour

    @staticmethod
    def _suggest_actions(level: int, trend: str, rate: float) -> list:
        """根據警報等級建議行動"""
        actions = {
            0: ["持續監測"],
            1: ["加密監測頻率至每 15 分鐘", "通知工地主任注意水情"],
            2: ["通知所有人員準備撤離", "啟動工地排水設備", "確認撤離路線暢通",
                "將重要機具移至高處"],
            3: ["立即啟動撤離程序", "啟動廣播喇叭警報", "啟動警示閃光燈",
                "通報 119 / 水利署", "停止所有施工作業"],
            4: ["全員立即撤離至安全高地", "確認人員清點完成", "關閉電力/瓦斯",
                "啟動國家級災害通報"],
        }
        result = actions.get(level, ["持續監測"])

        if trend == "rising" and level >= 1:
            result.insert(0, f"⚠️ 水位持續上升中（{rate:+.1f} 分/hr）")
        return result

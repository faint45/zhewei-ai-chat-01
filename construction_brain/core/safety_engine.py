# -*- coding: utf-8 -*-
"""
營建自動化大腦 — 工安檢查引擎
結合 YOLO 偵測 + LLM 判斷，產出工安報告與即時警報

複用：
  - tools/vision_edge_service.py: YOLO 偵測（安全帽、護欄、人員）
  - construction_brain/core/extract_work_events.py: LLM 事件抽取
"""
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger("construction_brain.safety")

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11460").rstrip("/")
OLLAMA_MODEL = os.environ.get("CB_LLM_MODEL", "qwen3:32b")

# 工安規範關鍵詞（用於 regex 快速偵測）
SAFETY_KEYWORDS = {
    "high": ["墜落", "倒塌", "觸電", "爆炸", "火災", "缺氧", "中毒", "感電",
             "無護欄", "未繫安全帶", "開口未防護", "無安全帽"],
    "medium": ["未戴安全帽", "反光背心", "安全網", "護欄鬆脫", "照明不足",
               "通道堵塞", "材料堆置", "鷹架", "開挖", "支撐不足"],
    "low": ["工具散落", "標示不清", "噪音", "粉塵", "高溫", "飲水"],
}


class SafetyEngine:
    """
    工安檢查引擎

    功能：
    1. 從文字/語音辨識結果偵測工安風險
    2. 從照片（YOLO+VLM）偵測安全違規
    3. 產出工安日報摘要
    4. 即時高風險警報推送
    """

    def __init__(self, project_name: str = ""):
        self.project_name = project_name
        self._alerts: list = []

    def check_text(self, transcript: str) -> list:
        """
        從文字中快速偵測工安關鍵詞（不需 LLM，即時回應）

        Returns: [{"risk": str, "severity": str, "source": "keyword"}]
        """
        alerts = []
        for severity, keywords in SAFETY_KEYWORDS.items():
            for kw in keywords:
                if kw in transcript:
                    alerts.append({
                        "risk": kw,
                        "severity": severity,
                        "action": self._suggest_action(kw, severity),
                        "source": "keyword",
                        "timestamp": datetime.now().isoformat(),
                    })
        self._alerts.extend(alerts)
        return alerts

    def check_photo(self, image_bytes: bytes) -> list:
        """
        從照片偵測工安違規（YOLO + 規則判斷）

        Returns: [{"risk": str, "severity": str, "source": "yolo"}]
        """
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

        alerts = []
        try:
            from tools.vision_edge_service import VisionPipeline
            pipeline = VisionPipeline()
            pipeline.load_yolo()
            detections = pipeline.yolo_detect(image_bytes)

            # 規則判斷
            persons = [d for d in detections if d["class"] == "person"]
            helmets = [d for d in detections if d["class"] in ("hard hat", "helmet", "safety helmet")]

            if persons and not helmets:
                alerts.append({
                    "risk": f"偵測到 {len(persons)} 名人員但未見安全帽",
                    "severity": "high",
                    "action": "立即要求所有人員配戴安全帽",
                    "source": "yolo",
                    "detection_count": len(persons),
                    "timestamp": datetime.now().isoformat(),
                })
            elif persons and len(helmets) < len(persons):
                alerts.append({
                    "risk": f"人員 {len(persons)} 人，安全帽僅 {len(helmets)} 頂",
                    "severity": "medium",
                    "action": "檢查並確認所有人員配戴安全帽",
                    "source": "yolo",
                    "timestamp": datetime.now().isoformat(),
                })
        except Exception as e:
            log.warning(f"YOLO 工安偵測跳過: {e}")

        self._alerts.extend(alerts)
        return alerts

    def check_with_llm(self, transcript: str, context: str = "") -> list:
        """
        深度工安分析（LLM）— 用於需要語境理解的情境

        Returns: [{"risk": str, "severity": str, "action": str, "source": "llm"}]
        """
        from construction_brain.core.extract_work_events import extract_events
        events = extract_events(transcript, project_name=self.project_name, context=context)
        alerts = events.get("safety_alerts", [])
        for a in alerts:
            a["source"] = "llm"
            a["timestamp"] = datetime.now().isoformat()
        self._alerts.extend(alerts)
        return alerts

    def get_all_alerts(self) -> list:
        """取得所有累積的警報"""
        return self._alerts

    def get_high_alerts(self) -> list:
        """取得高風險警報（需即時推送）"""
        return [a for a in self._alerts if a.get("severity") == "high"]

    def generate_safety_summary(self) -> str:
        """產出工安日報摘要"""
        if not self._alerts:
            return "今日無工安異常事項。"

        high = [a for a in self._alerts if a.get("severity") == "high"]
        medium = [a for a in self._alerts if a.get("severity") == "medium"]
        low = [a for a in self._alerts if a.get("severity") == "low"]

        lines = [f"工安日報摘要（{datetime.now().strftime('%Y-%m-%d')}）"]
        lines.append(f"工程名稱：{self.project_name}")
        lines.append(f"總警報數：{len(self._alerts)}")
        lines.append("")

        if high:
            lines.append(f"🔴 高風險（{len(high)} 項）— 需立即處理：")
            for a in high:
                lines.append(f"  - {a['risk']}（建議：{a.get('action', '')}）")
            lines.append("")

        if medium:
            lines.append(f"🟡 中風險（{len(medium)} 項）— 需限期改善：")
            for a in medium:
                lines.append(f"  - {a['risk']}")
            lines.append("")

        if low:
            lines.append(f"🟢 低風險（{len(low)} 項）— 持續關注：")
            for a in low:
                lines.append(f"  - {a['risk']}")

        return "\n".join(lines)

    def clear(self):
        """清除累積警報"""
        self._alerts.clear()

    @staticmethod
    def _suggest_action(keyword: str, severity: str) -> str:
        """根據關鍵詞建議處理措施"""
        actions = {
            "墜落": "立即檢查護欄、安全網、安全帶，必要時停工",
            "倒塌": "立即撤離人員，檢查支撐結構",
            "觸電": "立即斷電，檢查電力設備接地",
            "感電": "立即斷電，檢查電力設備接地",
            "無護欄": "立即設置護欄或安全警示",
            "未繫安全帶": "要求人員立即繫好安全帶",
            "無安全帽": "要求所有人員配戴安全帽",
            "未戴安全帽": "要求人員立即配戴安全帽",
            "開口未防護": "立即設置開口防護蓋或護欄",
        }
        return actions.get(keyword, f"依照工安規範處理 ({severity})")

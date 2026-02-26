#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 — 視覺邊緣運算學習模組 (Vision Edge Learning Module)

功能：
- 自動學習各領域邊緣運算最佳實踐
- 分析歷史辨識結果，找出低信心偵測並建議改進
- 維護領域知識庫（交通/工地/零售/農業/工業等）
- 提供 prompt 優化建議，提升 VLM 辨識精度
- 追蹤辨識準確率趨勢
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("VisionLearning")

ROOT = Path(__file__).resolve().parent.parent
LEARNING_DIR = ROOT / "reports" / "vision_learning"
LEARNING_DIR.mkdir(parents=True, exist_ok=True)
DOMAIN_KB_DIR = LEARNING_DIR / "domain_knowledge"
DOMAIN_KB_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================================
# 領域知識庫
# =====================================================================

DOMAIN_KNOWLEDGE = {
    "traffic": {
        "name": "交通監控",
        "name_zh": "交通監控",
        "description": "道路車輛、行人、交通號誌辨識",
        "yolo_focus_classes": ["car", "truck", "bus", "motorcycle", "bicycle", "person", "traffic light", "stop sign"],
        "vlm_prompt_template": (
            "你是專業交通監控 AI。請仔細分析畫面中的交通狀況：\n"
            "1. 車輛數量與類型（轎車/SUV/貨車/公車/機車/腳踏車）\n"
            "2. 每台車的顏色、行駛方向\n"
            "3. 如果看得到車牌請辨識\n"
            "4. 行人數量與位置\n"
            "5. 交通號誌狀態\n"
            "6. 是否有違規行為（闖紅燈、逆向、違停）\n"
            "7. 整體交通流量評估（暢通/壅塞/嚴重壅塞）"
        ),
        "best_practices": [
            "使用 YOLOv8n 或 YOLOv8s 以平衡速度與精度",
            "車牌辨識建議搭配專用 OCR 模型（如 PaddleOCR）",
            "夜間場景需調整影像亮度/對比度前處理",
            "高速公路場景建議提高 YOLO 信心閾值至 0.4",
            "交叉路口建議每 0.5 秒抽幀以追蹤車輛軌跡",
            "雨天/霧天場景需啟用影像去霧前處理",
        ],
        "conf_threshold": 0.3,
        "frame_interval_sec": 1.0,
    },
    "construction": {
        "name": "工地安全",
        "name_zh": "工地安全監控",
        "description": "施工現場安全帽、反光背心、危險區域偵測",
        "yolo_focus_classes": ["person", "hard hat", "safety vest", "no hard hat"],
        "vlm_prompt_template": (
            "你是施工安全 AI 檢查員。請分析工地照片：\n"
            "1. 人員總數及是否佩戴安全帽\n"
            "2. 是否穿著反光背心\n"
            "3. 高空作業是否有安全繩\n"
            "4. 機具操作是否安全\n"
            "5. 材料堆放是否穩固\n"
            "6. 是否有未設圍欄的危險區域"
        ),
        "best_practices": [
            "使用專門訓練的安全帽偵測模型可大幅提升精度",
            "建議 YOLO 信心閾值設為 0.35 以減少漏報",
            "工地環境複雜，建議同時使用 YOLO + VLM 雙重驗證",
            "夜間施工需確保照明充足或啟用紅外線攝影機",
            "定期更新模型以適應不同季節的服裝變化",
        ],
        "conf_threshold": 0.35,
        "frame_interval_sec": 5.0,
    },
    "retail": {
        "name": "零售分析",
        "name_zh": "零售場景分析",
        "description": "商店客流、商品陳列、顧客行為分析",
        "yolo_focus_classes": ["person", "handbag", "backpack", "bottle", "cell phone"],
        "vlm_prompt_template": (
            "你是零售場景分析 AI。請分析店鋪畫面：\n"
            "1. 顧客人數與分布\n"
            "2. 顧客停留區域（貨架/收銀台/入口）\n"
            "3. 商品陳列狀態\n"
            "4. 是否有異常行為\n"
            "5. 整體客流密度評估"
        ),
        "best_practices": [
            "人員計數建議使用 ByteTrack 追蹤避免重複計數",
            "俯視角度攝影機更適合客流統計",
            "熱力圖分析需累積至少 30 分鐘的資料",
            "建議每 2 秒抽幀以平衡精度與運算量",
        ],
        "conf_threshold": 0.3,
        "frame_interval_sec": 2.0,
    },
    "agriculture": {
        "name": "農業監控",
        "name_zh": "農業智慧監控",
        "description": "作物健康、病蟲害、灌溉狀態分析",
        "yolo_focus_classes": ["bird", "cow", "sheep", "horse", "potted plant"],
        "vlm_prompt_template": (
            "你是農業 AI 分析師。請分析農場/田地照片：\n"
            "1. 作物生長狀態（健康/枯萎/病害）\n"
            "2. 是否有病蟲害跡象\n"
            "3. 灌溉狀態\n"
            "4. 動物數量與狀態\n"
            "5. 天氣/光照條件評估"
        ),
        "best_practices": [
            "作物病害偵測建議使用專門訓練的模型",
            "無人機航拍需校正鏡頭畸變",
            "不同生長期需調整辨識參數",
            "建議搭配溫濕度感測器資料綜合分析",
        ],
        "conf_threshold": 0.25,
        "frame_interval_sec": 10.0,
    },
    "industrial": {
        "name": "工業檢測",
        "name_zh": "工業品質檢測",
        "description": "產品瑕疵、設備狀態、生產線監控",
        "yolo_focus_classes": [],
        "vlm_prompt_template": (
            "你是工業品質檢測 AI。請分析產品/設備照片：\n"
            "1. 產品表面是否有瑕疵（刮痕/凹陷/變色）\n"
            "2. 尺寸是否符合規格\n"
            "3. 設備運轉狀態\n"
            "4. 是否有異常磨損\n"
            "5. 生產線是否正常運作"
        ),
        "best_practices": [
            "瑕疵偵測需要高解析度影像（至少 1080p）",
            "建議使用固定光源和角度以減少誤判",
            "產品分類建議訓練專用模型",
            "設備監控建議搭配振動/溫度感測器",
        ],
        "conf_threshold": 0.2,
        "frame_interval_sec": 1.0,
    },
    "general": {
        "name": "通用場景",
        "name_zh": "通用場景分析",
        "description": "一般場景的全物件辨識與計數",
        "yolo_focus_classes": [],
        "vlm_prompt_template": (
            "你是專業視覺分析 AI。請仔細觀察並列出畫面中所有可見物件，\n"
            "包含數量、位置、顏色等屬性。不要遺漏任何細節。"
        ),
        "best_practices": [
            "通用場景建議使用 YOLOv8n（速度優先）或 YOLOv8m（精度優先）",
            "VLM 補充辨識可發現 YOLO 80 類以外的物件",
            "建議 YOLO 信心閾值設為 0.25 以最大化召回率",
            "複雜場景建議分區域分析以提升精度",
        ],
        "conf_threshold": 0.25,
        "frame_interval_sec": 2.0,
    },
}


# =====================================================================
# 資料結構
# =====================================================================

@dataclass
class LearningRecord:
    """學習紀錄"""
    id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    domain: str = "general"
    source_name: str = ""
    # 偵測統計
    total_objects: int = 0
    avg_confidence: float = 0.0
    low_conf_objects: int = 0  # 信心 < 0.5 的物件數
    class_distribution: dict = field(default_factory=dict)
    # 改進建議
    suggestions: list = field(default_factory=list)
    # VLM 補充發現
    vlm_extra_count: int = 0


@dataclass
class DomainProfile:
    """領域分析檔案"""
    domain: str = "general"
    total_analyses: int = 0
    total_objects_detected: int = 0
    avg_confidence_trend: list = field(default_factory=list)  # 最近 N 次平均信心
    common_classes: dict = field(default_factory=dict)  # 類別 → 出現次數
    common_issues: list = field(default_factory=list)  # 常見問題
    optimized_conf_threshold: float = 0.25
    last_updated: str = ""


# =====================================================================
# 學習引擎
# =====================================================================

class VisionLearningModule:
    """視覺邊緣運算學習模組"""

    def __init__(self):
        self._records: list[LearningRecord] = []
        self._domain_profiles: dict[str, DomainProfile] = {}
        self._load_profiles()

    def _load_profiles(self):
        """載入已儲存的領域檔案"""
        for domain in DOMAIN_KNOWLEDGE:
            profile_path = DOMAIN_KB_DIR / f"{domain}_profile.json"
            if profile_path.exists():
                try:
                    data = json.loads(profile_path.read_text(encoding="utf-8"))
                    self._domain_profiles[domain] = DomainProfile(**data)
                except Exception:
                    self._domain_profiles[domain] = DomainProfile(domain=domain)
            else:
                self._domain_profiles[domain] = DomainProfile(domain=domain)

    def _save_profile(self, domain: str):
        """儲存領域檔案"""
        if domain in self._domain_profiles:
            profile = self._domain_profiles[domain]
            profile.last_updated = datetime.now(timezone.utc).isoformat()
            path = DOMAIN_KB_DIR / f"{domain}_profile.json"
            path.write_text(
                json.dumps(asdict(profile), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    # ── 領域偵測 ────────────────────────────────────────

    def detect_domain(self, detected_classes: list[str], scene_description: str = "") -> str:
        """根據偵測到的物件類別自動判斷領域"""
        scores = {}
        for domain, info in DOMAIN_KNOWLEDGE.items():
            if domain == "general":
                continue
            focus = set(info.get("yolo_focus_classes", []))
            if not focus:
                continue
            overlap = len(set(detected_classes) & focus)
            scores[domain] = overlap

        # 場景描述關鍵字匹配
        desc_lower = scene_description.lower()
        keyword_map = {
            "traffic": ["road", "highway", "intersection", "車", "路", "交通", "紅綠燈"],
            "construction": ["construction", "site", "工地", "施工", "安全帽", "鷹架"],
            "retail": ["store", "shop", "商店", "賣場", "貨架", "收銀"],
            "agriculture": ["farm", "crop", "field", "農", "田", "作物", "牧場"],
            "industrial": ["factory", "machine", "product", "工廠", "機台", "產品", "生產線"],
        }
        for domain, keywords in keyword_map.items():
            for kw in keywords:
                if kw in desc_lower:
                    scores[domain] = scores.get(domain, 0) + 2

        if scores:
            best = max(scores, key=scores.get)
            if scores[best] > 0:
                return best
        return "general"

    # ── 學習分析 ────────────────────────────────────────

    def learn_from_analysis(self, report_data: dict) -> LearningRecord:
        """從分析報告中學習"""
        summary = report_data.get("summary", {})
        all_dets = report_data.get("all_detections_flat", [])
        scene_desc = report_data.get("scene_description", "")

        # 計算統計
        total = summary.get("total", 0)
        confidences = [d.get("confidence", 0) for d in all_dets if d.get("confidence", 0) > 0]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        low_conf = sum(1 for c in confidences if c < 0.5)
        class_dist = summary.get("by_class_zh", {})

        # 偵測領域
        detected_classes = [d.get("class_name", "") for d in all_dets]
        domain = self.detect_domain(detected_classes, scene_desc)

        # 產生改進建議
        suggestions = self._generate_suggestions(
            domain, total, avg_conf, low_conf, class_dist, all_dets, scene_desc
        )

        # 建立學習紀錄
        record = LearningRecord(
            id=report_data.get("id", ""),
            domain=domain,
            source_name=report_data.get("source_name", ""),
            total_objects=total,
            avg_confidence=round(avg_conf, 3),
            low_conf_objects=low_conf,
            class_distribution=class_dist,
            suggestions=suggestions,
            vlm_extra_count=sum(
                len(fa.get("vlm_extra_objects", []))
                for fa in report_data.get("frame_analyses", [])
            ),
        )
        self._records.append(record)

        # 更新領域檔案
        self._update_domain_profile(domain, record)

        # 儲存
        self._save_record(record)
        self._save_profile(domain)

        log.info(f"學習完成: domain={domain}, objects={total}, avg_conf={avg_conf:.2f}, suggestions={len(suggestions)}")
        return record

    def _generate_suggestions(
        self,
        domain: str,
        total: int,
        avg_conf: float,
        low_conf: int,
        class_dist: dict,
        all_dets: list,
        scene_desc: str,
    ) -> list[str]:
        """根據分析結果產生改進建議"""
        suggestions = []
        dk = DOMAIN_KNOWLEDGE.get(domain, DOMAIN_KNOWLEDGE["general"])

        # 信心度建議
        if avg_conf < 0.4 and total > 0:
            suggestions.append(
                f"平均信心度偏低 ({avg_conf:.0%})，建議：\n"
                f"  - 提高影像解析度\n"
                f"  - 改善光照條件\n"
                f"  - 考慮使用更大的 YOLO 模型（如 yolov8s 或 yolov8m）"
            )

        if low_conf > total * 0.3 and total > 3:
            suggestions.append(
                f"有 {low_conf}/{total} 個物件信心度低於 50%，"
                f"建議檢查攝影機角度和焦距"
            )

        # 物件數量建議
        if total == 0:
            suggestions.append(
                "未偵測到任何物件，可能原因：\n"
                "  - 影像品質不佳\n"
                "  - 場景中無 YOLO 可辨識的物件\n"
                "  - 建議降低信心閾值（conf < 0.2）重試"
            )

        # 領域特定建議
        if domain == "traffic":
            vehicle_count = sum(v for k, v in class_dist.items()
                                if k in ("小客車", "卡車/大車", "公車/大車", "機車", "腳踏車"))
            if vehicle_count > 20:
                suggestions.append("車輛密度高，建議啟用物件追蹤（ByteTrack）避免重複計數")
            person_count = class_dist.get("人", 0)
            if person_count > 10:
                suggestions.append("行人密度高，建議提高抽幀頻率以追蹤行人動態")

        elif domain == "construction":
            if "人" in class_dist and class_dist["人"] > 0:
                suggestions.append("偵測到工地人員，建議搭配安全帽專用偵測模型以提升安全監控精度")

        # 通用最佳實踐
        bp = dk.get("best_practices", [])
        if bp:
            suggestions.append(f"【{dk['name_zh']}最佳實踐】\n" + "\n".join(f"  - {p}" for p in bp[:3]))

        return suggestions

    def _update_domain_profile(self, domain: str, record: LearningRecord):
        """更新領域檔案"""
        profile = self._domain_profiles.get(domain, DomainProfile(domain=domain))
        profile.total_analyses += 1
        profile.total_objects_detected += record.total_objects

        # 信心度趨勢（保留最近 50 筆）
        profile.avg_confidence_trend.append(record.avg_confidence)
        if len(profile.avg_confidence_trend) > 50:
            profile.avg_confidence_trend = profile.avg_confidence_trend[-50:]

        # 類別分布累計
        for cls, cnt in record.class_distribution.items():
            profile.common_classes[cls] = profile.common_classes.get(cls, 0) + cnt

        # 動態調整信心閾值
        if len(profile.avg_confidence_trend) >= 5:
            recent_avg = sum(profile.avg_confidence_trend[-5:]) / 5
            if recent_avg > 0.6:
                profile.optimized_conf_threshold = min(0.4, profile.optimized_conf_threshold + 0.02)
            elif recent_avg < 0.3:
                profile.optimized_conf_threshold = max(0.15, profile.optimized_conf_threshold - 0.02)

        self._domain_profiles[domain] = profile

    def _save_record(self, record: LearningRecord):
        """儲存學習紀錄"""
        path = LEARNING_DIR / f"record_{record.id}.json"
        path.write_text(
            json.dumps(asdict(record), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── 查詢 API ────────────────────────────────────────

    def get_domain_info(self, domain: str = "") -> dict:
        """取得領域知識"""
        if domain and domain in DOMAIN_KNOWLEDGE:
            dk = DOMAIN_KNOWLEDGE[domain]
            profile = self._domain_profiles.get(domain, DomainProfile(domain=domain))
            return {
                "domain": domain,
                "info": dk,
                "profile": asdict(profile),
            }
        # 列出所有領域
        return {
            "domains": {
                d: {
                    "name": info["name_zh"],
                    "description": info["description"],
                    "analyses": self._domain_profiles.get(d, DomainProfile()).total_analyses,
                }
                for d, info in DOMAIN_KNOWLEDGE.items()
            }
        }

    def get_optimized_params(self, domain: str = "general") -> dict:
        """取得領域優化參數"""
        dk = DOMAIN_KNOWLEDGE.get(domain, DOMAIN_KNOWLEDGE["general"])
        profile = self._domain_profiles.get(domain, DomainProfile(domain=domain))
        return {
            "domain": domain,
            "conf_threshold": profile.optimized_conf_threshold or dk.get("conf_threshold", 0.25),
            "frame_interval_sec": dk.get("frame_interval_sec", 2.0),
            "vlm_prompt_template": dk.get("vlm_prompt_template", ""),
            "yolo_focus_classes": dk.get("yolo_focus_classes", []),
            "best_practices": dk.get("best_practices", []),
        }

    def get_learning_summary(self) -> dict:
        """取得學習模組總結"""
        total_records = len(self._records)
        domain_stats = {}
        for d, p in self._domain_profiles.items():
            if p.total_analyses > 0:
                domain_stats[d] = {
                    "name": DOMAIN_KNOWLEDGE.get(d, {}).get("name_zh", d),
                    "analyses": p.total_analyses,
                    "objects_detected": p.total_objects_detected,
                    "avg_conf_recent": (
                        round(sum(p.avg_confidence_trend[-5:]) / len(p.avg_confidence_trend[-5:]), 3)
                        if p.avg_confidence_trend else 0
                    ),
                    "optimized_threshold": p.optimized_conf_threshold,
                    "top_classes": dict(
                        sorted(p.common_classes.items(), key=lambda x: -x[1])[:10]
                    ),
                }

        return {
            "total_learning_records": total_records,
            "active_domains": len(domain_stats),
            "domain_stats": domain_stats,
            "available_domains": list(DOMAIN_KNOWLEDGE.keys()),
        }

    def get_recent_suggestions(self, limit: int = 10) -> list[dict]:
        """取得最近的改進建議"""
        recent = self._records[-limit:] if self._records else []
        return [
            {
                "id": r.id,
                "domain": r.domain,
                "timestamp": r.timestamp,
                "total_objects": r.total_objects,
                "avg_confidence": r.avg_confidence,
                "suggestions": r.suggestions,
            }
            for r in reversed(recent)
        ]


# =====================================================================
# 全域實例
# =====================================================================
learning_module = VisionLearningModule()

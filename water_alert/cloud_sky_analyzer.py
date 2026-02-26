# -*- coding: utf-8 -*-
"""
水情預警系統 — 魚眼鏡頭雲量/雲型辨識
IMX219 魚眼鏡頭 → 天空影像 → 雲量% + 雲型分類

複用：
  - tools/vision_edge_service.py: VisionPipeline VLM 推理
"""
import io
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

log = logging.getLogger("water_alert.cloud")


@dataclass
class CloudAnalysis:
    """雲量分析結果"""
    timestamp: str
    station_id: str
    cloud_cover_pct: float      # 雲量佔比 (0-100%)
    cloud_type: str             # 雲型（cumulus/stratus/cumulonimbus/cirrus/clear）
    cloud_type_zh: str          # 雲型中文
    brightness: float           # 天空亮度 (0-255)
    rain_probability: float     # 降雨機率估計 (0-100)
    description: str            # VLM 描述
    valid: bool = True
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "station_id": self.station_id,
            "cloud_cover_pct": round(self.cloud_cover_pct, 1),
            "cloud_type": self.cloud_type,
            "cloud_type_zh": self.cloud_type_zh,
            "brightness": round(self.brightness, 1),
            "rain_probability": round(self.rain_probability, 1),
            "description": self.description,
            "valid": self.valid,
        }


# 雲型對照表
CLOUD_TYPES = {
    "clear": {"zh": "晴空", "rain_prob": 0},
    "cirrus": {"zh": "卷雲", "rain_prob": 10},
    "cirrostratus": {"zh": "卷層雲", "rain_prob": 20},
    "altocumulus": {"zh": "高積雲", "rain_prob": 25},
    "altostratus": {"zh": "高層雲", "rain_prob": 40},
    "cumulus": {"zh": "積雲", "rain_prob": 20},
    "stratocumulus": {"zh": "層積雲", "rain_prob": 35},
    "stratus": {"zh": "層雲", "rain_prob": 40},
    "nimbostratus": {"zh": "雨層雲", "rain_prob": 85},
    "cumulonimbus": {"zh": "積雨雲", "rain_prob": 95},
}


class CloudSkyAnalyzer:
    """
    天空雲量辨識引擎

    方法：
    1. 色彩閾值法 — 快速（無需 GPU），藍天 vs 雲分割
    2. VLM 辨識法 — 精確，使用 Ollama moondream/gemma3 辨識雲型
    """

    def __init__(self, station_id: str = "WA-001", camera_index: int = 0):
        self.station_id = station_id
        self.camera_index = camera_index

    def capture_sky(self) -> Optional[bytes]:
        """從魚眼鏡頭擷取天空影像"""
        try:
            import cv2
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                log.error(f"攝影機 {self.camera_index} 無法開啟")
                return None
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return None
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return buf.tobytes()
        except ImportError:
            log.error("cv2 未安裝: pip install opencv-python-headless")
            return None
        except Exception as e:
            log.error(f"擷取天空影像失敗: {e}")
            return None

    def analyze_color(self, image_bytes: bytes) -> CloudAnalysis:
        """
        色彩閾值法：HSV 藍天分割計算雲量

        快速、不需 GPU，適合 Pi5 即時運算
        """
        now = datetime.now().isoformat()
        try:
            import cv2
            import numpy as np

            arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # 藍天 HSV 範圍
            lower_blue = np.array([90, 40, 40])
            upper_blue = np.array([130, 255, 255])
            blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

            total_pixels = blue_mask.size
            blue_pixels = cv2.countNonZero(blue_mask)
            cloud_pct = (1 - blue_pixels / total_pixels) * 100

            # 平均亮度
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            brightness = float(np.mean(gray))

            # 簡易雲型推估
            if cloud_pct < 10:
                cloud_type = "clear"
            elif cloud_pct < 40:
                cloud_type = "cumulus"
            elif cloud_pct < 70:
                cloud_type = "stratocumulus"
            elif brightness < 100:
                cloud_type = "nimbostratus"
            else:
                cloud_type = "altostratus"

            info = CLOUD_TYPES.get(cloud_type, {"zh": "未知", "rain_prob": 30})

            return CloudAnalysis(
                timestamp=now, station_id=self.station_id,
                cloud_cover_pct=cloud_pct, cloud_type=cloud_type,
                cloud_type_zh=info["zh"], brightness=brightness,
                rain_probability=info["rain_prob"],
                description=f"色彩法: 雲量{cloud_pct:.0f}%, 亮度{brightness:.0f}",
            )
        except ImportError:
            return CloudAnalysis(
                timestamp=now, station_id=self.station_id,
                cloud_cover_pct=0, cloud_type="unknown", cloud_type_zh="未知",
                brightness=0, rain_probability=0, description="",
                valid=False, error="cv2/numpy 未安裝",
            )
        except Exception as e:
            return CloudAnalysis(
                timestamp=now, station_id=self.station_id,
                cloud_cover_pct=0, cloud_type="unknown", cloud_type_zh="未知",
                brightness=0, rain_probability=0, description="",
                valid=False, error=str(e),
            )

    def analyze_vlm(self, image_bytes: bytes) -> CloudAnalysis:
        """
        VLM 辨識法：使用 Ollama VLM 辨識雲型（更精確）

        需要 GPU，適合總機端
        """
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        now = datetime.now().isoformat()
        # 先跑色彩法取得基本數據
        color_result = self.analyze_color(image_bytes)

        try:
            import asyncio
            from tools.vision_edge_service import VisionPipeline

            pipeline = VisionPipeline()
            prompt = (
                "這是從魚眼鏡頭拍攝的天空照片。請分析：\n"
                "1. 雲量佔比（0-100%）\n"
                "2. 雲型（cumulus/stratus/cumulonimbus/cirrus/nimbostratus/clear 等）\n"
                "3. 是否有降雨跡象\n"
                "回覆 JSON: {\"cloud_pct\": 60, \"cloud_type\": \"cumulonimbus\", \"rain_likely\": true, \"description\": \"...\"}"
            )

            loop = asyncio.new_event_loop()
            ok, text, ms = loop.run_until_complete(
                pipeline.vlm_inference(image_bytes, prompt)
            )
            loop.close()

            if ok:
                # 嘗試解析 JSON
                m = re.search(r'\{.*?\}', text, re.DOTALL)
                if m:
                    data = json.loads(m.group(0))
                    cloud_type = data.get("cloud_type", color_result.cloud_type)
                    cloud_pct = data.get("cloud_pct", color_result.cloud_cover_pct)
                    info = CLOUD_TYPES.get(cloud_type, {"zh": cloud_type, "rain_prob": 30})
                    rain_prob = info["rain_prob"]
                    if data.get("rain_likely"):
                        rain_prob = max(rain_prob, 70)

                    return CloudAnalysis(
                        timestamp=now, station_id=self.station_id,
                        cloud_cover_pct=cloud_pct, cloud_type=cloud_type,
                        cloud_type_zh=info["zh"], brightness=color_result.brightness,
                        rain_probability=rain_prob,
                        description=data.get("description", text[:200]),
                    )

            # VLM 失敗，用色彩法結果
            return color_result

        except Exception as e:
            log.warning(f"VLM 雲量辨識失敗，使用色彩法: {e}")
            return color_result

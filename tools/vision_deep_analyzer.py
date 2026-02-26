#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 — 視覺深度分析引擎 (Vision Deep Analyzer)
支援圖片/影片輸入（本地上傳 + 串流 URL），精細物件計數 + 標註圖 + 結構化報告

功能：
- 圖片/影片輸入（mp4, avi, mov, mkv, webm + RTSP/HTTP 串流）
- YOLO 全物件偵測 + VLM 深度分類
- 車輛細分（大車/小車/機車/腳踏車/廠牌/顏色/車牌）
- 人員分析（人數/男女）
- 全場景物件辨識計數（樹木/路標/建築/動物/家具/電子設備…）
- 標註圖片產生（偵測框 + 標籤 + 計數）
- 結構化報告（文字 + 標註圖 + JSON）
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import re
import sys
import tempfile
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("VisionDeepAnalyzer")

# ===== 路徑 =====
ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports" / "vision_deep"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
ANNOTATED_DIR = REPORTS_DIR / "annotated"
ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)
FRAMES_DIR = REPORTS_DIR / "frames"
FRAMES_DIR.mkdir(parents=True, exist_ok=True)

# ===== 環境變數 =====
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
VLM_MODEL = os.environ.get("VLM_OLLAMA_MODEL", "moondream")

# ===== YOLO COCO 80 類別中文映射 =====
COCO_CLASSES_ZH = {
    "person": "人", "bicycle": "腳踏車", "car": "小客車", "motorcycle": "機車",
    "airplane": "飛機", "bus": "公車", "train": "火車", "truck": "卡車",
    "boat": "船", "traffic light": "紅綠燈", "fire hydrant": "消防栓",
    "stop sign": "停止標誌", "parking meter": "停車計費器", "bench": "長椅",
    "bird": "鳥", "cat": "貓", "dog": "狗", "horse": "馬", "sheep": "羊",
    "cow": "牛", "elephant": "大象", "bear": "熊", "zebra": "斑馬",
    "giraffe": "長頸鹿", "backpack": "背包", "umbrella": "雨傘",
    "handbag": "手提包", "tie": "領帶", "suitcase": "行李箱",
    "frisbee": "飛盤", "skis": "滑雪板", "snowboard": "滑雪板",
    "sports ball": "球", "kite": "風箏", "baseball bat": "棒球棒",
    "baseball glove": "棒球手套", "skateboard": "滑板", "surfboard": "衝浪板",
    "tennis racket": "網球拍", "bottle": "瓶子", "wine glass": "酒杯",
    "cup": "杯子", "fork": "叉子", "knife": "刀", "spoon": "湯匙",
    "bowl": "碗", "banana": "香蕉", "apple": "蘋果", "sandwich": "三明治",
    "orange": "橘子", "broccoli": "花椰菜", "carrot": "胡蘿蔔",
    "hot dog": "熱狗", "pizza": "披薩", "donut": "甜甜圈", "cake": "蛋糕",
    "chair": "椅子", "couch": "沙發", "potted plant": "盆栽",
    "bed": "床", "dining table": "餐桌", "toilet": "馬桶", "tv": "電視",
    "laptop": "筆電", "mouse": "滑鼠", "remote": "遙控器",
    "keyboard": "鍵盤", "cell phone": "手機", "microwave": "微波爐",
    "oven": "烤箱", "toaster": "烤麵包機", "sink": "水槽",
    "refrigerator": "冰箱", "book": "書", "clock": "時鐘", "vase": "花瓶",
    "scissors": "剪刀", "teddy bear": "泰迪熊", "hair drier": "吹風機",
    "toothbrush": "牙刷",
}

# 車輛類別群組
VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle"}
VEHICLE_ZH_MAP = {
    "car": "小客車", "truck": "卡車/大車", "bus": "公車/大車",
    "motorcycle": "機車", "bicycle": "腳踏車",
}
LARGE_VEHICLE = {"truck", "bus"}
SMALL_VEHICLE = {"car"}
TWO_WHEEL = {"motorcycle", "bicycle"}

# 人員類別
PERSON_CLASSES = {"person"}

# 自然/環境物件（VLM 補充辨識用）
NATURE_KEYWORDS = ["tree", "bush", "flower", "grass", "rock", "mountain", "river",
                   "cloud", "sky", "sun", "moon", "star", "lake", "ocean", "hill",
                   "樹", "花", "草", "石", "山", "河", "雲", "天空"]

# =====================================================================
# 資料結構
# =====================================================================

@dataclass
class DetectedObject:
    """單一偵測物件"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    class_name: str = ""        # YOLO 原始類別
    class_zh: str = ""          # 中文名稱
    confidence: float = 0.0
    bbox: list = field(default_factory=list)  # [x1, y1, x2, y2]
    # 深度屬性（VLM 補充）
    color: str = ""             # 顏色
    subtype: str = ""           # 子類型（如：轎車/SUV/貨車）
    brand: str = ""             # 廠牌
    license_plate: str = ""     # 車牌
    gender: str = ""            # 性別（人員）
    additional: dict = field(default_factory=dict)


@dataclass
class FrameAnalysis:
    """單幀分析結果"""
    frame_index: int = 0
    timestamp_sec: float = 0.0
    image_path: str = ""
    annotated_path: str = ""
    objects: list[DetectedObject] = field(default_factory=list)
    object_counts: dict = field(default_factory=dict)
    vlm_description: str = ""
    vlm_extra_objects: list = field(default_factory=list)  # VLM 發現但 YOLO 未偵測的


@dataclass
class DeepAnalysisReport:
    """完整深度分析報告"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_type: str = ""       # image, video, stream
    source_name: str = ""
    duration_sec: float = 0.0   # 影片長度
    total_frames: int = 0       # 總幀數
    analyzed_frames: int = 0    # 分析幀數
    processing_ms: float = 0.0
    # 彙整統計
    summary: dict = field(default_factory=dict)
    vehicle_summary: dict = field(default_factory=dict)
    person_summary: dict = field(default_factory=dict)
    scene_objects: dict = field(default_factory=dict)
    # 幀分析
    frame_analyses: list[FrameAnalysis] = field(default_factory=list)
    # 報告路徑
    report_text_path: str = ""
    report_json_path: str = ""
    annotated_images: list = field(default_factory=list)
    # VLM 場景總結
    scene_description: str = ""
    # 原始資料
    all_detections_flat: list = field(default_factory=list)


# =====================================================================
# 核心引擎
# =====================================================================

class VisionDeepAnalyzer:
    """視覺深度分析引擎"""

    def __init__(self):
        self._yolo_model = None
        self._yolo_loaded = False
        self._import_deps()

    def _import_deps(self):
        """延遲匯入依賴"""
        self._httpx = None
        self._cv2 = None
        self._Image = None
        self._ImageDraw = None
        self._ImageFont = None
        self._np = None
        try:
            import httpx
            self._httpx = httpx
        except ImportError:
            pass
        try:
            import cv2
            self._cv2 = cv2
        except ImportError:
            pass
        try:
            from PIL import Image, ImageDraw, ImageFont
            self._Image = Image
            self._ImageDraw = ImageDraw
            self._ImageFont = ImageFont
        except ImportError:
            pass
        try:
            import numpy as np
            self._np = np
        except ImportError:
            pass

    # ── YOLO ────────────────────────────────────────────

    def load_yolo(self, model_path: str = "") -> bool:
        """載入 YOLO 模型（預設 yolov8n.pt，自動下載）"""
        path = model_path or os.environ.get("YOLO_MODEL_PATH", "") or "yolov8n.pt"
        try:
            import importlib
            # 清除可能的快取失敗
            if "ultralytics" not in sys.modules:
                try:
                    import ultralytics
                except ImportError:
                    pass
            mod = importlib.import_module("ultralytics")
            YOLO = getattr(mod, "YOLO")
            self._yolo_model = YOLO(path)
            self._yolo_loaded = True
            log.info(f"YOLO 模型已載入: {path}")
            return True
        except (ImportError, ModuleNotFoundError) as e:
            log.warning(f"ultralytics 未安裝（{e}）。pip install ultralytics")
            return False
        except Exception as e:
            log.warning(f"YOLO 載入失敗: {e}")
            return False

    def yolo_detect(self, image_bytes: bytes, conf: float = 0.25) -> list[DetectedObject]:
        """YOLO 偵測 → DetectedObject 列表"""
        if not self._yolo_loaded or not self._yolo_model:
            return []
        np = self._np
        cv2 = self._cv2
        Image = self._Image
        if not np:
            return []
        try:
            if cv2:
                arr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            else:
                pil_img = Image.open(io.BytesIO(image_bytes))
                img = np.array(pil_img)

            results = self._yolo_model(img, conf=conf, verbose=False)
            objects = []
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = r.names.get(cls_id, str(cls_id))
                    c = float(box.conf[0])
                    x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                    objects.append(DetectedObject(
                        class_name=cls_name,
                        class_zh=COCO_CLASSES_ZH.get(cls_name, cls_name),
                        confidence=round(c, 3),
                        bbox=[round(x1), round(y1), round(x2), round(y2)],
                    ))
            return objects
        except Exception as e:
            log.error(f"YOLO 偵測錯誤: {e}")
            return []

    # ── VLM 推理 ────────────────────────────────────────

    async def _vlm_call(self, image_bytes: bytes, prompt: str, model: str = "") -> tuple[bool, str, float]:
        """呼叫 Ollama VLM"""
        httpx = self._httpx
        if not httpx:
            return False, "httpx not installed", 0
        model = model or VLM_MODEL
        b64 = base64.b64encode(image_bytes).decode("ascii")
        bases = []
        for raw in [
            os.environ.get("VLM_OLLAMA_BASE_URL", ""),
            OLLAMA_BASE_URL,
            "http://127.0.0.1:11460",
            "http://127.0.0.1:11434",
        ]:
            s = str(raw or "").strip().rstrip("/")
            if s and s not in bases:
                bases.append(s)

        t0 = time.perf_counter()
        for base in bases:
            try:
                async with httpx.AsyncClient(timeout=180) as c:
                    r = await c.post(f"{base}/api/generate", json={
                        "model": model, "prompt": prompt,
                        "images": [b64], "stream": False,
                    })
                    if r.status_code == 200:
                        ans = r.json().get("response", "").strip()
                        if ans:
                            ms = (time.perf_counter() - t0) * 1000
                            return True, ans, ms
            except Exception:
                continue
        ms = (time.perf_counter() - t0) * 1000
        return False, "VLM unreachable", ms

    async def _vlm_call_gemini(self, image_bytes: bytes, prompt: str) -> tuple[bool, str, float]:
        """Gemini Vision 備援"""
        httpx = self._httpx
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key or not httpx:
            return False, "Gemini not available", 0
        b64 = base64.b64encode(image_bytes).decode("ascii")
        model = os.environ.get("GEMINI_VISION_MODEL", "gemini-1.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(url, json={
                    "contents": [{"parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/png", "data": b64}},
                    ]}]
                })
                if r.status_code == 200:
                    text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    ms = (time.perf_counter() - t0) * 1000
                    return True, text, ms
        except Exception:
            pass
        return False, "Gemini failed", (time.perf_counter() - t0) * 1000

    async def vlm_analyze(self, image_bytes: bytes, prompt: str, model: str = "") -> tuple[bool, str, float]:
        """VLM 分析（自動降級：Ollama → Gemini）"""
        ok, text, ms = await self._vlm_call(image_bytes, prompt, model)
        if ok:
            return ok, text, ms
        ok2, text2, ms2 = await self._vlm_call_gemini(image_bytes, prompt)
        return ok2, text2, ms + ms2

    # ── 影片處理 ────────────────────────────────────────

    def extract_frames(
        self,
        video_source: str | bytes,
        max_frames: int = 10,
        interval_sec: float = 0,
        is_bytes: bool = False,
    ) -> list[tuple[int, float, bytes]]:
        """
        從影片提取關鍵幀
        Returns: [(frame_index, timestamp_sec, image_bytes), ...]
        """
        cv2 = self._cv2
        np = self._np
        if not cv2 or not np:
            log.warning("cv2/numpy 未安裝，無法處理影片")
            return []

        # 如果是 bytes，先寫入暫存檔
        tmp_path = None
        if is_bytes:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            tmp.write(video_source)
            tmp.close()
            tmp_path = tmp.name
            video_source = tmp_path

        try:
            cap = cv2.VideoCapture(video_source)
            if not cap.isOpened():
                log.error(f"無法開啟影片: {video_source}")
                return []

            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0

            # 計算抽幀間隔
            if interval_sec > 0:
                frame_interval = max(1, int(fps * interval_sec))
            elif total_frames > 0:
                frame_interval = max(1, total_frames // max_frames)
            else:
                frame_interval = max(1, int(fps * 2))  # 預設每 2 秒

            frames = []
            idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if idx % frame_interval == 0 and len(frames) < max_frames:
                    ts = idx / fps if fps > 0 else 0
                    _, buf = cv2.imencode(".png", frame)
                    frames.append((idx, ts, buf.tobytes()))
                idx += 1

            cap.release()
            log.info(f"影片抽幀完成: {len(frames)}/{total_frames} 幀, {duration:.1f}s")
            return frames
        except Exception as e:
            log.error(f"影片處理錯誤: {e}")
            return []
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    async def download_video(self, url: str) -> bytes | None:
        """下載串流影片/圖片"""
        httpx = self._httpx
        if not httpx:
            return None
        try:
            async with httpx.AsyncClient(timeout=120, follow_redirects=True) as c:
                r = await c.get(url)
                if r.status_code == 200:
                    return r.content
        except Exception as e:
            log.error(f"下載失敗: {e}")
        return None

    # ── 標註圖片 ────────────────────────────────────────

    def draw_annotations(
        self,
        image_bytes: bytes,
        objects: list[DetectedObject],
        show_labels: bool = True,
        show_counts: bool = True,
    ) -> bytes:
        """在圖片上繪製偵測框 + 標籤 + 計數統計"""
        Image = self._Image
        ImageDraw = self._ImageDraw
        ImageFont = self._ImageFont
        if not Image or not ImageDraw:
            return image_bytes

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        draw = ImageDraw.Draw(img)

        # 顏色映射
        color_map = {
            "person": "#FF6B6B", "car": "#4ECDC4", "truck": "#45B7D1",
            "bus": "#96CEB4", "motorcycle": "#FFEAA7", "bicycle": "#DDA0DD",
            "bird": "#98D8C8", "cat": "#F7DC6F", "dog": "#BB8FCE",
        }
        default_color = "#74B9FF"

        # 嘗試載入字體
        font = None
        font_small = None
        try:
            # 嘗試系統中文字體
            for fp in [
                "C:/Windows/Fonts/msjh.ttc",      # 微軟正黑體
                "C:/Windows/Fonts/msyh.ttc",       # 微軟雅黑
                "C:/Windows/Fonts/arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]:
                if os.path.exists(fp):
                    font = ImageFont.truetype(fp, 16)
                    font_small = ImageFont.truetype(fp, 12)
                    break
        except Exception:
            pass

        # 繪製偵測框
        for obj in objects:
            if not obj.bbox or len(obj.bbox) < 4:
                continue
            x1, y1, x2, y2 = obj.bbox
            color = color_map.get(obj.class_name, default_color)

            # 框
            draw.rectangle([x1, y1, x2, y2], outline=color, width=2)

            if show_labels:
                # 標籤文字
                label_parts = [obj.class_zh or obj.class_name]
                if obj.color:
                    label_parts.append(obj.color)
                if obj.subtype:
                    label_parts.append(obj.subtype)
                if obj.brand:
                    label_parts.append(obj.brand)
                if obj.license_plate:
                    label_parts.append(f"車牌:{obj.license_plate}")
                if obj.gender:
                    label_parts.append(obj.gender)
                label = " ".join(label_parts)
                conf_text = f" {obj.confidence:.0%}"
                full_label = label + conf_text

                # 標籤背景
                f = font or ImageFont.load_default()
                bbox_text = draw.textbbox((x1, y1 - 20), full_label, font=f)
                draw.rectangle([bbox_text[0] - 2, bbox_text[1] - 2, bbox_text[2] + 2, bbox_text[3] + 2],
                               fill=color)
                draw.text((x1, y1 - 20), full_label, fill="black", font=f)

        # 右上角計數統計
        if show_counts and objects:
            counts = Counter(obj.class_zh or obj.class_name for obj in objects)
            stats_lines = [f"偵測物件總數: {len(objects)}"]
            for cls, cnt in counts.most_common(15):
                stats_lines.append(f"  {cls}: {cnt}")

            f = font_small or ImageFont.load_default()
            # 計算統計區域大小
            line_h = 18
            max_w = max(draw.textlength(line, font=f) for line in stats_lines) + 20
            box_h = len(stats_lines) * line_h + 10
            sx = img.width - max_w - 10
            sy = 10

            # 半透明背景
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle([sx, sy, sx + max_w, sy + box_h], fill=(0, 0, 0, 160))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)

            for i, line in enumerate(stats_lines):
                color_text = "#FFFFFF" if i == 0 else "#E0E0E0"
                draw.text((sx + 8, sy + 5 + i * line_h), line, fill=color_text, font=f)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    # ── VLM 深度分類 ────────────────────────────────────

    async def enrich_with_vlm(
        self,
        image_bytes: bytes,
        objects: list[DetectedObject],
    ) -> tuple[list[DetectedObject], str, list[str]]:
        """
        用 VLM 對 YOLO 偵測結果做深度分類：
        - 車輛：顏色、子類型、廠牌、車牌
        - 人員：性別
        - 全場景：VLM 補充 YOLO 未偵測到的物件
        Returns: (enriched_objects, scene_description, extra_objects)
        """
        # 統計 YOLO 偵測結果
        yolo_summary_parts = []
        vehicle_count = sum(1 for o in objects if o.class_name in VEHICLE_CLASSES)
        person_count = sum(1 for o in objects if o.class_name in PERSON_CLASSES)
        other_counts = Counter(o.class_zh for o in objects
                               if o.class_name not in VEHICLE_CLASSES and o.class_name not in PERSON_CLASSES)

        if vehicle_count:
            v_detail = Counter(o.class_zh for o in objects if o.class_name in VEHICLE_CLASSES)
            yolo_summary_parts.append(f"車輛 {vehicle_count} 台: " + ", ".join(f"{k}{v}台" for k, v in v_detail.items()))
        if person_count:
            yolo_summary_parts.append(f"人員 {person_count} 名")
        for cls, cnt in other_counts.most_common(10):
            yolo_summary_parts.append(f"{cls} {cnt}")

        yolo_summary = "; ".join(yolo_summary_parts) if yolo_summary_parts else "YOLO 未偵測到物件"

        prompt = (
            "你是專業的視覺分析 AI。我已用 YOLO 偵測到以下物件：\n"
            f"{yolo_summary}\n\n"
            "請仔細觀察這張圖片，完成以下任務並輸出 JSON：\n"
            "1. 【車輛詳細】每台車的顏色、類型（轎車/SUV/貨車/卡車/公車/機車/腳踏車）、"
            "如果看得出廠牌請標註、如果看得到車牌請辨識\n"
            "2. 【人員詳細】每個人的性別（男/女/不確定）\n"
            "3. 【全場景物件】列出畫面中所有可見物件（包含 YOLO 未偵測到的），"
            "例如：樹木、路燈、路標、建築物、天空、道路、圍欄、垃圾桶、花草等，"
            "每種物件標註數量\n"
            "4. 【場景描述】用 2-3 句話描述整個場景\n\n"
            "輸出格式（嚴格 JSON）：\n"
            "{\n"
            '  "vehicles": [{"index": 0, "color": "白色", "type": "轎車", "brand": "", "plate": ""}],\n'
            '  "persons": [{"index": 0, "gender": "男"}],\n'
            '  "scene_objects": {"樹木": 3, "路燈": 2, "建築物": 1, "道路": 1},\n'
            '  "scene_description": "這是一個...的場景"\n'
            "}"
        )

        ok, text, ms = await self.vlm_analyze(image_bytes, prompt)
        extra_objects = []
        scene_desc = ""

        if ok:
            parsed = self._parse_json(text)

            # 豐富車輛資訊
            vehicles_info = parsed.get("vehicles", [])
            vehicle_objs = [o for o in objects if o.class_name in VEHICLE_CLASSES]
            for i, vobj in enumerate(vehicle_objs):
                if i < len(vehicles_info):
                    vi = vehicles_info[i]
                    vobj.color = str(vi.get("color", ""))
                    vobj.subtype = str(vi.get("type", ""))
                    vobj.brand = str(vi.get("brand", ""))
                    vobj.license_plate = str(vi.get("plate", ""))

            # 豐富人員資訊
            persons_info = parsed.get("persons", [])
            person_objs = [o for o in objects if o.class_name in PERSON_CLASSES]
            for i, pobj in enumerate(person_objs):
                if i < len(persons_info):
                    pi = persons_info[i]
                    pobj.gender = str(pi.get("gender", ""))

            # 全場景物件（VLM 補充）
            scene_objs = parsed.get("scene_objects", {})
            if isinstance(scene_objs, dict):
                yolo_classes = set(o.class_zh for o in objects)
                for obj_name, count in scene_objs.items():
                    if obj_name not in yolo_classes:
                        extra_objects.append(f"{obj_name}×{count}")

            scene_desc = str(parsed.get("scene_description", ""))

        return objects, scene_desc, extra_objects

    # ── 計數彙整 ────────────────────────────────────────

    def compute_counts(self, objects: list[DetectedObject], extra_objects: list[str] = None) -> dict:
        """計算所有物件的分類計數"""
        counts = {
            "total": len(objects),
            "by_class": {},
            "by_class_zh": {},
            "vehicles": {
                "total": 0, "large": 0, "small": 0, "two_wheel": 0,
                "by_type": {}, "by_color": {}, "by_brand": {},
                "plates": [],
            },
            "persons": {
                "total": 0, "male": 0, "female": 0, "unknown": 0,
            },
            "scene_objects": {},
        }

        for obj in objects:
            # 按類別計數
            counts["by_class"][obj.class_name] = counts["by_class"].get(obj.class_name, 0) + 1
            zh = obj.class_zh or obj.class_name
            counts["by_class_zh"][zh] = counts["by_class_zh"].get(zh, 0) + 1

            # 車輛
            if obj.class_name in VEHICLE_CLASSES:
                counts["vehicles"]["total"] += 1
                if obj.class_name in LARGE_VEHICLE:
                    counts["vehicles"]["large"] += 1
                elif obj.class_name in SMALL_VEHICLE:
                    counts["vehicles"]["small"] += 1
                elif obj.class_name in TWO_WHEEL:
                    counts["vehicles"]["two_wheel"] += 1

                vtype = obj.subtype or VEHICLE_ZH_MAP.get(obj.class_name, obj.class_zh)
                counts["vehicles"]["by_type"][vtype] = counts["vehicles"]["by_type"].get(vtype, 0) + 1
                if obj.color:
                    counts["vehicles"]["by_color"][obj.color] = counts["vehicles"]["by_color"].get(obj.color, 0) + 1
                if obj.brand:
                    counts["vehicles"]["by_brand"][obj.brand] = counts["vehicles"]["by_brand"].get(obj.brand, 0) + 1
                if obj.license_plate:
                    counts["vehicles"]["plates"].append(obj.license_plate)

            # 人員
            elif obj.class_name in PERSON_CLASSES:
                counts["persons"]["total"] += 1
                g = (obj.gender or "").strip()
                if g in ("男", "male", "男性"):
                    counts["persons"]["male"] += 1
                elif g in ("女", "female", "女性"):
                    counts["persons"]["female"] += 1
                else:
                    counts["persons"]["unknown"] += 1

            # 其他場景物件
            else:
                counts["scene_objects"][zh] = counts["scene_objects"].get(zh, 0) + 1

        # 加入 VLM 補充的場景物件
        if extra_objects:
            for item in extra_objects:
                m = re.match(r"(.+?)×(\d+)", item)
                if m:
                    name, cnt = m.group(1), int(m.group(2))
                    if name not in counts["scene_objects"]:
                        counts["scene_objects"][name] = cnt

        return counts

    # ── 報告產生 ────────────────────────────────────────

    def generate_text_report(self, report: DeepAnalysisReport) -> str:
        """產生文字報告"""
        lines = []
        lines.append("=" * 60)
        lines.append("  築未科技 — AI 視覺深度分析報告")
        lines.append("=" * 60)
        lines.append(f"報告 ID: {report.id}")
        lines.append(f"時間: {report.timestamp}")
        lines.append(f"來源: {report.source_type} — {report.source_name}")
        if report.duration_sec > 0:
            lines.append(f"影片長度: {report.duration_sec:.1f} 秒")
        lines.append(f"分析幀數: {report.analyzed_frames}")
        lines.append(f"處理耗時: {report.processing_ms:.0f} ms")
        lines.append("")

        # 場景描述
        if report.scene_description:
            lines.append("【場景描述】")
            lines.append(report.scene_description)
            lines.append("")

        s = report.summary
        lines.append(f"【偵測物件總數】{s.get('total', 0)}")
        lines.append("")

        # 車輛
        v = report.vehicle_summary
        if v.get("total", 0) > 0:
            lines.append("【車輛統計】")
            lines.append(f"  車輛總數: {v['total']}")
            lines.append(f"  大車（卡車/公車）: {v.get('large', 0)}")
            lines.append(f"  小客車: {v.get('small', 0)}")
            lines.append(f"  二輪車（機車/腳踏車）: {v.get('two_wheel', 0)}")
            if v.get("by_type"):
                lines.append(f"  車型分布: {', '.join(f'{k}={v2}' for k, v2 in v['by_type'].items())}")
            if v.get("by_color"):
                lines.append(f"  顏色分布: {', '.join(f'{k}={v2}' for k, v2 in v['by_color'].items())}")
            if v.get("by_brand"):
                lines.append(f"  廠牌分布: {', '.join(f'{k}={v2}' for k, v2 in v['by_brand'].items())}")
            if v.get("plates"):
                lines.append(f"  辨識車牌: {', '.join(v['plates'])}")
            lines.append("")

        # 人員
        p = report.person_summary
        if p.get("total", 0) > 0:
            lines.append("【人員統計】")
            lines.append(f"  人員總數: {p['total']}")
            lines.append(f"  男性: {p.get('male', 0)}")
            lines.append(f"  女性: {p.get('female', 0)}")
            lines.append(f"  未確定: {p.get('unknown', 0)}")
            lines.append("")

        # 場景物件
        so = report.scene_objects
        if so:
            lines.append("【場景物件清單】")
            for name, cnt in sorted(so.items(), key=lambda x: -x[1]):
                lines.append(f"  {name}: {cnt}")
            lines.append("")

        # 所有偵測物件明細
        if report.all_detections_flat:
            lines.append("【偵測物件明細】")
            for i, det in enumerate(report.all_detections_flat[:50]):
                parts = [f"#{i+1} {det.get('class_zh', det.get('class_name', '?'))}"]
                if det.get("color"):
                    parts.append(f"顏色:{det['color']}")
                if det.get("subtype"):
                    parts.append(f"類型:{det['subtype']}")
                if det.get("brand"):
                    parts.append(f"廠牌:{det['brand']}")
                if det.get("license_plate"):
                    parts.append(f"車牌:{det['license_plate']}")
                if det.get("gender"):
                    parts.append(f"性別:{det['gender']}")
                parts.append(f"信心:{det.get('confidence', 0):.0%}")
                lines.append(f"  {' | '.join(parts)}")
            if len(report.all_detections_flat) > 50:
                lines.append(f"  ... 共 {len(report.all_detections_flat)} 個物件")
            lines.append("")

        # 標註圖片
        if report.annotated_images:
            lines.append("【標註圖片】")
            for p in report.annotated_images:
                lines.append(f"  {p}")
            lines.append("")

        lines.append("=" * 60)
        lines.append("  報告結束")
        lines.append("=" * 60)
        return "\n".join(lines)

    # ── 主分析流程 ──────────────────────────────────────

    async def analyze_image(
        self,
        image_bytes: bytes,
        source_name: str = "upload",
        conf: float = 0.25,
        save_annotated: bool = True,
    ) -> DeepAnalysisReport:
        """分析單張圖片 — 完整流程"""
        t0 = time.perf_counter()
        report = DeepAnalysisReport(
            source_type="image",
            source_name=source_name,
            total_frames=1,
            analyzed_frames=1,
        )

        # 1. YOLO 偵測
        if not self._yolo_loaded:
            self.load_yolo()
        objects = self.yolo_detect(image_bytes, conf)
        log.info(f"YOLO 偵測: {len(objects)} 個物件")

        # 2. VLM 深度分類
        objects, scene_desc, extra_objs = await self.enrich_with_vlm(image_bytes, objects)
        report.scene_description = scene_desc
        log.info(f"VLM 豐富完成: {len(extra_objs)} 個額外物件")

        # 3. 計數
        counts = self.compute_counts(objects, extra_objs)
        report.summary = counts
        report.vehicle_summary = counts["vehicles"]
        report.person_summary = counts["persons"]
        report.scene_objects = counts["scene_objects"]
        report.all_detections_flat = [asdict(o) for o in objects]

        # 4. 標註圖片
        if save_annotated:
            annotated_bytes = self.draw_annotations(image_bytes, objects)
            ann_path = ANNOTATED_DIR / f"{report.id}_annotated.png"
            ann_path.write_bytes(annotated_bytes)
            report.annotated_images.append(str(ann_path))
            log.info(f"標註圖片已儲存: {ann_path}")

        # 5. 幀分析
        frame = FrameAnalysis(
            frame_index=0,
            objects=objects,
            object_counts=counts["by_class_zh"],
            vlm_description=scene_desc,
            vlm_extra_objects=extra_objs,
        )
        if report.annotated_images:
            frame.annotated_path = report.annotated_images[0]
        report.frame_analyses.append(frame)

        # 6. 產生報告
        report.processing_ms = round((time.perf_counter() - t0) * 1000, 1)
        text_report = self.generate_text_report(report)
        txt_path = REPORTS_DIR / f"{report.id}_report.txt"
        txt_path.write_text(text_report, encoding="utf-8")
        report.report_text_path = str(txt_path)

        json_path = REPORTS_DIR / f"{report.id}_report.json"
        json_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        report.report_json_path = str(json_path)

        log.info(f"圖片分析完成: {report.processing_ms:.0f}ms, {counts['total']} 物件")
        return report

    async def analyze_video(
        self,
        video_source: str | bytes,
        source_name: str = "video",
        max_frames: int = 10,
        interval_sec: float = 0,
        conf: float = 0.25,
        is_bytes: bool = False,
    ) -> DeepAnalysisReport:
        """分析影片 — 逐幀抽取 + 分析 + 彙整"""
        t0 = time.perf_counter()
        report = DeepAnalysisReport(
            source_type="video",
            source_name=source_name,
        )

        # 1. 抽幀
        frames = self.extract_frames(video_source, max_frames, interval_sec, is_bytes)
        if not frames:
            report.processing_ms = round((time.perf_counter() - t0) * 1000, 1)
            report.scene_description = "無法從影片中提取幀"
            return report

        report.total_frames = len(frames)
        report.analyzed_frames = len(frames)
        if frames:
            report.duration_sec = round(frames[-1][1], 1)

        if not self._yolo_loaded:
            self.load_yolo()

        # 2. 逐幀分析
        all_objects = []
        all_extra = []
        all_scene_descs = []

        for idx, ts, frame_bytes in frames:
            log.info(f"分析幀 {idx} (t={ts:.1f}s)...")

            # YOLO
            objects = self.yolo_detect(frame_bytes, conf)

            # VLM（每幀都做深度分析）
            objects, scene_desc, extra_objs = await self.enrich_with_vlm(frame_bytes, objects)

            # 標註
            annotated_bytes = self.draw_annotations(frame_bytes, objects)
            ann_path = ANNOTATED_DIR / f"{report.id}_frame{idx}.png"
            ann_path.write_bytes(annotated_bytes)
            report.annotated_images.append(str(ann_path))

            # 幀分析
            frame_counts = Counter(o.class_zh or o.class_name for o in objects)
            fa = FrameAnalysis(
                frame_index=idx,
                timestamp_sec=round(ts, 2),
                annotated_path=str(ann_path),
                objects=objects,
                object_counts=dict(frame_counts),
                vlm_description=scene_desc,
                vlm_extra_objects=extra_objs,
            )
            report.frame_analyses.append(fa)

            all_objects.extend(objects)
            all_extra.extend(extra_objs)
            if scene_desc:
                all_scene_descs.append(f"[{ts:.1f}s] {scene_desc}")

        # 3. 彙整所有幀的計數
        counts = self.compute_counts(all_objects, list(set(all_extra)))
        report.summary = counts
        report.vehicle_summary = counts["vehicles"]
        report.person_summary = counts["persons"]
        report.scene_objects = counts["scene_objects"]
        report.all_detections_flat = [asdict(o) for o in all_objects]
        report.scene_description = "\n".join(all_scene_descs) if all_scene_descs else ""

        # 4. 報告
        report.processing_ms = round((time.perf_counter() - t0) * 1000, 1)
        text_report = self.generate_text_report(report)
        txt_path = REPORTS_DIR / f"{report.id}_report.txt"
        txt_path.write_text(text_report, encoding="utf-8")
        report.report_text_path = str(txt_path)

        json_path = REPORTS_DIR / f"{report.id}_report.json"
        json_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        report.report_json_path = str(json_path)

        log.info(f"影片分析完成: {report.processing_ms:.0f}ms, {len(frames)} 幀, {counts['total']} 物件")
        return report

    async def analyze_stream_url(
        self,
        url: str,
        source_name: str = "",
        max_frames: int = 10,
        interval_sec: float = 2,
        conf: float = 0.25,
    ) -> DeepAnalysisReport:
        """分析串流 URL（下載後分析）"""
        source_name = source_name or url.split("/")[-1][:50] or "stream"

        # 判斷是圖片還是影片
        lower = url.lower()
        is_image = any(lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"))

        data = await self.download_video(url)
        if not data:
            return DeepAnalysisReport(
                source_type="stream",
                source_name=source_name,
                scene_description=f"無法下載: {url}",
            )

        if is_image:
            return await self.analyze_image(data, source_name=source_name, conf=conf)
        else:
            return await self.analyze_video(
                data, source_name=source_name,
                max_frames=max_frames, interval_sec=interval_sec,
                conf=conf, is_bytes=True,
            )

    # ── 工具 ────────────────────────────────────────────

    def _parse_json(self, text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    pass
        return {}


# =====================================================================
# 全域實例
# =====================================================================
deep_analyzer = VisionDeepAnalyzer()

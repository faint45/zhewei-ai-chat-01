#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 — AI 視覺邊緣計算服務 (Vision Edge Service)
統一入口：FastAPI on port 8015

功能模組：
1. Vision Pipeline — 圖片前處理 + VLM 推理 + YOLO 偵測 + 結構化輸出
2. 即時視覺監控 — RTSP/攝影機/定時截圖串流 + 異常偵測 + 告警
3. 施工現場 AI — 安全帽偵測、進度辨識、工地異常（YOLO + VLM 雙層）
4. 邊緣節點管理 — 整合 edge_compute.py 核心
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import platform
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

try:
    from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
except ImportError:
    raise ImportError("請安裝 fastapi: pip install fastapi uvicorn python-multipart")

try:
    import httpx
except ImportError:
    httpx = None

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    import cv2
except ImportError:
    cv2 = None

# ===== 路徑 =====
ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports" / "vision_edge"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOTS_DIR = REPORTS_DIR / "snapshots"
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
ALERTS_DIR = REPORTS_DIR / "alerts"
ALERTS_DIR.mkdir(parents=True, exist_ok=True)

# ===== 日誌 =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s [VisionEdge] %(levelname)s %(message)s")
log = logging.getLogger("VisionEdge")

# ===== 環境變數 =====
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
VLM_MODEL = os.environ.get("VLM_OLLAMA_MODEL", "moondream")
YOLO_MODEL_PATH = os.environ.get("YOLO_MODEL_PATH", "")
YOLO_DEVICE = os.environ.get("YOLO_DEVICE", "1")  # GPU1=4060Ti for YOLO
VISION_EDGE_PORT = int(os.environ.get("VISION_EDGE_PORT", "8015"))
BRAIN_SERVER_URL = os.environ.get("BRAIN_SERVER_URL", "http://localhost:8002")
CHROMADB_PATH = os.environ.get("CHROMADB_PATH", str(ROOT / "chroma_db"))


# =====================================================================
# 1. Vision Pipeline — 圖片前處理 + VLM 推理 + YOLO 偵測
# =====================================================================

class VisionProvider(str, Enum):
    OLLAMA = "ollama"
    GEMINI = "gemini"
    CLAUDE = "claude"
    AUTO = "auto"


class DetectionModel(str, Enum):
    YOLO = "yolo"
    VLM_ONLY = "vlm_only"
    HYBRID = "hybrid"  # YOLO + VLM 雙層


@dataclass
class VisionResult:
    """視覺推理結果"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = ""           # 來源（file, camera, rtsp, screenshot）
    provider: str = ""         # 推理提供者
    model: str = ""            # 模型名稱
    inference_ms: float = 0    # 推理耗時 ms
    image_path: str = ""       # 原圖路徑
    image_size: tuple = (0, 0) # 圖片尺寸
    # VLM 結果
    description: str = ""      # 場景描述
    objects: list = field(default_factory=list)  # 偵測到的物件
    anomalies: list = field(default_factory=list)  # 異常項目
    confidence: float = 0.0
    raw_response: str = ""
    # YOLO 結果
    detections: list = field(default_factory=list)  # [{class, confidence, bbox}]
    detection_count: int = 0
    # 施工現場
    safety_violations: list = field(default_factory=list)
    progress_status: str = ""
    # 元數據
    metadata: dict = field(default_factory=dict)


class VisionPipeline:
    """視覺推理管線"""

    def __init__(self):
        self._yolo_model = None
        self._yolo_loaded = False
        self._history: deque[dict] = deque(maxlen=500)
        self._stats = {"total_inferences": 0, "total_detections": 0, "avg_inference_ms": 0.0}
        self._lock = threading.Lock()

    # ----- 圖片前處理 -----
    def preprocess(self, image_bytes: bytes, max_size: int = 1280, enhance: bool = False) -> tuple[bytes, tuple[int, int]]:
        """圖片前處理：縮放、增強"""
        if not Image:
            return image_bytes, (0, 0)
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        orig_size = img.size
        # 縮放
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        # 增強（可選）
        if enhance and np is not None:
            arr = np.array(img)
            # 簡單直方圖均衡化（亮度通道）
            if len(arr.shape) == 3:
                from PIL import ImageEnhance
                img = ImageEnhance.Contrast(img).enhance(1.2)
                img = ImageEnhance.Sharpness(img).enhance(1.1)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue(), orig_size

    # ----- VLM 推理（Ollama Vision） -----
    async def vlm_inference(
        self,
        image_bytes: bytes,
        prompt: str,
        model: str = "",
        provider: str = "ollama",
    ) -> tuple[bool, str, float]:
        """
        VLM 推理
        Returns: (success, response_text, inference_ms)
        """
        model = model or VLM_MODEL
        t0 = time.perf_counter()

        if provider in ("ollama", "auto"):
            ok, text = await self._call_ollama_vision(model, prompt, image_bytes)
            ms = (time.perf_counter() - t0) * 1000
            if ok:
                return True, text, ms

        if provider in ("gemini", "auto"):
            ok, text = await self._call_gemini_vision(prompt, image_bytes)
            ms = (time.perf_counter() - t0) * 1000
            if ok:
                return True, text, ms

        if provider in ("claude", "auto"):
            ok, text = await self._call_claude_vision(prompt, image_bytes)
            ms = (time.perf_counter() - t0) * 1000
            if ok:
                return True, text, ms

        ms = (time.perf_counter() - t0) * 1000
        return False, "所有 VLM 提供者均失敗", ms

    async def _call_ollama_vision(self, model: str, prompt: str, image_bytes: bytes) -> tuple[bool, str]:
        if not httpx:
            return False, "httpx not installed"
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
        for base in bases:
            try:
                async with httpx.AsyncClient(timeout=120) as c:
                    r = await c.post(f"{base}/api/generate", json={
                        "model": model,
                        "prompt": prompt,
                        "images": [b64],
                        "stream": False,
                    })
                    if r.status_code == 200:
                        ans = r.json().get("response", "").strip()
                        if ans:
                            return True, ans
            except Exception:
                continue
        return False, "Ollama vision unreachable"

    async def _call_gemini_vision(self, prompt: str, image_bytes: bytes) -> tuple[bool, str]:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key or not httpx:
            return False, "Gemini API key not set"
        b64 = base64.b64encode(image_bytes).decode("ascii")
        model = os.environ.get("GEMINI_VISION_MODEL", "gemini-1.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(url, json={
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/png", "data": b64}}
                        ]
                    }]
                })
                if r.status_code == 200:
                    text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return True, text
        except Exception:
            pass
        return False, "Gemini vision failed"

    async def _call_claude_vision(self, prompt: str, image_bytes: bytes) -> tuple[bool, str]:
        api_key = (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY") or "").strip()
        if not api_key or not httpx:
            return False, "Claude API key not set"
        b64 = base64.b64encode(image_bytes).decode("ascii")
        model = os.environ.get("CLAUDE_VISION_MODEL", "claude-3-5-sonnet-latest")
        try:
            async with httpx.AsyncClient(timeout=120) as c:
                r = await c.post("https://api.anthropic.com/v1/messages", json={
                    "model": model,
                    "max_tokens": 2048,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                        ]
                    }]
                }, headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                })
                if r.status_code == 200:
                    content = r.json().get("content", [])
                    texts = [c["text"] for c in content if isinstance(c, dict) and c.get("type") == "text"]
                    return True, "\n".join(texts).strip()
        except Exception:
            pass
        return False, "Claude vision failed"

    # ----- YOLO 偵測 -----
    def load_yolo(self, model_path: str = "") -> bool:
        """載入 YOLO 模型（優先 TensorRT engine，fallback .pt）"""
        path = model_path or YOLO_MODEL_PATH
        if not path:
            # 優先使用 TensorRT engine（+30-50% 速度）
            trt_path = str(ROOT / "yolov8n.engine")
            pt_path = str(ROOT / "yolov8n.pt")
            if os.path.exists(trt_path):
                path = trt_path
            else:
                path = pt_path
        try:
            from ultralytics import YOLO
            self._yolo_model = YOLO(path)
            self._yolo_loaded = True
            log.info(f"YOLO 模型已載入: {path} (device={YOLO_DEVICE})")
            return True
        except ImportError:
            log.warning("ultralytics 未安裝，YOLO 偵測不可用。pip install ultralytics")
            return False
        except Exception as e:
            log.warning(f"YOLO 載入失敗: {e}")
            return False

    def yolo_detect(self, image_bytes: bytes, conf_threshold: float = 0.25) -> list[dict]:
        """YOLO 物件偵測"""
        if not self._yolo_loaded or not self._yolo_model:
            return []
        if not np:
            return []
        try:
            arr = np.frombuffer(image_bytes, np.uint8)
            if cv2:
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            else:
                pil_img = Image.open(io.BytesIO(image_bytes))
                img = np.array(pil_img)
            results = self._yolo_model(img, conf=conf_threshold, device=YOLO_DEVICE, verbose=False)
            detections = []
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = r.names.get(cls_id, str(cls_id))
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                    detections.append({
                        "class": cls_name,
                        "confidence": round(conf, 3),
                        "bbox": [round(x1), round(y1), round(x2), round(y2)],
                    })
            return detections
        except Exception as e:
            log.error(f"YOLO 偵測錯誤: {e}")
            return []

    # ----- 完整推理 Pipeline -----
    async def analyze(
        self,
        image_bytes: bytes,
        prompt: str = "",
        source: str = "upload",
        mode: str = "hybrid",  # vlm_only, yolo, hybrid
        provider: str = "auto",
        model: str = "",
        conf_threshold: float = 0.25,
        enhance: bool = False,
        save_image: bool = True,
        metadata: dict = None,
    ) -> VisionResult:
        """
        完整視覺分析 Pipeline
        1. 前處理
        2. YOLO 偵測（如啟用）
        3. VLM 推理（如啟用）
        4. 結構化輸出
        """
        result = VisionResult(source=source, metadata=metadata or {})
        t0 = time.perf_counter()

        # 前處理
        processed_bytes, orig_size = self.preprocess(image_bytes, enhance=enhance)
        result.image_size = orig_size

        # 儲存原圖
        if save_image:
            img_path = SNAPSHOTS_DIR / f"{result.id}.png"
            img_path.write_bytes(processed_bytes)
            result.image_path = str(img_path)

        # YOLO 偵測
        if mode in ("yolo", "hybrid"):
            detections = self.yolo_detect(processed_bytes, conf_threshold)
            result.detections = detections
            result.detection_count = len(detections)

        # VLM 推理
        if mode in ("vlm_only", "hybrid"):
            if not prompt:
                prompt = self._build_analysis_prompt(result.detections if mode == "hybrid" else [])
            ok, text, ms = await self.vlm_inference(processed_bytes, prompt, model, provider)
            result.provider = provider
            result.model = model or VLM_MODEL
            result.inference_ms = ms
            if ok:
                result.raw_response = text
                self._parse_vlm_response(text, result)
                result.confidence = max(result.confidence, 0.5)
            else:
                result.raw_response = text
                result.confidence = 0.1 if result.detections else 0.0

        total_ms = (time.perf_counter() - t0) * 1000
        result.inference_ms = round(total_ms, 1)

        # 更新統計
        with self._lock:
            self._stats["total_inferences"] += 1
            self._stats["total_detections"] += result.detection_count
            n = self._stats["total_inferences"]
            self._stats["avg_inference_ms"] = round(
                (self._stats["avg_inference_ms"] * (n - 1) + total_ms) / n, 1
            )
            self._history.appendleft(asdict(result))

        return result

    def _build_analysis_prompt(self, yolo_detections: list) -> str:
        """建構分析 prompt"""
        base = (
            "你是 AI 視覺分析助理。請詳細分析這張圖片，輸出 JSON 格式：\n"
            "{\n"
            '  "description": "場景描述",\n'
            '  "objects": ["物件1", "物件2"],\n'
            '  "anomalies": ["異常1"],\n'
            '  "confidence": 0.0~1.0,\n'
            '  "safety_issues": ["安全問題"],\n'
            '  "progress": "施工進度描述（若為工地場景）"\n'
            "}\n"
        )
        if yolo_detections:
            det_summary = ", ".join([f"{d['class']}({d['confidence']:.0%})" for d in yolo_detections[:10]])
            base += f"\nYOLO 已偵測到：{det_summary}。請結合這些偵測結果做更深入分析。"
        return base

    def _parse_vlm_response(self, text: str, result: VisionResult):
        """解析 VLM 回應"""
        import re
        # 嘗試提取 JSON
        try:
            obj = json.loads(text)
        except Exception:
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                try:
                    obj = json.loads(m.group(0))
                except Exception:
                    obj = {}
            else:
                obj = {}

        if isinstance(obj, dict):
            result.description = str(obj.get("description", ""))[:1000]
            result.objects = obj.get("objects", []) if isinstance(obj.get("objects"), list) else []
            result.anomalies = obj.get("anomalies", []) if isinstance(obj.get("anomalies"), list) else []
            result.confidence = float(obj.get("confidence", 0.5))
            result.safety_violations = obj.get("safety_issues", []) if isinstance(obj.get("safety_issues"), list) else []
            result.progress_status = str(obj.get("progress", ""))[:500]
        else:
            result.description = text[:1000]
            result.confidence = 0.4

    def get_stats(self) -> dict:
        with self._lock:
            return {**self._stats, "history_size": len(self._history)}

    def get_history(self, limit: int = 20) -> list[dict]:
        with self._lock:
            return list(self._history)[:limit]


# =====================================================================
# 2. 即時視覺監控 — RTSP/攝影機/定時截圖 + 異常偵測 + 告警
# =====================================================================

class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MonitorSource:
    """監控來源"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    type: str = "screenshot"  # screenshot, rtsp, camera, url
    url: str = ""             # RTSP URL 或圖片 URL
    camera_id: int = 0        # 攝影機 ID
    interval_sec: int = 30    # 擷取間隔
    enabled: bool = True
    analysis_mode: str = "hybrid"  # vlm_only, yolo, hybrid
    alert_rules: list = field(default_factory=list)  # 告警規則
    last_capture: str = ""
    last_result: dict = field(default_factory=dict)


@dataclass
class Alert:
    """告警"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_id: str = ""
    source_name: str = ""
    level: str = "warning"
    category: str = ""        # safety, anomaly, progress, custom
    message: str = ""
    image_path: str = ""
    details: dict = field(default_factory=dict)
    acknowledged: bool = False


class VisionMonitor:
    """即時視覺監控管理器"""

    def __init__(self, pipeline: VisionPipeline):
        self.pipeline = pipeline
        self.sources: dict[str, MonitorSource] = {}
        self.alerts: deque[Alert] = deque(maxlen=200)
        self._running = False
        self._tasks: dict[str, asyncio.Task] = {}
        self._ws_clients: list[WebSocket] = []
        self._lock = threading.Lock()

    def add_source(self, source: MonitorSource) -> str:
        self.sources[source.id] = source
        log.info(f"監控來源已新增: {source.name} ({source.type})")
        return source.id

    def remove_source(self, source_id: str) -> bool:
        if source_id in self.sources:
            self.sources[source_id].enabled = False
            if source_id in self._tasks:
                self._tasks[source_id].cancel()
            del self.sources[source_id]
            return True
        return False

    async def start(self):
        """啟動所有監控來源"""
        self._running = True
        for sid, source in self.sources.items():
            if source.enabled and sid not in self._tasks:
                self._tasks[sid] = asyncio.create_task(self._monitor_loop(source))
        log.info(f"視覺監控已啟動，{len(self._tasks)} 個來源")

    async def stop(self):
        """停止所有監控"""
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()
        log.info("視覺監控已停止")

    async def _monitor_loop(self, source: MonitorSource):
        """單一來源監控迴圈"""
        while self._running and source.enabled:
            try:
                image_bytes = await self._capture(source)
                if image_bytes:
                    result = await self.pipeline.analyze(
                        image_bytes=image_bytes,
                        source=f"monitor:{source.name}",
                        mode=source.analysis_mode,
                        save_image=True,
                    )
                    source.last_capture = result.timestamp
                    source.last_result = asdict(result)

                    # 檢查告警規則
                    await self._check_alerts(source, result)

                    # 推送 WebSocket
                    await self._broadcast({
                        "type": "monitor_update",
                        "source_id": source.id,
                        "source_name": source.name,
                        "result": asdict(result),
                    })
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"監控 {source.name} 錯誤: {e}")

            await asyncio.sleep(source.interval_sec)

    async def _capture(self, source: MonitorSource) -> bytes | None:
        """從來源擷取圖片"""
        if source.type == "screenshot":
            return self._capture_screenshot()
        elif source.type == "rtsp" and source.url:
            return self._capture_rtsp(source.url)
        elif source.type == "camera":
            return self._capture_camera(source.camera_id)
        elif source.type == "url" and source.url:
            return await self._capture_url(source.url)
        return None

    def _capture_screenshot(self) -> bytes | None:
        """截取螢幕"""
        try:
            import pyautogui
            img = pyautogui.screenshot()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception as e:
            log.warning(f"截圖失敗: {e}")
            return None

    def _capture_rtsp(self, url: str) -> bytes | None:
        """從 RTSP 串流擷取一幀"""
        if not cv2:
            log.warning("cv2 未安裝，無法擷取 RTSP")
            return None
        try:
            cap = cv2.VideoCapture(url)
            ret, frame = cap.read()
            cap.release()
            if ret:
                _, buf = cv2.imencode(".png", frame)
                return buf.tobytes()
        except Exception as e:
            log.warning(f"RTSP 擷取失敗: {e}")
        return None

    def _capture_camera(self, camera_id: int = 0) -> bytes | None:
        """從本地攝影機擷取"""
        if not cv2:
            return None
        try:
            cap = cv2.VideoCapture(camera_id)
            ret, frame = cap.read()
            cap.release()
            if ret:
                _, buf = cv2.imencode(".png", frame)
                return buf.tobytes()
        except Exception:
            pass
        return None

    async def _capture_url(self, url: str) -> bytes | None:
        """從 URL 下載圖片"""
        if not httpx:
            return None
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(url)
                if r.status_code == 200:
                    return r.content
        except Exception:
            pass
        return None

    async def _check_alerts(self, source: MonitorSource, result: VisionResult):
        """檢查告警規則"""
        # 安全違規告警
        if result.safety_violations:
            alert = Alert(
                source_id=source.id,
                source_name=source.name,
                level=AlertLevel.CRITICAL,
                category="safety",
                message=f"安全違規偵測: {', '.join(result.safety_violations[:3])}",
                image_path=result.image_path,
                details={"violations": result.safety_violations},
            )
            self.alerts.appendleft(alert)
            await self._broadcast({"type": "alert", "alert": asdict(alert)})
            self._save_alert(alert)

        # 異常告警
        if result.anomalies:
            alert = Alert(
                source_id=source.id,
                source_name=source.name,
                level=AlertLevel.WARNING,
                category="anomaly",
                message=f"異常偵測: {', '.join(result.anomalies[:3])}",
                image_path=result.image_path,
                details={"anomalies": result.anomalies},
            )
            self.alerts.appendleft(alert)
            await self._broadcast({"type": "alert", "alert": asdict(alert)})
            self._save_alert(alert)

        # 自訂規則
        for rule in source.alert_rules:
            if self._evaluate_rule(rule, result):
                alert = Alert(
                    source_id=source.id,
                    source_name=source.name,
                    level=rule.get("level", "warning"),
                    category="custom",
                    message=rule.get("message", "自訂規則觸發"),
                    image_path=result.image_path,
                    details={"rule": rule, "trigger_value": rule.get("field", "")},
                )
                self.alerts.appendleft(alert)
                await self._broadcast({"type": "alert", "alert": asdict(alert)})

    def _evaluate_rule(self, rule: dict, result: VisionResult) -> bool:
        """評估自訂告警規則"""
        field_name = rule.get("field", "")
        operator = rule.get("operator", "contains")
        value = rule.get("value", "")

        actual = getattr(result, field_name, None)
        if actual is None:
            return False

        if operator == "contains" and isinstance(actual, str):
            return value.lower() in actual.lower()
        elif operator == "gt" and isinstance(actual, (int, float)):
            return actual > float(value)
        elif operator == "lt" and isinstance(actual, (int, float)):
            return actual < float(value)
        elif operator == "eq":
            return str(actual) == str(value)
        elif operator == "class_detected" and isinstance(actual, list):
            return any(d.get("class") == value for d in actual if isinstance(d, dict))
        return False

    def _save_alert(self, alert: Alert):
        """儲存告警到檔案"""
        try:
            path = ALERTS_DIR / f"{alert.id}.json"
            path.write_text(json.dumps(asdict(alert), ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    async def _broadcast(self, data: dict):
        """推送到所有 WebSocket 客戶端"""
        dead = []
        for ws in self._ws_clients:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._ws_clients.remove(ws)

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "sources": {sid: {
                "name": s.name,
                "type": s.type,
                "enabled": s.enabled,
                "interval_sec": s.interval_sec,
                "last_capture": s.last_capture,
                "analysis_mode": s.analysis_mode,
            } for sid, s in self.sources.items()},
            "active_tasks": len(self._tasks),
            "total_alerts": len(self.alerts),
            "ws_clients": len(self._ws_clients),
        }

    def get_alerts(self, limit: int = 50, level: str = "") -> list[dict]:
        alerts = list(self.alerts)
        if level:
            alerts = [a for a in alerts if a.level == level]
        return [asdict(a) for a in alerts[:limit]]


# =====================================================================
# 3. 施工現場 AI — 安全帽偵測、進度辨識、工地異常
# =====================================================================

class ConstructionAI:
    """施工現場 AI 分析"""

    # 施工安全相關 YOLO 類別
    SAFETY_CLASSES = {
        "person": "人員",
        "hard hat": "安全帽",
        "safety vest": "反光背心",
        "no hard hat": "未戴安全帽",
        "no safety vest": "未穿反光背心",
    }

    CONSTRUCTION_PROMPTS = {
        "safety_check": (
            "你是施工安全 AI 檢查員。請分析這張工地照片：\n"
            "1. 所有人員是否都戴安全帽？\n"
            "2. 是否穿著反光背心？\n"
            "3. 有無其他安全隱患（高空作業無安全繩、未設圍欄等）？\n"
            "輸出 JSON：\n"
            '{"total_workers": 0, "with_helmet": 0, "without_helmet": 0, '
            '"safety_issues": ["問題1"], "risk_level": "low|medium|high|critical", '
            '"recommendations": ["建議1"]}'
        ),
        "progress_check": (
            "你是施工進度 AI 分析師。請分析這張工地照片：\n"
            "1. 目前施工階段（基礎/結構/裝修/完工）\n"
            "2. 可見的施工項目\n"
            "3. 預估完成度\n"
            "輸出 JSON：\n"
            '{"stage": "", "visible_work": ["項目1"], "completion_pct": 0, '
            '"notes": "備註"}'
        ),
        "anomaly_check": (
            "你是工地異常偵測 AI。請分析這張工地照片：\n"
            "1. 是否有結構裂縫、滲水、傾斜？\n"
            "2. 材料堆放是否安全？\n"
            "3. 機具是否正常？\n"
            "輸出 JSON：\n"
            '{"anomalies": [{"type": "", "severity": "low|medium|high", "location": "", "description": ""}], '
            '"overall_status": "normal|attention|danger"}'
        ),
    }

    def __init__(self, pipeline: VisionPipeline):
        self.pipeline = pipeline

    async def safety_check(self, image_bytes: bytes, provider: str = "auto") -> dict:
        """安全帽 + 反光背心 + 安全隱患檢查"""
        # YOLO 偵測
        detections = self.pipeline.yolo_detect(image_bytes)
        person_count = sum(1 for d in detections if d["class"] == "person")

        # VLM 深度分析
        prompt = self.CONSTRUCTION_PROMPTS["safety_check"]
        if detections:
            det_summary = ", ".join([f"{d['class']}({d['confidence']:.0%})" for d in detections[:15]])
            prompt += f"\n\nYOLO 偵測結果：{det_summary}"

        ok, text, ms = await self.pipeline.vlm_inference(image_bytes, prompt, provider=provider)
        result = {
            "type": "safety_check",
            "yolo_detections": detections,
            "person_count_yolo": person_count,
            "inference_ms": round(ms, 1),
            "provider": provider,
        }

        if ok:
            parsed = self._parse_json(text)
            result.update(parsed)
            result["raw_response"] = text[:2000]
        else:
            result["error"] = text
            result["risk_level"] = "unknown"

        return result

    async def progress_check(self, image_bytes: bytes, provider: str = "auto") -> dict:
        """施工進度分析"""
        prompt = self.CONSTRUCTION_PROMPTS["progress_check"]
        ok, text, ms = await self.pipeline.vlm_inference(image_bytes, prompt, provider=provider)
        result = {"type": "progress_check", "inference_ms": round(ms, 1)}
        if ok:
            parsed = self._parse_json(text)
            result.update(parsed)
            result["raw_response"] = text[:2000]
        else:
            result["error"] = text
        return result

    async def anomaly_check(self, image_bytes: bytes, provider: str = "auto") -> dict:
        """工地異常偵測"""
        # YOLO 偵測
        detections = self.pipeline.yolo_detect(image_bytes)

        prompt = self.CONSTRUCTION_PROMPTS["anomaly_check"]
        if detections:
            det_summary = ", ".join([f"{d['class']}({d['confidence']:.0%})" for d in detections[:15]])
            prompt += f"\n\nYOLO 偵測結果：{det_summary}"

        ok, text, ms = await self.pipeline.vlm_inference(image_bytes, prompt, provider=provider)
        result = {
            "type": "anomaly_check",
            "yolo_detections": detections,
            "inference_ms": round(ms, 1),
        }
        if ok:
            parsed = self._parse_json(text)
            result.update(parsed)
            result["raw_response"] = text[:2000]
        else:
            result["error"] = text
        return result

    async def full_site_analysis(self, image_bytes: bytes, provider: str = "auto") -> dict:
        """完整工地分析（安全 + 進度 + 異常）"""
        safety = await self.safety_check(image_bytes, provider)
        progress = await self.progress_check(image_bytes, provider)
        anomaly = await self.anomaly_check(image_bytes, provider)
        return {
            "type": "full_site_analysis",
            "safety": safety,
            "progress": progress,
            "anomaly": anomaly,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _parse_json(self, text: str) -> dict:
        import re
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    pass
        return {"raw": text[:1000]}


# =====================================================================
# 4. 知識庫整合
# =====================================================================

class _OllamaEmbeddingFunction:
    """使用本地 Ollama nomic-embed-text 產生 embedding，避免 ChromaDB 下載 79MB ONNX 模型。
    符合 ChromaDB 1.5.0 EmbeddingFunction Protocol。"""

    def __init__(self, model: str = "nomic-embed-text", base_url: str = ""):
        self._model = model
        self._base_urls = [u for u in [
            base_url,
            OLLAMA_BASE_URL,
            "http://127.0.0.1:11460",
            "http://127.0.0.1:11434",
        ] if u]

    @staticmethod
    def name() -> str:
        return "ollama_nomic_embed"

    def get_config(self) -> dict:
        return {"model": self._model}

    @staticmethod
    def build_from_config(config: dict):
        return _OllamaEmbeddingFunction(model=config.get("model", "nomic-embed-text"))

    def __call__(self, input: list[str]) -> list[list[float]]:
        import urllib.request
        for base in self._base_urls:
            url = f"{base.rstrip('/')}/api/embed"
            try:
                payload = json.dumps({"model": self._model, "input": input}).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read().decode("utf-8"))
                    return data.get("embeddings", [])
            except Exception:
                continue
        log.warning("Ollama embedding 不可用，回傳零向量")
        return [[0.0] * 768 for _ in input]


class VisionKnowledgeStore:
    """視覺分析結果寫入知識庫"""

    def __init__(self):
        self._collection = None
        self._initialized = False

    def _init_chromadb(self):
        if self._initialized:
            return
        try:
            import chromadb
            client = chromadb.PersistentClient(path=CHROMADB_PATH)
            embed_fn = _OllamaEmbeddingFunction()
            try:
                self._collection = client.get_or_create_collection(
                    name="vision_edge_results",
                    metadata={"description": "AI 視覺邊緣計算分析結果"},
                    embedding_function=embed_fn,
                )
            except Exception:
                # 已有 collection 且 embedding function 衝突時，直接取得
                self._collection = client.get_collection(
                    name="vision_edge_results",
                    embedding_function=embed_fn,
                )
            self._initialized = True
            log.info(f"ChromaDB 視覺知識庫已連接（Ollama embedding）: {CHROMADB_PATH}")
        except Exception as e:
            log.warning(f"ChromaDB 連接失敗: {e}")

    def store_result(self, result: VisionResult):
        """儲存分析結果到知識庫"""
        self._init_chromadb()
        if not self._collection:
            return
        try:
            doc = (
                f"[視覺分析 {result.timestamp}] "
                f"來源: {result.source} | "
                f"描述: {result.description} | "
                f"物件: {', '.join(result.objects[:10])} | "
                f"異常: {', '.join(result.anomalies[:5])} | "
                f"安全: {', '.join(result.safety_violations[:5])} | "
                f"進度: {result.progress_status}"
            )
            self._collection.add(
                documents=[doc],
                ids=[result.id],
                metadatas=[{
                    "source": result.source,
                    "timestamp": result.timestamp,
                    "confidence": result.confidence,
                    "detection_count": result.detection_count,
                    "has_anomaly": len(result.anomalies) > 0,
                    "has_safety_issue": len(result.safety_violations) > 0,
                }]
            )
        except Exception as e:
            log.warning(f"知識庫寫入失敗: {e}")

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """搜尋視覺知識庫"""
        self._init_chromadb()
        if not self._collection:
            return []
        try:
            results = self._collection.query(query_texts=[query], n_results=limit)
            items = []
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                items.append({"document": doc, "metadata": meta, "distance": results["distances"][0][i] if results.get("distances") else 0})
            return items
        except Exception:
            return []

    def get_count(self) -> int:
        self._init_chromadb()
        if not self._collection:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0


# =====================================================================
# 5. FastAPI 應用
# =====================================================================

app = FastAPI(
    title="築未科技 — AI 視覺邊緣計算服務",
    version="1.0.0",
    description="Vision Edge Computing Service: Pipeline + Monitor + Construction AI + Dashboard",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全域實例
pipeline = VisionPipeline()
monitor = VisionMonitor(pipeline)
construction_ai = ConstructionAI(pipeline)
knowledge_store = VisionKnowledgeStore()


# ----- 健康檢查 -----
@app.get("/health")
async def health():
    ollama_ok = False
    if httpx:
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(f"{OLLAMA_BASE_URL}/api/tags")
                ollama_ok = r.status_code == 200
        except Exception:
            pass
    return {
        "status": "ok",
        "service": "vision-edge",
        "version": "1.0.0",
        "ollama": ollama_ok,
        "yolo_loaded": pipeline._yolo_loaded,
        "monitor_running": monitor._running,
        "monitor_sources": len(monitor.sources),
        "knowledge_count": knowledge_store.get_count(),
        "stats": pipeline.get_stats(),
    }


# ----- Vision Pipeline API -----
@app.post("/api/vision/analyze")
async def api_analyze(
    file: UploadFile = File(None),
    image_base64: str = Form(""),
    prompt: str = Form(""),
    mode: str = Form("hybrid"),
    provider: str = Form("auto"),
    model: str = Form(""),
    enhance: bool = Form(False),
    save_to_kb: bool = Form(True),
):
    """通用視覺分析"""
    if file:
        image_bytes = await file.read()
    elif image_base64:
        image_bytes = base64.b64decode(image_base64)
    else:
        raise HTTPException(400, "需要提供 file 或 image_base64")

    result = await pipeline.analyze(
        image_bytes=image_bytes,
        prompt=prompt,
        source="api_upload",
        mode=mode,
        provider=provider,
        model=model,
        enhance=enhance,
    )

    if save_to_kb:
        knowledge_store.store_result(result)

    return asdict(result)


@app.post("/api/vision/detect")
async def api_detect(
    file: UploadFile = File(None),
    image_base64: str = Form(""),
    conf_threshold: float = Form(0.25),
):
    """純 YOLO 物件偵測"""
    if file:
        image_bytes = await file.read()
    elif image_base64:
        image_bytes = base64.b64decode(image_base64)
    else:
        raise HTTPException(400, "需要提供 file 或 image_base64")

    if not pipeline._yolo_loaded:
        pipeline.load_yolo()

    detections = pipeline.yolo_detect(image_bytes, conf_threshold)
    return {"ok": True, "detections": detections, "count": len(detections)}


@app.post("/api/vision/vlm")
async def api_vlm(
    file: UploadFile = File(None),
    image_base64: str = Form(""),
    prompt: str = Form("請描述這張圖片的內容"),
    provider: str = Form("auto"),
    model: str = Form(""),
):
    """純 VLM 推理"""
    if file:
        image_bytes = await file.read()
    elif image_base64:
        image_bytes = base64.b64decode(image_base64)
    else:
        raise HTTPException(400, "需要提供 file 或 image_base64")

    ok, text, ms = await pipeline.vlm_inference(image_bytes, prompt, model, provider)
    return {"ok": ok, "response": text, "inference_ms": round(ms, 1), "provider": provider}


# ----- 監控 API -----
@app.post("/api/monitor/sources")
async def api_add_monitor_source(payload: dict):
    """新增監控來源"""
    source = MonitorSource(
        name=payload.get("name", "未命名"),
        type=payload.get("type", "screenshot"),
        url=payload.get("url", ""),
        camera_id=int(payload.get("camera_id", 0)),
        interval_sec=max(5, int(payload.get("interval_sec", 30))),
        analysis_mode=payload.get("analysis_mode", "hybrid"),
        alert_rules=payload.get("alert_rules", []),
    )
    sid = monitor.add_source(source)
    return {"ok": True, "source_id": sid, "source": asdict(source)}


@app.delete("/api/monitor/sources/{source_id}")
async def api_remove_monitor_source(source_id: str):
    ok = monitor.remove_source(source_id)
    return {"ok": ok}


@app.post("/api/monitor/start")
async def api_monitor_start():
    await monitor.start()
    return {"ok": True, "status": monitor.get_status()}


@app.post("/api/monitor/stop")
async def api_monitor_stop():
    await monitor.stop()
    return {"ok": True}


@app.get("/api/monitor/status")
async def api_monitor_status():
    return monitor.get_status()


@app.get("/api/monitor/alerts")
async def api_monitor_alerts(limit: int = 50, level: str = ""):
    return {"alerts": monitor.get_alerts(limit, level)}


@app.post("/api/monitor/capture-now/{source_id}")
async def api_capture_now(source_id: str):
    """立即擷取並分析"""
    source = monitor.sources.get(source_id)
    if not source:
        raise HTTPException(404, "來源不存在")
    image_bytes = await monitor._capture(source)
    if not image_bytes:
        raise HTTPException(500, "擷取失敗")
    result = await pipeline.analyze(
        image_bytes=image_bytes,
        source=f"manual:{source.name}",
        mode=source.analysis_mode,
    )
    knowledge_store.store_result(result)
    return asdict(result)


# ----- 施工現場 AI API -----
@app.post("/api/construction/safety")
async def api_construction_safety(
    file: UploadFile = File(None),
    image_base64: str = Form(""),
    provider: str = Form("auto"),
):
    """施工安全檢查"""
    if file:
        image_bytes = await file.read()
    elif image_base64:
        image_bytes = base64.b64decode(image_base64)
    else:
        raise HTTPException(400, "需要提供 file 或 image_base64")
    return await construction_ai.safety_check(image_bytes, provider)


@app.post("/api/construction/progress")
async def api_construction_progress(
    file: UploadFile = File(None),
    image_base64: str = Form(""),
    provider: str = Form("auto"),
):
    """施工進度分析"""
    if file:
        image_bytes = await file.read()
    elif image_base64:
        image_bytes = base64.b64decode(image_base64)
    else:
        raise HTTPException(400, "需要提供 file 或 image_base64")
    return await construction_ai.progress_check(image_bytes, provider)


@app.post("/api/construction/anomaly")
async def api_construction_anomaly(
    file: UploadFile = File(None),
    image_base64: str = Form(""),
    provider: str = Form("auto"),
):
    """工地異常偵測"""
    if file:
        image_bytes = await file.read()
    elif image_base64:
        image_bytes = base64.b64decode(image_base64)
    else:
        raise HTTPException(400, "需要提供 file 或 image_base64")
    return await construction_ai.anomaly_check(image_bytes, provider)


@app.post("/api/construction/full-analysis")
async def api_construction_full(
    file: UploadFile = File(None),
    image_base64: str = Form(""),
    provider: str = Form("auto"),
):
    """完整工地分析"""
    if file:
        image_bytes = await file.read()
    elif image_base64:
        image_bytes = base64.b64decode(image_base64)
    else:
        raise HTTPException(400, "需要提供 file 或 image_base64")
    return await construction_ai.full_site_analysis(image_bytes, provider)


# ----- 知識庫 API -----
@app.get("/api/vision/knowledge/search")
async def api_knowledge_search(q: str = "", limit: int = 10):
    if not q:
        raise HTTPException(400, "需要提供 q 參數")
    return {"results": knowledge_store.search(q, limit)}


@app.get("/api/vision/knowledge/count")
async def api_knowledge_count():
    return {"count": knowledge_store.get_count()}


# ----- 推理歷史 -----
@app.get("/api/vision/history")
async def api_history(limit: int = 20):
    return {"history": pipeline.get_history(limit)}


@app.get("/api/vision/stats")
async def api_stats():
    return pipeline.get_stats()


# ----- WebSocket 即時推送 -----
@app.websocket("/ws/vision")
async def ws_vision(websocket: WebSocket):
    await websocket.accept()
    monitor._ws_clients.append(websocket)
    log.info(f"WebSocket 客戶端已連接，共 {len(monitor._ws_clients)} 個")
    try:
        while True:
            data = await websocket.receive_text()
            # 可處理客戶端指令
            try:
                cmd = json.loads(data)
                if cmd.get("action") == "ping":
                    await websocket.send_json({"type": "pong", "ts": datetime.now(timezone.utc).isoformat()})
            except Exception:
                pass
    except WebSocketDisconnect:
        if websocket in monitor._ws_clients:
            monitor._ws_clients.remove(websocket)
        log.info(f"WebSocket 客戶端已斷開，剩餘 {len(monitor._ws_clients)} 個")


# ----- 深度分析 API（圖片/影片/串流 → 精細計數 + 標註圖 + 報告）-----
try:
    from tools.vision_deep_analyzer import deep_analyzer, DeepAnalysisReport
    _deep_ok = True
except ImportError:
    try:
        from vision_deep_analyzer import deep_analyzer, DeepAnalysisReport
        _deep_ok = True
    except ImportError:
        deep_analyzer = None
        _deep_ok = False
        log.warning("vision_deep_analyzer 匯入失敗，深度分析功能不可用")


@app.post("/api/vision/deep/image")
async def api_deep_image(
    file: UploadFile = File(None),
    image_base64: str = Form(""),
    image_url: str = Form(""),
    conf: float = Form(0.25),
    source_name: str = Form("upload"),
):
    """深度分析圖片 — YOLO 全物件偵測 + VLM 深度分類 + 標註圖 + 報告"""
    if not _deep_ok:
        raise HTTPException(503, "深度分析模組未載入")

    if file and file.filename:
        image_bytes = await file.read()
        source_name = source_name or file.filename
    elif image_base64:
        image_bytes = base64.b64decode(image_base64)
    elif image_url:
        image_bytes = await deep_analyzer.download_video(image_url)
        if not image_bytes:
            raise HTTPException(400, f"無法下載圖片: {image_url}")
        source_name = source_name or image_url.split("/")[-1][:50]
    else:
        raise HTTPException(400, "需要提供 file、image_base64 或 image_url")

    report = await deep_analyzer.analyze_image(image_bytes, source_name=source_name, conf=conf)

    # 學習模組自動學習
    learning_result = None
    if _learning_ok and learning_module:
        try:
            from dataclasses import asdict as _da
            learning_result = learning_module.learn_from_analysis(_da(report))
        except Exception as e:
            log.warning(f"學習模組處理失敗: {e}")

    # 儲存到知識庫
    if report.summary.get("total", 0) > 0:
        try:
            vr = VisionResult(
                source=f"deep:{source_name}",
                description=report.scene_description,
                objects=list(report.summary.get("by_class_zh", {}).keys()),
                detection_count=report.summary.get("total", 0),
                confidence=0.8,
            )
            knowledge_store.store_result(vr)
        except Exception:
            pass

    return _deep_report_response(report)


@app.post("/api/vision/deep/video")
async def api_deep_video(
    file: UploadFile = File(None),
    video_url: str = Form(""),
    max_frames: int = Form(10),
    interval_sec: float = Form(0),
    conf: float = Form(0.25),
    source_name: str = Form("video"),
):
    """深度分析影片 — 逐幀抽取 + YOLO + VLM + 標註圖 + 彙整報告"""
    if not _deep_ok:
        raise HTTPException(503, "深度分析模組未載入")

    if file and file.filename:
        video_bytes = await file.read()
        source_name = source_name or file.filename
        report = await deep_analyzer.analyze_video(
            video_bytes, source_name=source_name,
            max_frames=max_frames, interval_sec=interval_sec,
            conf=conf, is_bytes=True,
        )
    elif video_url:
        source_name = source_name or video_url.split("/")[-1][:50]
        report = await deep_analyzer.analyze_stream_url(
            video_url, source_name=source_name,
            max_frames=max_frames, interval_sec=interval_sec,
            conf=conf,
        )
    else:
        raise HTTPException(400, "需要提供 file 或 video_url")

    # 學習模組自動學習
    if _learning_ok and learning_module:
        try:
            from dataclasses import asdict as _da
            learning_module.learn_from_analysis(_da(report))
        except Exception:
            pass

    return _deep_report_response(report)


@app.post("/api/vision/deep/stream")
async def api_deep_stream(
    stream_url: str = Form(""),
    max_frames: int = Form(10),
    interval_sec: float = Form(2),
    conf: float = Form(0.25),
    source_name: str = Form(""),
):
    """分析串流 URL（圖片或影片）"""
    if not _deep_ok:
        raise HTTPException(503, "深度分析模組未載入")
    if not stream_url:
        raise HTTPException(400, "需要提供 stream_url")

    report = await deep_analyzer.analyze_stream_url(
        stream_url, source_name=source_name,
        max_frames=max_frames, interval_sec=interval_sec,
        conf=conf,
    )
    return _deep_report_response(report)


@app.get("/api/vision/deep/report/{report_id}")
async def api_deep_report(report_id: str):
    """取得深度分析報告 JSON"""
    json_path = ROOT / "reports" / "vision_deep" / f"{report_id}_report.json"
    if not json_path.exists():
        raise HTTPException(404, "報告不存在")
    return JSONResponse(json.loads(json_path.read_text(encoding="utf-8")))


@app.get("/api/vision/deep/report/{report_id}/text")
async def api_deep_report_text(report_id: str):
    """取得深度分析報告純文字"""
    txt_path = ROOT / "reports" / "vision_deep" / f"{report_id}_report.txt"
    if not txt_path.exists():
        raise HTTPException(404, "報告不存在")
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(txt_path.read_text(encoding="utf-8"))


@app.get("/api/vision/deep/annotated/{filename}")
async def api_deep_annotated(filename: str):
    """取得標註圖片"""
    from fastapi.responses import FileResponse
    img_path = ROOT / "reports" / "vision_deep" / "annotated" / filename
    if not img_path.exists():
        raise HTTPException(404, "圖片不存在")
    return FileResponse(str(img_path), media_type="image/png")


def _deep_report_response(report) -> dict:
    """將 DeepAnalysisReport 轉為 API 回應"""
    from dataclasses import asdict as _asdict
    d = _asdict(report)
    # 移除過大的欄位，改為摘要
    frame_summaries = []
    for fa in d.get("frame_analyses", []):
        frame_summaries.append({
            "frame_index": fa.get("frame_index"),
            "timestamp_sec": fa.get("timestamp_sec"),
            "object_count": len(fa.get("objects", [])),
            "object_counts": fa.get("object_counts", {}),
            "vlm_description": fa.get("vlm_description", "")[:300],
            "vlm_extra_objects": fa.get("vlm_extra_objects", []),
            "annotated_path": fa.get("annotated_path", ""),
        })
    d["frame_analyses"] = frame_summaries
    # 限制 all_detections_flat 大小
    if len(d.get("all_detections_flat", [])) > 100:
        d["all_detections_flat"] = d["all_detections_flat"][:100]
        d["all_detections_truncated"] = True
    return d


# ----- 學習模組 API -----
try:
    from tools.vision_learning_module import learning_module
    _learning_ok = True
except ImportError:
    try:
        from vision_learning_module import learning_module
        _learning_ok = True
    except ImportError:
        learning_module = None
        _learning_ok = False
        log.warning("vision_learning_module 匯入失敗")


@app.get("/api/vision/learning/domains")
async def api_learning_domains(domain: str = ""):
    """取得領域知識"""
    if not _learning_ok:
        raise HTTPException(503, "學習模組未載入")
    return learning_module.get_domain_info(domain)


@app.get("/api/vision/learning/params")
async def api_learning_params(domain: str = "general"):
    """取得領域優化參數"""
    if not _learning_ok:
        raise HTTPException(503, "學習模組未載入")
    return learning_module.get_optimized_params(domain)


@app.get("/api/vision/learning/summary")
async def api_learning_summary():
    """取得學習模組總結"""
    if not _learning_ok:
        raise HTTPException(503, "學習模組未載入")
    return learning_module.get_learning_summary()


@app.get("/api/vision/learning/suggestions")
async def api_learning_suggestions(limit: int = 10):
    """取得最近改進建議"""
    if not _learning_ok:
        raise HTTPException(503, "學習模組未載入")
    return {"suggestions": learning_module.get_recent_suggestions(limit)}


# ----- 儀表板 -----
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html_path = ROOT / "tools" / "vision_edge_dashboard.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Vision Edge Dashboard</h1><p>Dashboard HTML not found.</p>")


# ----- 啟動事件 -----
@app.on_event("startup")
async def startup():
    log.info("=== AI 視覺邊緣計算服務啟動 ===")
    log.info(f"Port: {VISION_EDGE_PORT}")
    log.info(f"Ollama: {OLLAMA_BASE_URL}")
    log.info(f"VLM Model: {VLM_MODEL}")

    # 嘗試載入 YOLO
    if YOLO_MODEL_PATH or os.path.exists("yolov8n.pt"):
        pipeline.load_yolo()
    else:
        log.info("YOLO 模型未指定，物件偵測功能需手動載入")

    # 新增預設截圖監控來源（停用狀態，需手動啟用）
    monitor.add_source(MonitorSource(
        name="螢幕截圖",
        type="screenshot",
        interval_sec=60,
        enabled=False,
        analysis_mode="vlm_only",
    ))

    log.info("服務就緒")


# ===== 主程式 =====
def main():
    import uvicorn
    uvicorn.run(
        "tools.vision_edge_service:app",
        host="0.0.0.0",
        port=VISION_EDGE_PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()

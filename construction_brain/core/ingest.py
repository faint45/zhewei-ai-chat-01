# -*- coding: utf-8 -*-
"""
營建自動化大腦 — 入庫分類引擎
語音/照片 → 辨識 → 分類 → 結構化 → 儲存

複用：
  - construction_mgmt/voice_service.py: faster-whisper 語音辨識
  - tools/vision_edge_service.py: YOLO + VLM 視覺分析
"""
import asyncio
import io
import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger("construction_brain.ingest")

# ===== 設定 =====
DATA_DIR = Path(os.environ.get("CB_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "voice").mkdir(exist_ok=True)
(DATA_DIR / "photos").mkdir(exist_ok=True)
(DATA_DIR / "events").mkdir(exist_ok=True)


class IngestResult:
    """入庫結果"""
    __slots__ = ("id", "type", "timestamp", "project_id", "transcript",
                 "events", "image_description", "yolo_detections",
                 "source_path", "elapsed_ms", "error")

    def __init__(self):
        self.id = str(uuid.uuid4())[:12]
        self.timestamp = datetime.now().isoformat()
        self.type = ""           # "voice" | "photo" | "text"
        self.project_id = ""
        self.transcript = ""
        self.events = {}         # extract_work_events 結果
        self.image_description = ""
        self.yolo_detections = []
        self.source_path = ""
        self.elapsed_ms = 0.0
        self.error = ""

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__slots__}


def ingest_voice(audio_path: str, project_id: str = "", project_name: str = "",
                 language: str = "auto") -> IngestResult:
    """
    語音入庫：audio → faster-whisper → 事件抽取 → 儲存

    Args:
        audio_path: 語音檔路徑
        project_id: 工程代號
        project_name: 工程名稱
        language: 語言代碼 ("zh", "auto")
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    t0 = time.perf_counter()
    result = IngestResult()
    result.type = "voice"
    result.project_id = project_id
    result.source_path = audio_path

    # 1. 語音辨識（faster-whisper，綁 GPU1）
    try:
        from construction_mgmt.voice_service import transcribe_audio
        asr = transcribe_audio(audio_path, language=language)
        result.transcript = asr.get("text", "")
        if asr.get("error"):
            result.error = asr["error"]
            return result
    except Exception as e:
        result.error = f"語音辨識失敗: {e}"
        log.error(result.error)
        return result

    # 2. 事件抽取（LLM 統一 prompt）
    try:
        from construction_brain.core.extract_work_events import extract_events
        result.events = extract_events(result.transcript, project_name=project_name)
    except Exception as e:
        result.error = f"事件抽取失敗: {e}"
        log.error(result.error)

    # 3. 儲存
    result.elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    _save_event(result)
    log.info(f"語音入庫完成: {result.id} ({result.elapsed_ms}ms)")
    return result


def ingest_photo(image_bytes: bytes, project_id: str = "", project_name: str = "",
                 filename: str = "") -> IngestResult:
    """
    照片入庫：image → YOLO 偵測 + VLM 描述 → 事件抽取 → 儲存

    Args:
        image_bytes: 圖片二進位資料
        project_id: 工程代號
        project_name: 工程名稱
        filename: 原始檔名
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    t0 = time.perf_counter()
    result = IngestResult()
    result.type = "photo"
    result.project_id = project_id

    # 1. 儲存照片
    ext = Path(filename).suffix if filename else ".jpg"
    photo_path = DATA_DIR / "photos" / f"{result.id}{ext}"
    photo_path.write_bytes(image_bytes)
    result.source_path = str(photo_path)

    # 2. YOLO 偵測（綁 GPU1）
    try:
        from tools.vision_edge_service import VisionPipeline
        pipeline = VisionPipeline()
        pipeline.load_yolo()
        result.yolo_detections = pipeline.yolo_detect(image_bytes)
    except Exception as e:
        log.warning(f"YOLO 偵測跳過: {e}")

    # 3. VLM 圖片描述（若可用）
    try:
        from tools.vision_edge_service import VisionPipeline
        pipeline = VisionPipeline()
        loop = asyncio.new_event_loop()
        ok, desc, _ = loop.run_until_complete(
            pipeline.vlm_inference(image_bytes, "請描述這張施工現場照片，列出可見的人員、設備、材料和施工項目。")
        )
        loop.close()
        if ok:
            result.image_description = desc
    except Exception as e:
        log.warning(f"VLM 描述跳過: {e}")

    # 4. 事件抽取（結合 YOLO + VLM 結果）
    try:
        from construction_brain.core.extract_work_events import extract_events_from_photo
        description = result.image_description or "施工現場照片"
        result.events = extract_events_from_photo(
            description,
            yolo_detections=result.yolo_detections,
            project_name=project_name,
        )
    except Exception as e:
        result.error = f"事件抽取失敗: {e}"
        log.error(result.error)

    result.elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    _save_event(result)
    log.info(f"照片入庫完成: {result.id} ({result.elapsed_ms}ms)")
    return result


def ingest_text(text: str, project_id: str = "", project_name: str = "") -> IngestResult:
    """
    文字入庫：手動輸入文字 → 事件抽取 → 儲存
    """
    t0 = time.perf_counter()
    result = IngestResult()
    result.type = "text"
    result.project_id = project_id
    result.transcript = text

    try:
        from construction_brain.core.extract_work_events import extract_events
        result.events = extract_events(text, project_name=project_name)
    except Exception as e:
        result.error = f"事件抽取失敗: {e}"
        log.error(result.error)

    result.elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    _save_event(result)
    return result


def _save_event(result: IngestResult):
    """儲存事件到 JSON 檔"""
    try:
        path = DATA_DIR / "events" / f"{result.id}.json"
        path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log.error(f"事件儲存失敗: {e}")

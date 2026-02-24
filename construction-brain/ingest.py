# -*- coding: utf-8 -*-
"""
築未科技 Construction Brain
ingest.py

功能：
  1. 語音檔（m4a/mp3/wav/ogg）→ Whisper 轉寫 → transcript.txt → 觸發 extract_work_events
  2. 照片檔（jpg/png/webp）→ EXIF 抽取 → hash 去重 → AI 分類 → 分類資料夾 → SQLite 索引
  3. 監控資料夾新增檔案，自動觸發上述流程

用法：
    # 單次處理一個語音檔
    python ingest.py --voice 01_Input/Voice/LINE/2026-02-24/msg001.m4a --project_id PRJ-001

    # 單次處理一張照片
    python ingest.py --photo 01_Input/Photos/LINE/2026-02-24/img001.jpg --project_id PRJ-001

    # 監控資料夾（常駐模式）
    python ingest.py --watch --project_id PRJ-001
"""

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(os.environ.get("ZHEWEI_BASE", r"C:\ZheweiConstruction"))
DB_PATH = BASE_DIR / "db" / "index.db"

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "zhewei-brain")

VOICE_EXTENSIONS = {".m4a", ".mp3", ".wav", ".ogg", ".aac", ".flac"}
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}

PHOTO_TYPES = ["施工進度", "工安缺失", "材料入場", "機具運作", "竣工查驗", "環境天候", "其他"]

CLASSIFY_PROMPT = """你是工地照片分類引擎。

分析照片內容，輸出純 JSON（不得有其他文字）：
{
  "photo_type": "施工進度|工安缺失|材料入場|機具運作|竣工查驗|環境天候|其他",
  "sub_type": "詳細子類型（鋼筋/模板/混凝土/未戴安全帽/開口未防護/...）",
  "location_hint": "可辨識的位置或工區（無法判斷填null）",
  "safety_issues": [
    {"description": "缺失描述", "location": "位置", "severity": "low|medium|high"}
  ],
  "description": "一句話說明照片內容"
}

safety_issues 只在 photo_type=工安缺失 時填寫，其他情況填 []。"""


def _ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS photos (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            date TEXT,
            original_path TEXT,
            classified_path TEXT,
            photo_type TEXT,
            sub_type TEXT,
            location_hint TEXT,
            hash TEXT UNIQUE,
            exif_time TEXT,
            exif_gps TEXT,
            message_id TEXT,
            description TEXT,
            safety_json TEXT,
            status TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS transcripts (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            date TEXT,
            voice_path TEXT,
            transcript_path TEXT,
            hash TEXT UNIQUE,
            message_id TEXT,
            status TEXT,
            created_at TEXT
        );
    """)
    conn.commit()
    conn.close()


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_duplicate(table: str, file_hash: str) -> bool:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(f"SELECT id FROM {table} WHERE hash=?", (file_hash,)).fetchone()
    conn.close()
    return row is not None


def _exif_extract(photo_path: Path) -> tuple[str, str]:
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
        img = Image.open(photo_path)
        exif_data = img._getexif() or {}
        exif_time = ""
        gps_info = ""
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "DateTimeOriginal":
                exif_time = str(value)
            if tag == "GPSInfo":
                gps_info = str(value)
        return exif_time, gps_info
    except Exception:
        return "", ""


def _classify_photo(photo_path: Path) -> dict:
    try:
        import base64
        import httpx
        with open(photo_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        ext = photo_path.suffix.lower().lstrip(".")
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": CLASSIFY_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "請分類此工地照片："},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
                    ],
                },
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }
        with httpx.Client(timeout=60) as client:
            r = client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            r.raise_for_status()
            raw = r.json()["message"]["content"].strip()
        import re
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            return json.loads(m.group(0))
    except Exception as e:
        print(f"[ingest] 照片分類失敗（{e}），歸類為「其他」")
    return {"photo_type": "其他", "sub_type": "", "location_hint": None,
            "safety_issues": [], "description": ""}


def _build_classified_path(project_id: str, event_date: str,
                            photo_type: str, sub_type: str, location: str,
                            original_name: str) -> Path:
    date_str = event_date.replace("-", "")
    time_str = datetime.now().strftime("%H%M%S")
    parts = [date_str, time_str, photo_type]
    if location:
        parts.append(location[:20])
    if sub_type:
        parts.append(sub_type[:20])
    suffix = Path(original_name).suffix
    filename = "_".join(p for p in parts if p) + suffix
    classified_dir = (
        BASE_DIR / "projects" / project_id
        / "01_Input" / "Photos" / photo_type / event_date
    )
    classified_dir.mkdir(parents=True, exist_ok=True)
    return classified_dir / filename


def process_photo(photo_path: Path, project_id: str = "default",
                  message_id: str = "", event_date: str = "") -> dict:
    _ensure_db()
    photo_path = Path(photo_path)
    event_date = event_date or datetime.now().strftime("%Y-%m-%d")
    file_hash = _file_hash(photo_path)

    if _is_duplicate("photos", file_hash):
        print(f"[ingest] 照片重複，略過：{photo_path.name}")
        return {"status": "duplicate", "hash": file_hash}

    print(f"[ingest] 處理照片：{photo_path.name}")
    exif_time, exif_gps = _exif_extract(photo_path)
    classify_result = _classify_photo(photo_path)

    photo_type = classify_result.get("photo_type", "其他")
    sub_type = classify_result.get("sub_type", "")
    location_hint = classify_result.get("location_hint") or ""
    description = classify_result.get("description", "")
    safety_json = json.dumps(classify_result.get("safety_issues", []), ensure_ascii=False)

    classified_path = _build_classified_path(
        project_id, event_date, photo_type, sub_type, location_hint, photo_path.name
    )
    shutil.copy2(photo_path, classified_path)
    print(f"[ingest] 照片分類 → {photo_type}/{classified_path.name}")

    photo_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO photos
           (id,project_id,date,original_path,classified_path,photo_type,sub_type,
            location_hint,hash,exif_time,exif_gps,message_id,description,safety_json,status,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (photo_id, project_id, event_date, str(photo_path), str(classified_path),
         photo_type, sub_type, location_hint, file_hash, exif_time, exif_gps,
         message_id, description, safety_json, "ok", datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    result = {
        "photo_id": photo_id,
        "photo_type": photo_type,
        "sub_type": sub_type,
        "classified_path": str(classified_path),
        "safety_issues": classify_result.get("safety_issues", []),
        "status": "ok",
    }

    if classify_result.get("safety_issues"):
        print(f"[ingest] ⚠️ 發現工安缺失 {len(classify_result['safety_issues'])} 項，將寫入工安模組")

    return result


def process_voice(voice_path: Path, project_id: str = "default",
                  message_id: str = "", event_date: str = "") -> dict:
    _ensure_db()
    voice_path = Path(voice_path)
    event_date = event_date or datetime.now().strftime("%Y-%m-%d")
    file_hash = _file_hash(voice_path)

    if _is_duplicate("transcripts", file_hash):
        print(f"[ingest] 語音重複，略過：{voice_path.name}")
        return {"status": "duplicate", "hash": file_hash}

    print(f"[ingest] 語音轉寫：{voice_path.name}")
    try:
        import faster_whisper
        model = faster_whisper.WhisperModel(WHISPER_MODEL, device="auto", compute_type="auto")
        segments, info = model.transcribe(str(voice_path), language="zh")
        transcript = "".join(seg.text for seg in segments).strip()
        print(f"[ingest] 轉寫完成（{info.language}）：{transcript[:80]}...")
    except ImportError:
        print("[ingest] faster-whisper 未安裝，請執行：pip install faster-whisper")
        return {"status": "error", "error": "faster-whisper 未安裝"}
    except Exception as e:
        print(f"[ingest] 語音轉寫失敗：{e}")
        return {"status": "error", "error": str(e)}

    transcript_dir = BASE_DIR / "projects" / project_id / "01_Input" / "Voice" / event_date
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = transcript_dir / (voice_path.stem + "_transcript.txt")
    transcript_path.write_text(transcript, encoding="utf-8")
    print(f"[ingest] 逐字稿 → {transcript_path}")

    transcript_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO transcripts
           (id,project_id,date,voice_path,transcript_path,hash,message_id,status,created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (transcript_id, project_id, event_date, str(voice_path),
         str(transcript_path), file_hash, message_id, "ok", datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    from extract_work_events import extract
    event = extract(
        text=transcript,
        project_id=project_id,
        source="line_voice",
        source_ref=voice_path.name,
        event_date=event_date,
    )

    return {"transcript_id": transcript_id, "transcript": transcript,
            "work_event_id": event.get("event_id"), "status": "ok"}


def watch(project_id: str = "default", interval: int = 5):
    """監控 Input 資料夾，自動觸發處理（輪詢模式）"""
    watch_dirs = [
        BASE_DIR / "projects" / project_id / "01_Input" / "Photos" / "LINE",
        BASE_DIR / "projects" / project_id / "01_Input" / "Voice" / "LINE",
    ]
    for d in watch_dirs:
        d.mkdir(parents=True, exist_ok=True)

    processed = set()
    print(f"[ingest] 監控中（間隔 {interval}s）... Ctrl+C 結束")
    while True:
        for watch_dir in watch_dirs:
            for f in watch_dir.rglob("*"):
                if f.is_file() and str(f) not in processed:
                    processed.add(str(f))
                    event_date = f.parent.name if len(f.parent.name) == 10 else datetime.now().strftime("%Y-%m-%d")
                    if f.suffix.lower() in PHOTO_EXTENSIONS:
                        process_photo(f, project_id=project_id, event_date=event_date)
                    elif f.suffix.lower() in VOICE_EXTENSIONS:
                        process_voice(f, project_id=project_id, event_date=event_date)
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="築未科技 — 語音/照片自動入庫")
    parser.add_argument("--project_id", default="test_project_001")
    parser.add_argument("--date", default="")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--voice", help="語音檔路徑")
    group.add_argument("--photo", help="照片檔路徑")
    group.add_argument("--watch", action="store_true", help="監控資料夾模式")
    args = parser.parse_args()

    if args.voice:
        result = process_voice(Path(args.voice), project_id=args.project_id, event_date=args.date)
    elif args.photo:
        result = process_photo(Path(args.photo), project_id=args.project_id, event_date=args.date)
    else:
        watch(project_id=args.project_id)
        result = {}

    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))

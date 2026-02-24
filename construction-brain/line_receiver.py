# -*- coding: utf-8 -*-
"""
築未科技 Construction Brain
line_receiver.py

功能：LINE Messaging API Webhook 接收端
  - 文字訊息 → 觸發 extract_work_events
  - 語音訊息 → 下載 m4a → 觸發 ingest.process_voice
  - 圖片訊息 → 下載 jpg → 觸發 ingest.process_photo

啟動方式：
    uvicorn line_receiver:app --host 0.0.0.0 --port 8003

環境變數（.env）：
    LINE_CHANNEL_SECRET=xxxxx
    LINE_CHANNEL_ACCESS_TOKEN=xxxxx
    DEFAULT_PROJECT_ID=PRJ-001
    ZHEWEI_BASE=C:\ZheweiConstruction
"""

import hashlib
import hmac
import json
import os
from base64 import b64decode
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from extract_work_events import extract
from ingest import process_photo, process_voice

BASE_DIR = Path(os.environ.get("ZHEWEI_BASE", r"C:\ZheweiConstruction"))
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
DEFAULT_PROJECT_ID = os.environ.get("DEFAULT_PROJECT_ID", "test_project_001")

LINE_CONTENT_API = "https://api-data.line.me/v2/bot/message/{message_id}/content"

app = FastAPI(title="築未科技 LINE Receiver", version="0.1.0")


def _verify_signature(body: bytes, signature: str) -> bool:
    if not LINE_CHANNEL_SECRET:
        return True
    expected = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"), body, hashlib.sha256
    ).digest()
    try:
        return hmac.compare_digest(expected, b64decode(signature))
    except Exception:
        return False


def _download_line_content(message_id: str, dest_path: Path) -> bool:
    url = LINE_CONTENT_API.format(message_id=message_id)
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    try:
        with httpx.stream("GET", url, headers=headers, timeout=60) as r:
            r.raise_for_status()
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"[line_receiver] 下載失敗 message_id={message_id}: {e}")
        return False


def _get_project_id(group_id: str) -> str:
    mapping_path = BASE_DIR / "config" / "group_project_map.json"
    if mapping_path.exists():
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        return mapping.get(group_id, DEFAULT_PROJECT_ID)
    return DEFAULT_PROJECT_ID


def _handle_text(event: dict, project_id: str):
    text = event.get("message", {}).get("text", "").strip()
    if not text:
        return
    print(f"[line_receiver] 文字訊息：{text[:80]}")
    message_id = event.get("message", {}).get("id", "")
    event_date = datetime.now().strftime("%Y-%m-%d")
    extract(
        text=text,
        project_id=project_id,
        source="line_text",
        source_ref=message_id,
        event_date=event_date,
    )


def _handle_audio(event: dict, project_id: str):
    message_id = event.get("message", {}).get("id", "")
    event_date = datetime.now().strftime("%Y-%m-%d")
    dest = (
        BASE_DIR / "projects" / project_id
        / "01_Input" / "Voice" / "LINE" / event_date
        / f"{message_id}.m4a"
    )
    print(f"[line_receiver] 下載語音 {message_id}")
    if _download_line_content(message_id, dest):
        process_voice(dest, project_id=project_id, message_id=message_id, event_date=event_date)
    else:
        print(f"[line_receiver] ⚠️ 語音下載失敗 {message_id}")


def _handle_image(event: dict, project_id: str):
    message_id = event.get("message", {}).get("id", "")
    event_date = datetime.now().strftime("%Y-%m-%d")
    dest = (
        BASE_DIR / "projects" / project_id
        / "01_Input" / "Photos" / "LINE" / event_date
        / f"{message_id}.jpg"
    )
    print(f"[line_receiver] 下載圖片 {message_id}")
    if _download_line_content(message_id, dest):
        process_photo(dest, project_id=project_id, message_id=message_id, event_date=event_date)
    else:
        print(f"[line_receiver] ⚠️ 圖片下載失敗 {message_id}")


@app.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature: str = Header(None),
):
    body = await request.body()

    if LINE_CHANNEL_SECRET and not _verify_signature(body, x_line_signature or ""):
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    for event in payload.get("events", []):
        source = event.get("source", {})
        group_id = source.get("groupId") or source.get("userId", "")
        project_id = _get_project_id(group_id)
        msg_type = event.get("message", {}).get("type", "")

        if msg_type == "text":
            background_tasks.add_task(_handle_text, event, project_id)
        elif msg_type == "audio":
            background_tasks.add_task(_handle_audio, event, project_id)
        elif msg_type == "image":
            background_tasks.add_task(_handle_image, event, project_id)
        else:
            print(f"[line_receiver] 略過訊息類型：{msg_type}")

    return JSONResponse({"status": "ok"})


@app.get("/health")
async def health():
    return {"status": "ok", "service": "築未科技 LINE Receiver", "version": "0.1.0"}


@app.get("/")
async def root():
    return {
        "service": "築未科技 Construction Brain",
        "endpoints": {
            "POST /webhook": "LINE Messaging API Webhook",
            "GET /health": "服務狀態",
        },
    }

# -*- coding: utf-8 -*-
"""
營建自動化大腦 — LINE Webhook 接收器
接收 LINE 訊息/照片 → 自動入庫 → 回覆結構化結果

用法：
  掛載到 brain_server.py 或獨立 FastAPI app
  LINE Webhook URL: https://jarvis.zhe-wei.net/api/line/webhook
"""
import hashlib
import hmac
import json
import logging
import os
import tempfile
import time
import base64
from pathlib import Path
from typing import Optional

log = logging.getLogger("construction_brain.line")

LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11460").rstrip("/")


def verify_signature(body: bytes, signature: str) -> bool:
    """驗證 LINE Webhook 簽章"""
    if not LINE_CHANNEL_SECRET:
        log.warning("LINE_CHANNEL_SECRET 未設定，跳過簽章驗證")
        return True
    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(signature, expected)


def _download_line_content(message_id: str) -> Optional[bytes]:
    """從 LINE 下載附件（圖片/音檔）"""
    if not LINE_CHANNEL_TOKEN:
        log.error("LINE_CHANNEL_ACCESS_TOKEN 未設定")
        return None
    import urllib.request
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {LINE_CHANNEL_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except Exception as e:
        log.error(f"LINE 附件下載失敗: {e}")
        return None


def _reply_line(reply_token: str, text: str):
    """回覆 LINE 訊息"""
    if not LINE_CHANNEL_TOKEN:
        return
    import urllib.request
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text[:5000]}],  # LINE 限制 5000 字
    }
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/reply",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LINE_CHANNEL_TOKEN}",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log.error(f"LINE 回覆失敗: {e}")


def handle_webhook(body: dict) -> dict:
    """
    處理 LINE Webhook 事件

    Args:
        body: LINE Webhook JSON body

    Returns:
        {"processed": int, "results": [...]}
    """
    events = body.get("events", [])
    results = []

    for event in events:
        event_type = event.get("type", "")
        reply_token = event.get("replyToken", "")

        if event_type == "message":
            msg = event.get("message", {})
            msg_type = msg.get("type", "")
            # 取得用戶 / 群組資訊
            source = event.get("source", {})
            user_id = source.get("userId", "")
            group_id = source.get("groupId", "")

            if msg_type == "text":
                result = _handle_text_message(msg.get("text", ""), reply_token, user_id)
                results.append(result)

            elif msg_type == "image":
                result = _handle_image_message(msg.get("id", ""), reply_token, user_id)
                results.append(result)

            elif msg_type == "audio":
                result = _handle_audio_message(msg.get("id", ""), reply_token, user_id)
                results.append(result)

            else:
                log.info(f"忽略訊息類型: {msg_type}")

    return {"processed": len(results), "results": results}


def _handle_text_message(text: str, reply_token: str, user_id: str) -> dict:
    """處理文字訊息 → 事件抽取"""
    log.info(f"收到文字: {text[:50]}... (user={user_id})")

    try:
        from construction_brain.core.ingest import ingest_text
        result = ingest_text(text, project_id="line", project_name="LINE 回報")

        # 組裝回覆
        events = result.events or {}
        safety = events.get("safety_alerts", [])
        high_alerts = [s for s in safety if s.get("severity") == "high"]

        reply = f"✅ 已收到並記錄（{result.elapsed_ms:.0f}ms）"
        if high_alerts:
            reply += f"\n\n🔴 工安警報：\n"
            for a in high_alerts:
                reply += f"• {a.get('risk', '')}（{a.get('action', '')}）\n"

        _reply_line(reply_token, reply)
        return {"type": "text", "id": result.id, "status": "ok"}

    except Exception as e:
        log.error(f"文字處理失敗: {e}")
        _reply_line(reply_token, f"⚠️ 處理失敗: {e}")
        return {"type": "text", "status": "error", "error": str(e)}


def _handle_image_message(message_id: str, reply_token: str, user_id: str) -> dict:
    """處理圖片訊息 → YOLO + 事件抽取"""
    log.info(f"收到圖片: msg_id={message_id}")
    _reply_line(reply_token, "📷 照片分析中...")  # 先回覆，避免逾時

    image_bytes = _download_line_content(message_id)
    if not image_bytes:
        return {"type": "image", "status": "error", "error": "下載失敗"}

    try:
        from construction_brain.core.ingest import ingest_photo
        result = ingest_photo(image_bytes, project_id="line", project_name="LINE 回報",
                              filename=f"{message_id}.jpg")
        return {"type": "image", "id": result.id, "status": "ok"}
    except Exception as e:
        log.error(f"圖片處理失敗: {e}")
        return {"type": "image", "status": "error", "error": str(e)}


def _handle_audio_message(message_id: str, reply_token: str, user_id: str) -> dict:
    """處理語音訊息 → faster-whisper + 事件抽取"""
    log.info(f"收到語音: msg_id={message_id}")
    _reply_line(reply_token, "🎤 語音辨識中...")

    audio_bytes = _download_line_content(message_id)
    if not audio_bytes:
        return {"type": "audio", "status": "error", "error": "下載失敗"}

    # 暫存音檔
    tmp = tempfile.NamedTemporaryFile(suffix=".m4a", delete=False)
    tmp.write(audio_bytes)
    tmp.close()

    try:
        from construction_brain.core.ingest import ingest_voice
        result = ingest_voice(tmp.name, project_id="line", project_name="LINE 回報")

        # 回覆辨識結果摘要
        transcript = result.transcript[:200] if result.transcript else "（無法辨識）"
        # 不再 reply（已經用過 replyToken）
        return {"type": "audio", "id": result.id, "transcript": transcript, "status": "ok"}
    except Exception as e:
        log.error(f"語音處理失敗: {e}")
        return {"type": "audio", "status": "error", "error": str(e)}
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

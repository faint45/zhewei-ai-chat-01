#!/usr/bin/env python3
"""快速測試 RTSP 連線"""
import os, sys
from pathlib import Path

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

url = os.environ.get("TAPO_RTSP_URL") or (sys.argv[1] if len(sys.argv) > 1 else None)
if not url:
    print("請在 .env 設定 TAPO_RTSP_URL")
    sys.exit(1)

import cv2

print(f"測試連線：{url}")
cap = cv2.VideoCapture(url)
if not cap.isOpened():
    print("❌ 失敗：無法連線")
    sys.exit(1)

ret, frame = cap.read()
cap.release()

if ret and frame is not None:
    h, w = frame.shape[:2]
    print(f"✅ 成功：解析度 {w}x{h}")
    sys.exit(0)
else:
    print("❌ 失敗：連線成功但無法讀取畫面")
    sys.exit(1)

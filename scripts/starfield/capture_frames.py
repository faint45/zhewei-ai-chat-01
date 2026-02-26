#!/usr/bin/env python3
"""Tapo C230 星空攝影 — 擷取多幀"""
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"

import argparse
import cv2
from datetime import datetime
from pathlib import Path


def capture(rtsp_url, output_dir="starfield_frames", interval_sec=2.0, count=100):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    frame_dir = Path(output_dir) / datetime.now().strftime("%Y%m%d_%H%M%S")
    frame_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("錯誤：無法開啟 RTSP 串流")
        return
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    captured = 0
    try:
        while captured < count:
            ret, frame = cap.read()
            if not ret:
                cap.release()
                cap = cv2.VideoCapture(rtsp_url)
                continue
            cv2.imwrite(str(frame_dir / f"frame_{captured:05d}.png"), frame)
            captured += 1
            print(f"\r擷取中：{captured}/{count}", end="", flush=True)
            for _ in range(max(0, int(interval_sec * fps) - 1)):
                cap.grab()
    except KeyboardInterrupt:
        print("\n使用者中斷")
    finally:
        cap.release()
        print(f"\n完成：{captured} 幀 → {frame_dir}")


def main():
    parser = argparse.ArgumentParser(description="Tapo C230 星空攝影 — 擷取多幀（原始影像）")
    parser.add_argument("-u", "--url", help="RTSP URL（或從 .env 讀取 TAPO_RTSP_URL）")
    parser.add_argument("-o", "--output", default="starfield_frames", help="輸出目錄")
    parser.add_argument("-i", "--interval", type=float, default=2.0, help="擷取間隔（秒）")
    parser.add_argument("-n", "--count", type=int, default=100, help="擷取幀數")
    args = parser.parse_args()

    rtsp_url = args.url
    if not rtsp_url:
        try:
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).resolve().parent / ".env")
        except ImportError:
            pass
        rtsp_url = os.environ.get("TAPO_RTSP_URL")

    if not rtsp_url:
        print("錯誤：請提供 RTSP URL（-u 參數或 .env 中的 TAPO_RTSP_URL）")
        return

    capture(rtsp_url, args.output, args.interval, args.count)


if __name__ == "__main__":
    main()

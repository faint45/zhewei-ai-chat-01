#!/usr/bin/env python3
"""星空攝影擷取 — 套用虛擬參數與 AI 輔助"""
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"

import argparse
import cv2
from datetime import datetime
from pathlib import Path
from virtual_cam_params import VirtualParams, apply_params


def capture_with_params(rtsp_url, output_dir="starfield_frames", interval_sec=2.0,
                        count=100, params: VirtualParams = None):
    if params is None:
        params = VirtualParams()
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
            processed = apply_params(frame, params)
            cv2.imwrite(str(frame_dir / f"frame_{captured:05d}.png"), processed)
            captured += 1
            print(f"\r擷取中（含參數處理）：{captured}/{count}", end="", flush=True)
            for _ in range(max(0, int(interval_sec * fps) - 1)):
                cap.grab()
    except KeyboardInterrupt:
        print("\n使用者中斷")
    finally:
        cap.release()
        print(f"\n完成：{captured} 幀 → {frame_dir}")
        print(f"參數：brightness={params.brightness}, contrast={params.contrast}, "
              f"gamma={params.gamma}, saturation={params.saturation}, "
              f"sharpen={params.sharpen}, denoise={params.denoise}, "
              f"clahe={params.clahe}, star_mode={params.star_mode}")


def main():
    parser = argparse.ArgumentParser(description="星空攝影擷取 — 套用虛擬參數與 AI 輔助")
    parser.add_argument("-u", "--url", help="RTSP URL（或從 .env 讀取 TAPO_RTSP_URL）")
    parser.add_argument("-o", "--output", default="starfield_frames", help="輸出目錄")
    parser.add_argument("-i", "--interval", type=float, default=2.0, help="擷取間隔（秒）")
    parser.add_argument("-n", "--count", type=int, default=100, help="擷取幀數")
    parser.add_argument("--brightness", type=float, default=0.0, help="亮度 (-100~100)")
    parser.add_argument("--contrast", type=float, default=1.0, help="對比 (0.5~2.0)")
    parser.add_argument("--gamma", type=float, default=1.0, help="伽瑪 (0.5~2.0)")
    parser.add_argument("--saturation", type=float, default=1.0, help="飽和度 (0.0~2.0)")
    parser.add_argument("--sharpen", type=float, default=0.0, help="銳利度 (0~1)")
    parser.add_argument("--denoise", action="store_true", help="啟用降噪")
    parser.add_argument("--clahe", action="store_true", help="啟用 CLAHE 自適應對比")
    parser.add_argument("--star-mode", action="store_true", help="啟用星空增強模式")
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

    params = VirtualParams(
        brightness=args.brightness, contrast=args.contrast, gamma=args.gamma,
        saturation=args.saturation, sharpen=args.sharpen,
        denoise=args.denoise, clahe=args.clahe, star_mode=args.star_mode
    )
    capture_with_params(rtsp_url, args.output, args.interval, args.count, params)


if __name__ == "__main__":
    main()

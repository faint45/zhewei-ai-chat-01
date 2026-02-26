#!/usr/bin/env python3
"""
星空攝影 — 縮時攝影輸出
功能：
  - 幀序列合成 MP4 縮時影片
  - 可選 FPS、解析度、codec
  - 支援自動曝光過濾（跳過過亮幀）
  - 支援套用虛擬參數
  - 支援加入時間戳浮水印
"""

import argparse
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

from advanced_stack import load_images, frame_brightness


def create_timelapse(input_dir: str, output_path: str = None,
                     pattern: str = "*.png",
                     fps: int = 24,
                     width: int = 0, height: int = 0,
                     codec: str = "mp4v",
                     max_brightness: float = 0,
                     min_brightness: float = 0,
                     add_timestamp: bool = False,
                     apply_processing=None,
                     max_count: int = 0) -> dict:
    """
    將幀序列合成縮時影片

    apply_processing: 可選的處理函式 (frame) -> frame
    """
    print(f"=== 縮時攝影合成 ===")
    files, imgs = load_images(input_dir, pattern, max_count)
    if len(imgs) < 2:
        raise ValueError(f"影像不足：找到 {len(imgs)} 張")
    print(f"載入 {len(imgs)} 張影像")

    report = {
        "input_dir": str(input_dir),
        "total_frames": len(imgs),
        "fps": fps,
        "codec": codec,
        "timestamp": datetime.now().isoformat()
    }

    # 曝光過濾
    if max_brightness > 0 or min_brightness > 0:
        max_b = max_brightness if max_brightness > 0 else 255
        min_b = min_brightness if min_brightness > 0 else 0
        filtered = []
        rejected = 0
        for img in imgs:
            b = frame_brightness(img)
            if min_b <= b <= max_b:
                filtered.append(img)
            else:
                rejected += 1
        imgs = filtered
        report["brightness_filtered"] = rejected
        print(f"曝光過濾：排除 {rejected} 幀，保留 {len(imgs)} 幀")
        if len(imgs) < 2:
            raise ValueError("過濾後影像不足")

    # 決定解析度
    sample_h, sample_w = imgs[0].shape[:2]
    if width > 0 and height > 0:
        out_w, out_h = width, height
    elif width > 0:
        ratio = width / sample_w
        out_w, out_h = width, int(sample_h * ratio)
    elif height > 0:
        ratio = height / sample_h
        out_w, out_h = int(sample_w * ratio), height
    else:
        out_w, out_h = sample_w, sample_h

    report["resolution"] = f"{out_w}x{out_h}"

    # 輸出路徑
    if output_path is None:
        output_path = str(Path(input_dir).parent /
                          f"{Path(input_dir).name}_timelapse.mp4")

    # 建立 VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(output_path, fourcc, fps, (out_w, out_h))
    if not writer.isOpened():
        raise RuntimeError(f"無法建立影片寫入器：{output_path}")

    written = 0
    for i, img in enumerate(imgs):
        frame = img
        # 套用處理
        if apply_processing:
            frame = apply_processing(frame)
        # 縮放
        if (frame.shape[1], frame.shape[0]) != (out_w, out_h):
            frame = cv2.resize(frame, (out_w, out_h))
        # 時間戳浮水印
        if add_timestamp:
            ts_text = f"Frame {i+1}/{len(imgs)}"
            cv2.putText(frame, ts_text, (10, out_h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1,
                        cv2.LINE_AA)
        writer.write(frame)
        written += 1
        if (i + 1) % 50 == 0:
            print(f"  寫入進度：{i+1}/{len(imgs)}")

    writer.release()
    report["frames_written"] = written
    report["output"] = output_path
    duration = written / fps
    report["duration_sec"] = round(duration, 2)
    print(f"✅ 縮時影片完成 → {output_path}")
    print(f"   {written} 幀 @ {fps}fps = {duration:.1f} 秒")
    return report


def create_startrail_video(input_dir: str, output_path: str = None,
                           pattern: str = "*.png",
                           fps: int = 24,
                           width: int = 0, height: int = 0,
                           codec: str = "mp4v",
                           mode: str = "accumulate",
                           decay: float = 0.95,
                           max_count: int = 0) -> dict:
    """
    星軌生成過程影片 — 逐幀累積顯示星軌形成過程

    mode:
      - accumulate: 逐幀取 max 累積
      - fade: 帶衰減的累積效果
    """
    print(f"=== 星軌生成影片 ===")
    files, imgs = load_images(input_dir, pattern, max_count)
    if len(imgs) < 2:
        raise ValueError(f"影像不足：找到 {len(imgs)} 張")

    sample_h, sample_w = imgs[0].shape[:2]
    if width > 0 and height > 0:
        out_w, out_h = width, height
    else:
        out_w, out_h = sample_w, sample_h

    if output_path is None:
        output_path = str(Path(input_dir).parent /
                          f"{Path(input_dir).name}_startrail_video.mp4")

    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(output_path, fourcc, fps, (out_w, out_h))

    accumulator = imgs[0].astype(np.float32)
    for i, img in enumerate(imgs):
        current = img.astype(np.float32)
        if mode == "fade":
            accumulator = np.maximum(accumulator * decay, current)
        else:
            accumulator = np.maximum(accumulator, current)

        frame = np.clip(accumulator, 0, 255).astype(np.uint8)
        if (frame.shape[1], frame.shape[0]) != (out_w, out_h):
            frame = cv2.resize(frame, (out_w, out_h))

        # 進度文字
        progress_text = f"Trail: {i+1}/{len(imgs)}"
        cv2.putText(frame, progress_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 1,
                    cv2.LINE_AA)
        writer.write(frame)

        if (i + 1) % 20 == 0:
            print(f"  星軌影片進度：{i+1}/{len(imgs)}")

    writer.release()
    duration = len(imgs) / fps
    print(f"✅ 星軌影片完成 → {output_path}")
    print(f"   {len(imgs)} 幀 @ {fps}fps = {duration:.1f} 秒")

    return {"output": output_path, "frames": len(imgs),
            "duration_sec": round(duration, 2), "mode": mode}


def main():
    parser = argparse.ArgumentParser(description="星空攝影 — 縮時攝影 & 星軌影片")
    sub = parser.add_subparsers(dest="command", help="子命令")

    # 縮時
    tl = sub.add_parser("timelapse", help="幀序列合成縮時影片")
    tl.add_argument("input_dir", help="輸入幀目錄")
    tl.add_argument("-o", "--output", help="輸出檔案路徑")
    tl.add_argument("-p", "--pattern", default="*.png")
    tl.add_argument("--fps", type=int, default=24, help="影片 FPS（預設 24）")
    tl.add_argument("-W", "--width", type=int, default=0, help="輸出寬度（0=原始）")
    tl.add_argument("-H", "--height", type=int, default=0, help="輸出高度（0=原始）")
    tl.add_argument("--codec", default="mp4v", help="影片 codec（預設 mp4v）")
    tl.add_argument("--max-brightness", type=float, default=0,
                    help="最大亮度閾值（0=不過濾）")
    tl.add_argument("--min-brightness", type=float, default=0,
                    help="最小亮度閾值（0=不過濾）")
    tl.add_argument("--timestamp", action="store_true", help="加入幀編號浮水印")
    tl.add_argument("--max-count", type=int, default=0, help="最大幀數（0=全部）")

    # 星軌影片
    st = sub.add_parser("startrail", help="星軌生成過程影片")
    st.add_argument("input_dir", help="輸入幀目錄")
    st.add_argument("-o", "--output", help="輸出檔案路徑")
    st.add_argument("-p", "--pattern", default="*.png")
    st.add_argument("--fps", type=int, default=24)
    st.add_argument("-W", "--width", type=int, default=0)
    st.add_argument("-H", "--height", type=int, default=0)
    st.add_argument("--codec", default="mp4v")
    st.add_argument("--mode", choices=["accumulate", "fade"], default="accumulate",
                    help="星軌模式（預設 accumulate）")
    st.add_argument("--decay", type=float, default=0.95, help="漸變衰減係數")
    st.add_argument("--max-count", type=int, default=0)

    args = parser.parse_args()

    if args.command == "timelapse":
        create_timelapse(
            args.input_dir, args.output, args.pattern,
            args.fps, args.width, args.height, args.codec,
            args.max_brightness, args.min_brightness,
            args.timestamp, max_count=args.max_count
        )
    elif args.command == "startrail":
        create_startrail_video(
            args.input_dir, args.output, args.pattern,
            args.fps, args.width, args.height, args.codec,
            args.mode, args.decay, args.max_count
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

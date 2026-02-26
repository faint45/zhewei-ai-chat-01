#!/usr/bin/env python3
"""星空攝影 — 簡單疊圖"""
import argparse
import cv2
import numpy as np
from pathlib import Path


def stack_frames(input_dir, output_path=None, method="median", pattern="*.png"):
    files = sorted(Path(input_dir).glob(pattern))
    if len(files) < 2:
        raise ValueError("至少需要 2 張影像")
    imgs = [cv2.imread(str(f)) for f in files if cv2.imread(str(f)) is not None]
    if len(imgs) < 2:
        raise ValueError(f"可讀取的影像不足 2 張（找到 {len(imgs)} 張）")
    print(f"載入 {len(imgs)} 張影像，使用 {method} 疊圖...")
    stack = np.array(imgs, dtype=np.float32)
    if method == "median":
        result = np.median(stack, axis=0).astype(np.uint8)
    else:
        result = np.mean(stack, axis=0).astype(np.uint8)
    out = output_path or str(Path(input_dir).parent / f"{Path(input_dir).name}_stacked.png")
    cv2.imwrite(out, result)
    print(f"疊圖完成 → {out}")
    return out


def main():
    parser = argparse.ArgumentParser(description="星空攝影 — 簡單疊圖（median/mean）")
    parser.add_argument("input_dir", help="輸入幀目錄")
    parser.add_argument("-o", "--output", help="輸出檔案路徑")
    parser.add_argument("-m", "--method", choices=["median", "mean"], default="median",
                        help="疊圖方法（預設 median）")
    parser.add_argument("-p", "--pattern", default="*.png", help="檔案匹配模式")
    args = parser.parse_args()

    stack_frames(args.input_dir, args.output, args.method, args.pattern)


if __name__ == "__main__":
    main()

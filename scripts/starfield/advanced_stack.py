#!/usr/bin/env python3
"""
星空攝影 — 進階疊圖引擎
功能：
  - Sigma clipping（去除飛機/衛星軌跡等異常值）
  - Star alignment（星點對齊，補償地球自轉）
  - Star trails（星軌模式，max 疊圖 + 漸變尾巴）
  - Dark frame calibration（暗場校正，減去暗電流雜訊）
  - 自動曝光偵測（跳過過亮幀）
"""

import argparse
import json
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime


# ---------------------------------------------------------------------------
# 工具函式
# ---------------------------------------------------------------------------

def load_images(input_dir: str, pattern: str = "*.png", max_count: int = 0):
    """載入目錄中所有影像，回傳 (file_list, image_list)"""
    files = sorted(Path(input_dir).glob(pattern))
    if max_count > 0:
        files = files[:max_count]
    imgs = []
    valid_files = []
    for f in files:
        img = cv2.imread(str(f))
        if img is not None:
            imgs.append(img)
            valid_files.append(f)
    return valid_files, imgs


def frame_brightness(img: np.ndarray) -> float:
    """計算影像平均亮度 (0~255)"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    return float(np.mean(gray))


def filter_bright_frames(imgs: list, files: list = None,
                         max_brightness: float = 80.0,
                         min_brightness: float = 5.0):
    """過濾過亮/過暗的幀，回傳 (filtered_imgs, filtered_files, report)"""
    filtered_imgs = []
    filtered_files = []
    report = {"total": len(imgs), "kept": 0, "rejected_bright": 0,
              "rejected_dark": 0, "brightness_values": []}

    for i, img in enumerate(imgs):
        b = frame_brightness(img)
        report["brightness_values"].append(round(b, 2))
        if b > max_brightness:
            report["rejected_bright"] += 1
        elif b < min_brightness:
            report["rejected_dark"] += 1
        else:
            filtered_imgs.append(img)
            if files:
                filtered_files.append(files[i])

    report["kept"] = len(filtered_imgs)
    return filtered_imgs, filtered_files, report


# ---------------------------------------------------------------------------
# Dark Frame Calibration
# ---------------------------------------------------------------------------

def create_master_dark(dark_dir: str, pattern: str = "*.png") -> np.ndarray:
    """從暗場目錄建立 master dark frame（中位數疊合）"""
    _, darks = load_images(dark_dir, pattern)
    if len(darks) < 1:
        raise ValueError(f"暗場目錄中找不到影像：{dark_dir}")
    print(f"建立 Master Dark：{len(darks)} 張暗場影像")
    stack = np.array(darks, dtype=np.float32)
    master = np.median(stack, axis=0)
    return master


def apply_dark_calibration(imgs: list, master_dark: np.ndarray) -> list:
    """對每張影像減去 master dark"""
    calibrated = []
    for img in imgs:
        result = img.astype(np.float32) - master_dark
        result = np.clip(result, 0, 255).astype(np.uint8)
        calibrated.append(result)
    return calibrated


# ---------------------------------------------------------------------------
# Sigma Clipping Stack
# ---------------------------------------------------------------------------

def sigma_clip_stack(imgs: list, sigma: float = 2.5, iterations: int = 3) -> np.ndarray:
    """
    Sigma clipping 疊圖 — 逐像素去除超過 sigma 倍標準差的異常值後取平均
    有效去除飛機、衛星、流星等短暫亮點
    """
    if len(imgs) < 3:
        print("⚠️ Sigma clipping 需要至少 3 張影像，改用 median")
        stack = np.array(imgs, dtype=np.float32)
        return np.median(stack, axis=0).astype(np.uint8)

    stack = np.array(imgs, dtype=np.float32)  # (N, H, W, C)
    mask = np.ones(stack.shape, dtype=bool)    # True = 保留

    for iteration in range(iterations):
        masked = np.where(mask, stack, np.nan)
        with np.errstate(all='ignore'):
            mean = np.nanmean(masked, axis=0)   # (H, W, C)
            std = np.nanstd(masked, axis=0)      # (H, W, C)

        # 標記超出 sigma 倍標準差的像素
        lower = mean - sigma * std
        upper = mean + sigma * std
        new_mask = (stack >= lower[np.newaxis]) & (stack <= upper[np.newaxis])
        # 確保每個像素至少保留 2 個值
        count = new_mask.sum(axis=0)
        too_few = count < 2
        if too_few.any():
            new_mask[:, too_few] = mask[:, too_few]
        changed = (mask != new_mask).sum()
        mask = new_mask
        print(f"  Sigma clip 迭代 {iteration+1}/{iterations}：排除 {(~mask).sum()} 個像素值")
        if changed == 0:
            break

    masked = np.where(mask, stack, np.nan)
    with np.errstate(all='ignore'):
        result = np.nanmean(masked, axis=0)
    result = np.clip(result, 0, 255).astype(np.uint8)
    return result


# ---------------------------------------------------------------------------
# Star Alignment
# ---------------------------------------------------------------------------

def detect_stars(gray: np.ndarray, max_stars: int = 200) -> np.ndarray:
    """偵測星點，回傳 keypoints 座標陣列 (N, 2)"""
    # 用 ORB 偵測亮點特徵
    orb = cv2.ORB_create(nfeatures=max_stars)
    # 先做閾值處理突出星點
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kps, des = orb.detectAndCompute(gray, None)
    if kps is None or len(kps) == 0:
        return np.array([]), None
    pts = np.array([kp.pt for kp in kps], dtype=np.float32)
    return pts, des


def align_to_reference(imgs: list, ref_index: int = 0) -> list:
    """
    以第一張為基準，對齊所有影像（使用 ORB 特徵匹配 + Homography）
    適用於補償地球自轉造成的星點位移
    """
    if len(imgs) < 2:
        return imgs

    ref = cv2.cvtColor(imgs[ref_index], cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=500)
    ref_kps, ref_des = orb.detectAndCompute(ref, None)

    if ref_des is None:
        print("⚠️ 基準影像無法偵測特徵點，跳過對齊")
        return imgs

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    aligned = []
    h, w = ref.shape[:2]
    success = 0

    for i, img in enumerate(imgs):
        if i == ref_index:
            aligned.append(img)
            success += 1
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        kps, des = orb.detectAndCompute(gray, None)

        if des is None or len(kps) < 4:
            print(f"  幀 {i}: 特徵點不足，使用原圖")
            aligned.append(img)
            continue

        matches = bf.knnMatch(des, ref_des, k=2)
        # Lowe's ratio test
        good = []
        for m_pair in matches:
            if len(m_pair) == 2:
                m, n = m_pair
                if m.distance < 0.75 * n.distance:
                    good.append(m)

        if len(good) < 4:
            print(f"  幀 {i}: 匹配點不足 ({len(good)})，使用原圖")
            aligned.append(img)
            continue

        src_pts = np.float32([kps[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([ref_kps[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

        M, mask_h = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if M is not None:
            warped = cv2.warpPerspective(img, M, (w, h))
            aligned.append(warped)
            success += 1
            if (i + 1) % 10 == 0:
                print(f"  對齊進度：{i+1}/{len(imgs)}")
        else:
            aligned.append(img)

    print(f"星點對齊完成：{success}/{len(imgs)} 張成功")
    return aligned


# ---------------------------------------------------------------------------
# Star Trails
# ---------------------------------------------------------------------------

def star_trails_max(imgs: list) -> np.ndarray:
    """星軌模式 — 取每像素最大值（經典星軌效果）"""
    result = imgs[0].astype(np.float32)
    for i in range(1, len(imgs)):
        result = np.maximum(result, imgs[i].astype(np.float32))
        if (i + 1) % 20 == 0:
            print(f"  星軌疊圖進度：{i+1}/{len(imgs)}")
    return np.clip(result, 0, 255).astype(np.uint8)


def star_trails_fade(imgs: list, decay: float = 0.95) -> np.ndarray:
    """
    星軌漸變模式 — 帶有漸變尾巴效果
    decay: 衰減係數 (0.9~0.99)，越大尾巴越長
    """
    result = imgs[0].astype(np.float32)
    trail = imgs[0].astype(np.float32)

    for i in range(1, len(imgs)):
        current = imgs[i].astype(np.float32)
        trail = np.maximum(trail * decay, current)
        result = np.maximum(result, trail)
        if (i + 1) % 20 == 0:
            print(f"  漸變星軌進度：{i+1}/{len(imgs)}")

    return np.clip(result, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# 主函式
# ---------------------------------------------------------------------------

def advanced_stack(input_dir: str, output_path: str = None,
                   method: str = "sigma_clip",
                   pattern: str = "*.png",
                   dark_dir: str = None,
                   sigma: float = 2.5,
                   sigma_iterations: int = 3,
                   align: bool = False,
                   max_brightness: float = 80.0,
                   min_brightness: float = 5.0,
                   trail_decay: float = 0.95,
                   max_count: int = 0) -> dict:
    """
    進階疊圖主函式

    method: sigma_clip | median | mean | star_trails | star_trails_fade
    """
    print(f"=== 進階疊圖引擎 ===")
    print(f"方法：{method}")
    print(f"輸入：{input_dir}")

    # 載入影像
    files, imgs = load_images(input_dir, pattern, max_count)
    if len(imgs) < 2:
        raise ValueError(f"影像不足：找到 {len(imgs)} 張，至少需要 2 張")
    print(f"載入 {len(imgs)} 張影像")

    report = {
        "method": method,
        "input_dir": str(input_dir),
        "total_frames": len(imgs),
        "timestamp": datetime.now().isoformat()
    }

    # 自動曝光過濾
    imgs, files, brightness_report = filter_bright_frames(
        imgs, files, max_brightness, min_brightness)
    report["brightness_filter"] = brightness_report
    if len(imgs) < 2:
        raise ValueError(f"過濾後影像不足：{brightness_report['kept']} 張")
    print(f"曝光過濾後：{len(imgs)} 張（排除 {brightness_report['rejected_bright']} 過亮、"
          f"{brightness_report['rejected_dark']} 過暗）")

    # Dark frame 校正
    if dark_dir:
        print(f"載入暗場校正：{dark_dir}")
        master_dark = create_master_dark(dark_dir, pattern)
        imgs = apply_dark_calibration(imgs, master_dark)
        report["dark_calibration"] = True
        # 儲存 master dark
        dark_out = str(Path(input_dir).parent / "master_dark.png")
        cv2.imwrite(dark_out, master_dark.astype(np.uint8))
        print(f"Master Dark 已儲存 → {dark_out}")

    # 星點對齊
    if align and method not in ("star_trails", "star_trails_fade"):
        print("執行星點對齊...")
        imgs = align_to_reference(imgs)
        report["alignment"] = True

    # 疊圖
    print(f"開始疊圖（{method}）...")
    if method == "sigma_clip":
        result = sigma_clip_stack(imgs, sigma, sigma_iterations)
    elif method == "median":
        stack = np.array(imgs, dtype=np.float32)
        result = np.median(stack, axis=0).astype(np.uint8)
    elif method == "mean":
        stack = np.array(imgs, dtype=np.float32)
        result = np.mean(stack, axis=0).astype(np.uint8)
    elif method == "star_trails":
        result = star_trails_max(imgs)
    elif method == "star_trails_fade":
        result = star_trails_fade(imgs, trail_decay)
    else:
        raise ValueError(f"不支援的方法：{method}")

    # 儲存結果
    if output_path is None:
        suffix = method.replace("_", "-")
        output_path = str(Path(input_dir).parent /
                          f"{Path(input_dir).name}_{suffix}.png")
    cv2.imwrite(output_path, result)
    report["output"] = output_path
    print(f"✅ 疊圖完成 → {output_path}")

    # 儲存報告
    report_path = output_path.replace(".png", "_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"報告 → {report_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="星空攝影 — 進階疊圖引擎")
    parser.add_argument("input_dir", help="輸入幀目錄")
    parser.add_argument("-o", "--output", help="輸出檔案路徑")
    parser.add_argument("-m", "--method", default="sigma_clip",
                        choices=["sigma_clip", "median", "mean",
                                 "star_trails", "star_trails_fade"],
                        help="疊圖方法（預設 sigma_clip）")
    parser.add_argument("-p", "--pattern", default="*.png", help="檔案匹配模式")
    parser.add_argument("--dark-dir", help="暗場影像目錄（用於 dark frame 校正）")
    parser.add_argument("--sigma", type=float, default=2.5,
                        help="Sigma clipping 閾值（預設 2.5）")
    parser.add_argument("--sigma-iter", type=int, default=3,
                        help="Sigma clipping 迭代次數（預設 3）")
    parser.add_argument("--align", action="store_true",
                        help="啟用星點對齊（補償地球自轉）")
    parser.add_argument("--max-brightness", type=float, default=80.0,
                        help="最大亮度閾值（超過則排除，預設 80）")
    parser.add_argument("--min-brightness", type=float, default=5.0,
                        help="最小亮度閾值（低於則排除，預設 5）")
    parser.add_argument("--trail-decay", type=float, default=0.95,
                        help="星軌漸變衰減係數（預設 0.95）")
    parser.add_argument("--max-count", type=int, default=0,
                        help="最大載入幀數（0=全部）")
    args = parser.parse_args()

    advanced_stack(
        args.input_dir, args.output, args.method, args.pattern,
        args.dark_dir, args.sigma, args.sigma_iter, args.align,
        args.max_brightness, args.min_brightness, args.trail_decay,
        args.max_count
    )


if __name__ == "__main__":
    main()

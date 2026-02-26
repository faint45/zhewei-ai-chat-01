#!/usr/bin/env python3
"""
虛擬參數 + AI 輔助 — Tapo C230 即時影片處理
可調整：亮度、對比、伽瑪、飽和度、銳利度
AI 輔助：降噪、CLAHE 自適應對比、星空增強模式
"""

import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"

import argparse
import cv2
import numpy as np
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VirtualParams:
    brightness: float = 0.0      # -100 ~ 100
    contrast: float = 1.0        # 0.5 ~ 2.0
    gamma: float = 1.0           # 0.5 ~ 2.0
    saturation: float = 1.0      # 0.0 ~ 2.0
    sharpen: float = 0.0         # 0 ~ 1
    denoise: bool = False
    denoise_strength: int = 6    # NLMeans h 參數 (3=輕, 6=中, 12=強)
    clahe: bool = False
    clahe_clip: float = 2.0      # CLAHE clipLimit
    clahe_grid: int = 8          # CLAHE tileGridSize
    star_mode: bool = False
    temporal_denoise: bool = False  # 時域降噪（多幀累積）
    temporal_weight: float = 0.7    # 時域混合權重（越高=越平滑）


# --- 預設模式 ---

def night_sky_preset() -> "VirtualParams":
    """
    夜空優化預設 — 模擬大光圈 + ISO 50
    - 亮度 +15：模擬光圈加大，暗部提亮
    - 伽瑪 1.4：非線性提亮暗部，保留亮部細節
    - 對比 1.15：輕微增強星點與背景對比
    - CLAHE：自適應局部對比增強（讓暗區星點更明顯）
    - 強力降噪 h=10：模擬 ISO 50 低雜訊
    - 時域降噪：多幀累積平滑，進一步壓制隨機雜訊
    - 銳利度 0.3：補償降噪後的細節損失
    """
    return VirtualParams(
        brightness=15,
        contrast=1.15,
        gamma=1.4,
        saturation=1.1,
        sharpen=0.3,
        denoise=True,
        denoise_strength=10,
        clahe=True,
        clahe_clip=3.0,
        clahe_grid=4,
        star_mode=False,
        temporal_denoise=True,
        temporal_weight=0.6,
    )


def starfield_preset() -> "VirtualParams":
    """星空攝影預設 — 最大化星點可見度"""
    return VirtualParams(
        brightness=20,
        contrast=1.2,
        gamma=1.6,
        saturation=1.3,
        sharpen=0.4,
        denoise=True,
        denoise_strength=8,
        clahe=True,
        clahe_clip=3.5,
        clahe_grid=4,
        star_mode=True,
        temporal_denoise=True,
        temporal_weight=0.5,
    )


def daytime_preset() -> "VirtualParams":
    """白天模式 — 降低亮度避免過曝，輕微降噪"""
    return VirtualParams(
        brightness=-10,
        contrast=1.05,
        gamma=0.85,
        saturation=1.0,
        sharpen=0.2,
        denoise=True,
        denoise_strength=4,
        clahe=False,
        star_mode=False,
        temporal_denoise=False,
    )


def raw_preset() -> "VirtualParams":
    """原始模式 — 不做任何處理"""
    return VirtualParams()


def stacked_raw_preset() -> "VirtualParams":
    """原始疊加模式 — 不調色，純靠多幀疊加消除雜訊"""
    return VirtualParams()  # 參數全預設，疊加由外部處理


def ai_enhanced_preset() -> "VirtualParams":
    """AI 增強模式 — 多幀疊加 + AI 輔助（雙邊濾波+CLAHE+USM）"""
    return VirtualParams()  # 參數全預設，增強由外部處理


def apply_stacked(frame: np.ndarray) -> np.ndarray:
    """原始疊加降噪 — 將幀加入 buffer 並回傳疊加結果"""
    return _stacker.add_frame(frame)


def apply_ai_enhanced(frame: np.ndarray) -> np.ndarray:
    """漸進式增強 — 每 16 幀合併+AI增強，畫質越來越好"""
    return _progressive.process(frame)


def get_stack_depth() -> int:
    """取得目前疊加深度"""
    return max(_stacker.current_depth, _progressive.current_depth)


def get_smart_info() -> dict:
    """取得增強器的狀態資訊"""
    info = _progressive.get_info()
    return {
        "strategy": f"R{info['round']} ({info['buffer']}/{info['buffer_max']})",
        "noise_level": info.get("noise_after", 0),
        "stack_depth": info["buffer"],
    }


def get_progressive_info() -> dict:
    """取得漸進式增強器的完整狀態"""
    return _progressive.get_info()


def auto_select_preset(frame: np.ndarray) -> str:
    """
    根據畫面平均亮度自動選擇預設模式
    回傳預設名稱：'night_sky' / 'daytime' / 'starfield'
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
    avg = float(np.mean(gray))
    if avg > 100:       # 白天（亮）
        return "daytime"
    elif avg > 30:      # 黃昏/光害
        return "night_sky"
    else:               # 深夜（暗）
        return "starfield"


class TemporalDenoiser:
    """時域降噪器 — 多幀加權累積，模擬長曝光低 ISO 效果"""

    def __init__(self):
        self._acc = None

    def process(self, frame: np.ndarray, weight: float = 0.6) -> np.ndarray:
        f = frame.astype(np.float64)
        if self._acc is None or self._acc.shape != f.shape:
            self._acc = f
        else:
            self._acc = self._acc * weight + f * (1 - weight)
        return np.clip(self._acc, 0, 255).astype(np.uint8)

    def reset(self):
        self._acc = None


class FrameStackDenoiser:
    """
    多幀疊加降噪器 — 累積 N 幀後取平均值
    原理：隨機雜訊在多幀間不相關，疊加後雜訊 ∝ 1/√N
    """

    def __init__(self, stack_size: int = 16, method: str = "mean"):
        self.stack_size = stack_size
        self.method = method
        self._buffer = []

    def add_frame(self, frame: np.ndarray) -> np.ndarray:
        self._buffer.append(frame.astype(np.float32))
        if len(self._buffer) > self.stack_size:
            self._buffer.pop(0)
        if len(self._buffer) < 2:
            return frame
        stack = np.array(self._buffer)
        if self.method == "median":
            result = np.median(stack, axis=0)
        else:
            result = np.mean(stack, axis=0)
        return np.clip(result, 0, 255).astype(np.uint8)

    @property
    def current_depth(self) -> int:
        return len(self._buffer)

    def reset(self):
        self._buffer.clear()


def estimate_noise(frame: np.ndarray) -> float:
    """
    估算影像雜訊量（Laplacian 方差法）
    回傳值越高 = 雜訊/細節越多
    - < 50：非常乾淨（白天好光線）
    - 50~200：中等（室內/陰天）
    - 200~500：高雜訊（夜間/低光）
    - > 500：極高雜訊（深夜無光）
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


class SmartEnhancer:
    """
    智慧畫質增強器 — 根據場景自動選擇最佳策略
    
    白天（亮、低雜訊）：
      → 不疊加（沒意義）
      → 輕微雙邊濾波 + 強 USM 銳化 + 色彩增強
      → 效果：畫面更銳利、色彩更鮮豔
    
    夜間（暗、高雜訊）：
      → 深度疊加（8~16 幀）
      → 強力雙邊濾波 + CLAHE 暗部提亮
      → 效果：雜訊大幅降低、暗部細節浮現
    """

    def __init__(self):
        self._stacker = FrameStackDenoiser(stack_size=16, method="mean")
        self._noise_level = 0.0
        self._brightness = 128.0
        self._strategy = "bright"  # "bright" / "medium" / "dark"
        self._frame_count = 0

    def process(self, frame: np.ndarray) -> np.ndarray:
        self._frame_count += 1

        # 每 30 幀重新評估場景
        if self._frame_count % 30 == 1:
            self._noise_level = estimate_noise(frame)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            self._brightness = float(np.mean(gray))
            if self._brightness > 100:
                self._strategy = "bright"
            elif self._brightness > 40:
                self._strategy = "medium"
            else:
                self._strategy = "dark"

        if self._strategy == "bright":
            return self._enhance_bright(frame)
        elif self._strategy == "medium":
            return self._enhance_medium(frame)
        else:
            return self._enhance_dark(frame)

    def _enhance_bright(self, frame: np.ndarray) -> np.ndarray:
        """白天策略：銳化 + 色彩增強 + 輕微降噪"""
        out = frame.copy()

        # 輕微雙邊濾波（保邊去噪，不模糊）
        out = cv2.bilateralFilter(out, d=5, sigmaColor=30, sigmaSpace=30)

        # 色彩增強 — 飽和度 +15%
        hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.15, 0, 255)
        out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # 強 USM 銳化 — 讓細節更清晰
        blur = cv2.GaussianBlur(out, (0, 0), 1.5)
        out = cv2.addWeighted(out, 1.8, blur, -0.8, 0)

        # 對比微調
        out = np.clip(out.astype(np.float32) * 1.05 - 6, 0, 255).astype(np.uint8)

        return out

    def _enhance_medium(self, frame: np.ndarray) -> np.ndarray:
        """黃昏/室內策略：輕度疊加 + 降噪 + CLAHE"""
        # 4 幀疊加
        self._stacker.stack_size = 4
        out = self._stacker.add_frame(frame)

        # 雙邊濾波
        out = cv2.bilateralFilter(out, d=7, sigmaColor=40, sigmaSpace=40)

        # CLAHE 提亮暗部
        lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        out = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

        # USM 銳化
        blur = cv2.GaussianBlur(out, (0, 0), 2.0)
        out = cv2.addWeighted(out, 1.5, blur, -0.5, 0)

        return np.clip(out, 0, 255).astype(np.uint8)

    def _enhance_dark(self, frame: np.ndarray) -> np.ndarray:
        """夜間策略：深度疊加 + 強力降噪 + CLAHE + 伽瑪提亮"""
        # 16 幀疊加
        self._stacker.stack_size = 16
        out = self._stacker.add_frame(frame)

        # 強力雙邊濾波
        out = cv2.bilateralFilter(out, d=9, sigmaColor=75, sigmaSpace=75)

        # CLAHE 強力提亮暗部
        lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
        l = clahe.apply(l)
        out = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

        # 伽瑪提亮
        out = (255 * np.power(out.astype(np.float32) / 255.0, 1.0 / 1.3))
        out = np.clip(out, 0, 255).astype(np.uint8)

        # USM 銳化（補償降噪模糊）
        blur = cv2.GaussianBlur(out, (0, 0), 2.0)
        out = cv2.addWeighted(out, 1.4, blur, -0.4, 0)

        return np.clip(out, 0, 255).astype(np.uint8)

    @property
    def current_depth(self) -> int:
        return self._stacker.current_depth

    @property
    def strategy(self) -> str:
        return self._strategy

    @property
    def noise_level(self) -> float:
        return self._noise_level

    def reset(self):
        self._stacker.reset()
        self._frame_count = 0


class ProgressiveEnhancer:
    """
    漸進式增強器 — 疊加 + AI 整合，畫質越來越好
    
    流程：
    1. 收集 16 幀 → 合併（mean stack）
    2. 對合併結果做 AI 增強（降噪+CLAHE+銳化）
    3. 將增強結果混入「主基底」（master）
       master = master * blend + enhanced * (1-blend)
       blend 隨輪次遞減：0.3 → 0.5 → 0.6 → 0.7（越後面新幀權重越低）
    4. 下一輪繼續收集 16 幀，重複
    
    效果：
    - 第 1 輪（16 幀）：基礎降噪，雜訊↓75%
    - 第 2 輪（32 幀）：進一步平滑，等效 32 幀疊加
    - 第 3 輪（48 幀）：接近極限，雜訊↓90%+
    - 第 4 輪+：微調，畫質趨於穩定
    
    畫質分數（0~100）：
    - 基於 PSNR 估算，越高越好
    """

    def __init__(self, stack_size: int = 16):
        self.stack_size = stack_size
        self._buffer = []
        self._master = None       # 主基底（float64）
        self._display = None      # 當前顯示幀（uint8）
        self._round = 0           # 已完成的合併輪次
        self._total_frames = 0    # 總收集幀數
        self._quality_score = 0.0 # 畫質分數 0~100
        self._noise_before = 0.0  # 增強前雜訊
        self._noise_after = 0.0   # 增強後雜訊

    def process(self, frame: np.ndarray) -> np.ndarray:
        self._total_frames += 1
        self._buffer.append(frame.astype(np.float64))

        # 還沒收滿 → 即時預覽（用目前已收集的幀做臨時疊加）
        if len(self._buffer) < self.stack_size:
            preview = np.mean(np.array(self._buffer), axis=0)
            preview = np.clip(preview, 0, 255).astype(np.uint8)
            if self._master is not None:
                # 混合主基底和臨時預覽
                w = min(0.7, 0.3 + self._round * 0.1)
                blended = self._master * w + preview.astype(np.float64) * (1 - w)
                preview = np.clip(blended, 0, 255).astype(np.uint8)
            preview = self._ai_enhance(preview)
            self._display = preview
            return preview

        # 收滿 16 幀 → 合併 + AI 增強 + 混入主基底
        stack = np.array(self._buffer)
        merged = np.mean(stack, axis=0)
        self._buffer.clear()

        # 記錄增強前雜訊
        merged_u8 = np.clip(merged, 0, 255).astype(np.uint8)
        self._noise_before = estimate_noise(merged_u8)

        # AI 增強
        enhanced = self._ai_enhance(merged_u8)

        # 記錄增強後雜訊
        self._noise_after = estimate_noise(enhanced)

        # 混入主基底
        enhanced_f = enhanced.astype(np.float64)
        if self._master is None:
            self._master = enhanced_f
        else:
            # 隨輪次增加主基底權重（越後面越穩定）
            w = min(0.8, 0.3 + self._round * 0.15)
            self._master = self._master * w + enhanced_f * (1 - w)

        self._round += 1
        self._display = np.clip(self._master, 0, 255).astype(np.uint8)

        # 計算畫質分數
        self._update_quality_score()

        return self._display

    def _ai_enhance(self, frame: np.ndarray) -> np.ndarray:
        """AI 增強流水線（根據亮度自動調整強度）"""
        out = frame.copy()
        gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))

        # 降噪強度根據亮度調整
        if brightness < 40:
            # 夜間：強力降噪
            out = cv2.bilateralFilter(out, d=9, sigmaColor=75, sigmaSpace=75)
            clip = 4.0
            gamma = 1.3
        elif brightness < 100:
            # 黃昏：中等降噪
            out = cv2.bilateralFilter(out, d=7, sigmaColor=50, sigmaSpace=50)
            clip = 2.5
            gamma = 1.1
        else:
            # 白天：輕微降噪
            out = cv2.bilateralFilter(out, d=5, sigmaColor=30, sigmaSpace=30)
            clip = 1.5
            gamma = 1.0

        # CLAHE 自適應對比
        lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(4, 4))
        l = clahe.apply(l)
        out = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

        # 伽瑪校正（夜間提亮）
        if gamma != 1.0:
            out = (255 * np.power(out.astype(np.float32) / 255.0, 1.0 / gamma))
            out = np.clip(out, 0, 255).astype(np.uint8)

        # USM 銳化
        blur = cv2.GaussianBlur(out, (0, 0), 1.5)
        out = cv2.addWeighted(out, 1.5, blur, -0.5, 0)

        # 色彩增強
        hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.1, 0, 255)
        out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        return np.clip(out, 0, 255).astype(np.uint8)

    def _update_quality_score(self):
        """根據雜訊降低比例估算畫質分數"""
        if self._noise_before > 0:
            reduction = 1 - (self._noise_after / self._noise_before)
            # 基礎分 + 輪次加成 + 降噪加成
            base = min(40, self._round * 15)
            denoise_bonus = max(0, reduction * 40)
            round_bonus = min(20, self._round * 5)
            self._quality_score = min(100, base + denoise_bonus + round_bonus)
        else:
            self._quality_score = min(100, self._round * 20)

    @property
    def current_depth(self) -> int:
        return len(self._buffer)

    @property
    def round_count(self) -> int:
        return self._round

    @property
    def total_frames(self) -> int:
        return self._total_frames

    @property
    def quality_score(self) -> float:
        return round(self._quality_score, 1)

    def get_info(self) -> dict:
        return {
            "round": self._round,
            "buffer": len(self._buffer),
            "buffer_max": self.stack_size,
            "total_frames": self._total_frames,
            "quality_score": self.quality_score,
            "noise_before": round(self._noise_before, 1),
            "noise_after": round(self._noise_after, 1),
        }

    def reset(self):
        self._buffer.clear()
        self._master = None
        self._display = None
        self._round = 0
        self._total_frames = 0
        self._quality_score = 0.0


# 向後相容
AIEnhancer = SmartEnhancer


_temporal = TemporalDenoiser()
_stacker = FrameStackDenoiser(stack_size=16, method="mean")
_smart = SmartEnhancer()
_progressive = ProgressiveEnhancer(stack_size=16)


def apply_params(frame: np.ndarray, p: VirtualParams) -> np.ndarray:
    out = frame.astype(np.float32)
    if p.brightness != 0:
        out = np.clip(out + p.brightness, 0, 255)
    if p.contrast != 1.0:
        out = np.clip((out - 127.5) * p.contrast + 127.5, 0, 255)
    if p.gamma != 1.0:
        out = 255 * np.power(out / 255.0, 1.0 / p.gamma)
    out = np.clip(out, 0, 255).astype(np.uint8)
    if p.saturation != 1.0:
        hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * p.saturation, 0, 255)
        out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    if p.sharpen > 0:
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
        kernel = kernel * p.sharpen + (1 - p.sharpen) * np.eye(3)
        out = cv2.filter2D(out, -1, kernel)
        out = np.clip(out, 0, 255).astype(np.uint8)
    if p.denoise:
        h = p.denoise_strength
        out = cv2.fastNlMeansDenoisingColored(out, None, h, h, 7, 21)
    if p.clahe:
        lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=p.clahe_clip, tileGridSize=(p.clahe_grid, p.clahe_grid))
        l = clahe.apply(l)
        out = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    if p.star_mode:
        out = cv2.cvtColor(out, cv2.COLOR_BGR2Lab)
        l, a, b = cv2.split(out)
        l = np.clip(l.astype(np.float32) * 1.2 - 10, 0, 255).astype(np.uint8)
        out = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_Lab2BGR)
    if p.temporal_denoise:
        out = _temporal.process(out, p.temporal_weight)
    return out


def run_interactive(rtsp_url: str, width: int = 640, height: int = 480) -> None:
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("錯誤：無法開啟 RTSP 串流")
        return
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    ret, _ = cap.read()
    if not ret:
        print("錯誤：無法讀取 RTSP 畫面")
        cap.release()
        return
    vals = {"b": 100, "c": 100, "g": 100, "s": 100, "sh": 0, "dn": 0, "cl": 0, "st": 0}
    def make_params():
        c = 0.5 + (min(200, max(50, vals["c"])) - 50) / 100.0
        g = 0.5 + (min(200, max(50, vals["g"])) - 50) / 100.0
        return VirtualParams(brightness=(vals["b"]-100), contrast=c, gamma=g,
            saturation=vals["s"]/100, sharpen=vals["sh"]/100,
            denoise=bool(vals["dn"]), clahe=bool(vals["cl"]), star_mode=bool(vals["st"]))
    win_name = "Tapo Camera | Press Q to quit"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, width + 20, height + 120)
    cv2.createTrackbar("Brightness", win_name, 100, 200, lambda v: vals.update({"b": v}))
    cv2.createTrackbar("Contrast", win_name, 100, 200, lambda v: vals.update({"c": v}))
    cv2.createTrackbar("Gamma", win_name, 100, 200, lambda v: vals.update({"g": v}))
    cv2.createTrackbar("Saturation", win_name, 100, 200, lambda v: vals.update({"s": v}))
    cv2.createTrackbar("Sharpen", win_name, 0, 100, lambda v: vals.update({"sh": v}))
    cv2.createTrackbar("Denoise 0/1", win_name, 0, 1, lambda v: vals.update({"dn": v}))
    cv2.createTrackbar("CLAHE 0/1", win_name, 0, 1, lambda v: vals.update({"cl": v}))
    cv2.createTrackbar("Star Mode 0/1", win_name, 0, 1, lambda v: vals.update({"st": v}))
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                cap.release()
                cap = cv2.VideoCapture(rtsp_url)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                continue
            frame = cv2.resize(frame, (width, height))
            out = apply_params(frame, make_params())
            cv2.imshow(win_name, out)
            if cv2.waitKey(30) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Tapo C230 虛擬參數即時影片處理")
    parser.add_argument("-u", "--url", help="RTSP URL（或從 .env 讀取 TAPO_RTSP_URL）")
    parser.add_argument("-i", "--interactive", action="store_true", help="互動模式（滑桿調整）")
    parser.add_argument("--no-vcam", action="store_true", help="不啟動虛擬攝影機")
    parser.add_argument("-W", "--width", type=int, default=640, help="畫面寬度")
    parser.add_argument("-H", "--height", type=int, default=480, help="畫面高度")
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

    if args.interactive:
        run_interactive(rtsp_url, args.width, args.height)
    else:
        print("請使用 -i 啟動互動模式")
        print("範例：python virtual_cam_params.py -i --no-vcam")


if __name__ == "__main__":
    main()

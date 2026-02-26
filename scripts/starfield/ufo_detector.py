#!/usr/bin/env python3
"""
UFO 偵測引擎 — Tapo C230 夜空不明飛行物偵測
核心演算法：
  1. 背景建模（星空靜態背景）— 累積平均 or MOG2
  2. 前景偵測（移動物體提取）— 背景差分 + 形態學
  3. 星點排除 — 靜態亮點過濾（星星不動）
  4. 軌跡追蹤 — 多幀關聯 + 卡爾曼濾波預測
  5. 物體分類 — 依亮度/速度/軌跡形狀/閃爍模式分類
  6. 事件記錄 — 自動截圖 + JSON 事件日誌
"""

import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"

import cv2
import numpy as np
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# 資料結構
# ---------------------------------------------------------------------------

@dataclass
class Detection:
    """單幀偵測結果"""
    x: int
    y: int
    w: int
    h: int
    cx: float          # 中心 x
    cy: float          # 中心 y
    area: int
    brightness: float  # 平均亮度
    max_brightness: float
    frame_id: int
    timestamp: float


@dataclass
class Track:
    """追蹤軌跡"""
    track_id: str = ""
    detections: List[Detection] = field(default_factory=list)
    predicted_x: float = 0.0
    predicted_y: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    speed_px_per_sec: float = 0.0
    age: int = 0             # 存活幀數
    missed: int = 0          # 連續未匹配幀數
    classification: str = "unknown"
    confidence: float = 0.0
    color: Tuple[int, int, int] = (0, 255, 0)
    first_seen: float = 0.0
    last_seen: float = 0.0
    is_flashing: bool = False
    flash_frequency: float = 0.0

    def __post_init__(self):
        if not self.track_id:
            self.track_id = uuid.uuid4().hex[:8]


@dataclass
class UFOEvent:
    """UFO 事件"""
    event_id: str
    track_id: str
    classification: str
    confidence: float
    start_time: str
    end_time: str
    duration_sec: float
    avg_speed: float
    max_speed: float
    trajectory_points: int
    trajectory_length_px: float
    avg_brightness: float
    is_flashing: bool
    flash_frequency: float
    bbox_first: dict
    bbox_last: dict
    screenshot_path: str = ""
    trail_image_path: str = ""


# ---------------------------------------------------------------------------
# 物體分類器
# ---------------------------------------------------------------------------

class SkyObjectClassifier:
    """
    夜空物體分類器
    依據：速度、亮度、軌跡形狀、閃爍模式、持續時間
    """

    # 分類規則（可調整）
    RULES = {
        "airplane": {
            "speed_range": (5, 80),       # px/sec（中等速度）
            "duration_min": 3.0,           # 至少 3 秒
            "flashing": True,              # 飛機有閃爍燈
            "trajectory": "linear",        # 直線軌跡
            "brightness_range": (30, 200),
        },
        "satellite": {
            "speed_range": (2, 40),        # px/sec（穩定慢速）
            "duration_min": 5.0,           # 衛星過境較久
            "flashing": False,             # 衛星不閃爍（穩定反射）
            "trajectory": "linear",        # 直線
            "brightness_range": (15, 120), # 較暗
        },
        "meteor": {
            "speed_range": (80, 9999),     # px/sec（極快）
            "duration_min": 0.0,
            "duration_max": 3.0,           # 流星很短暫
            "flashing": False,
            "trajectory": "linear",
            "brightness_range": (50, 255), # 很亮
        },
        "drone": {
            "speed_range": (1, 60),
            "duration_min": 2.0,
            "flashing": True,              # 無人機有燈
            "trajectory": "erratic",       # 軌跡不規則
            "brightness_range": (20, 180),
        },
        "ufo": {
            "speed_range": (0, 9999),      # 任何速度
            "duration_min": 0.5,
            "flashing": None,              # 不確定
            "trajectory": "any",           # 任何軌跡
            "brightness_range": (10, 255),
        },
    }

    @staticmethod
    def analyze_trajectory(points: List[Tuple[float, float]]) -> dict:
        """分析軌跡特徵"""
        if len(points) < 3:
            return {"type": "unknown", "linearity": 0, "curvature": 0}

        pts = np.array(points, dtype=np.float64)

        # 線性度：用最小二乘法擬合直線，計算 R²
        if len(pts) >= 2:
            # 用 x,y 分別對 index 做線性回歸
            t = np.arange(len(pts), dtype=np.float64)
            if np.std(pts[:, 0]) > 1e-6:
                corr_x = np.corrcoef(t, pts[:, 0])[0, 1] if len(t) > 1 else 0
            else:
                corr_x = 1.0
            if np.std(pts[:, 1]) > 1e-6:
                corr_y = np.corrcoef(t, pts[:, 1])[0, 1] if len(t) > 1 else 0
            else:
                corr_y = 1.0
            linearity = (abs(corr_x) + abs(corr_y)) / 2.0
        else:
            linearity = 0

        # 曲率：相鄰向量的角度變化
        angles = []
        for i in range(1, len(pts) - 1):
            v1 = pts[i] - pts[i - 1]
            v2 = pts[i + 1] - pts[i]
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            if norm1 > 0.5 and norm2 > 0.5:
                cos_a = np.clip(np.dot(v1, v2) / (norm1 * norm2), -1, 1)
                angles.append(np.degrees(np.arccos(cos_a)))

        avg_curvature = np.mean(angles) if angles else 0
        max_curvature = np.max(angles) if angles else 0

        if linearity > 0.85 and avg_curvature < 15:
            traj_type = "linear"
        elif avg_curvature > 30 or max_curvature > 60:
            traj_type = "erratic"
        else:
            traj_type = "curved"

        return {
            "type": traj_type,
            "linearity": round(linearity, 3),
            "curvature_avg": round(avg_curvature, 1),
            "curvature_max": round(max_curvature, 1),
        }

    @staticmethod
    def detect_flashing(brightness_history: List[float], fps: float = 15) -> dict:
        """偵測閃爍模式"""
        if len(brightness_history) < 6:
            return {"is_flashing": False, "frequency": 0, "amplitude": 0}

        arr = np.array(brightness_history, dtype=np.float64)
        mean_b = np.mean(arr)
        std_b = np.std(arr)

        if mean_b < 1:
            return {"is_flashing": False, "frequency": 0, "amplitude": 0}

        # 變異係數 > 0.2 視為閃爍
        cv = std_b / mean_b if mean_b > 0 else 0
        is_flashing = cv > 0.2

        # 估算頻率：計算過零點
        centered = arr - mean_b
        zero_crossings = np.sum(np.diff(np.sign(centered)) != 0)
        duration = len(arr) / fps if fps > 0 else 1
        frequency = zero_crossings / (2 * duration) if duration > 0 else 0

        return {
            "is_flashing": is_flashing,
            "frequency": round(frequency, 2),
            "amplitude": round(std_b, 1),
            "cv": round(cv, 3),
        }

    def classify(self, track: Track, fps: float = 15) -> Tuple[str, float]:
        """分類追蹤物體"""
        if len(track.detections) < 2:
            return "unknown", 0.0

        points = [(d.cx, d.cy) for d in track.detections]
        brightness_hist = [d.brightness for d in track.detections]
        duration = track.last_seen - track.first_seen

        traj = self.analyze_trajectory(points)
        flash = self.detect_flashing(brightness_hist, fps)

        speed = track.speed_px_per_sec
        avg_bright = np.mean(brightness_hist)

        scores = {}
        for name, rule in self.RULES.items():
            if name == "ufo":
                continue  # UFO 是 fallback
            score = 0
            total = 0

            # 速度
            total += 30
            s_min, s_max = rule["speed_range"]
            if s_min <= speed <= s_max:
                score += 30
            elif speed < s_min * 0.5 or speed > s_max * 2:
                score += 0
            else:
                score += 10

            # 持續時間
            total += 20
            if duration >= rule.get("duration_min", 0):
                if "duration_max" not in rule or duration <= rule["duration_max"]:
                    score += 20
                else:
                    score += 5
            else:
                score += 5

            # 閃爍
            total += 25
            if rule["flashing"] is not None:
                if flash["is_flashing"] == rule["flashing"]:
                    score += 25
                else:
                    score += 5
            else:
                score += 15  # 不確定

            # 軌跡
            total += 15
            if rule["trajectory"] == "any" or traj["type"] == rule["trajectory"]:
                score += 15
            elif traj["type"] == "unknown":
                score += 8
            else:
                score += 3

            # 亮度
            total += 10
            b_min, b_max = rule["brightness_range"]
            if b_min <= avg_bright <= b_max:
                score += 10
            else:
                score += 3

            scores[name] = score / total if total > 0 else 0

        if scores:
            best = max(scores, key=scores.get)
            confidence = scores[best]
            if confidence >= 0.55:
                return best, round(confidence, 3)

        return "ufo", round(1.0 - max(scores.values(), default=0), 3)


# ---------------------------------------------------------------------------
# 追蹤器
# ---------------------------------------------------------------------------

class MultiTracker:
    """多物體追蹤器（簡化版 SORT）"""

    def __init__(self, max_missed: int = 15, min_hits: int = 3,
                 max_distance: float = 80.0):
        self.tracks: List[Track] = []
        self.max_missed = max_missed
        self.min_hits = min_hits
        self.max_distance = max_distance
        self.next_color_idx = 0
        self.colors = [
            (0, 255, 0), (255, 255, 0), (0, 255, 255), (255, 0, 255),
            (255, 128, 0), (128, 255, 0), (0, 128, 255), (255, 0, 128),
        ]

    def _get_color(self):
        c = self.colors[self.next_color_idx % len(self.colors)]
        self.next_color_idx += 1
        return c

    def update(self, detections: List[Detection]) -> List[Track]:
        """用新偵測結果更新追蹤器"""
        now = time.time()

        # 預測現有軌跡的下一個位置
        for t in self.tracks:
            if len(t.detections) >= 2:
                t.predicted_x = t.detections[-1].cx + t.velocity_x
                t.predicted_y = t.detections[-1].cy + t.velocity_y
            elif t.detections:
                t.predicted_x = t.detections[-1].cx
                t.predicted_y = t.detections[-1].cy

        # 匈牙利匹配（簡化版：貪心最近鄰）
        used_det = set()
        used_trk = set()

        if self.tracks and detections:
            # 計算距離矩陣
            costs = np.zeros((len(self.tracks), len(detections)))
            for i, t in enumerate(self.tracks):
                for j, d in enumerate(detections):
                    costs[i, j] = np.sqrt(
                        (t.predicted_x - d.cx) ** 2 +
                        (t.predicted_y - d.cy) ** 2
                    )

            # 貪心匹配
            while True:
                min_val = costs.min() if costs.size > 0 else self.max_distance + 1
                if min_val > self.max_distance:
                    break
                i, j = np.unravel_index(costs.argmin(), costs.shape)
                if i in used_trk or j in used_det:
                    costs[i, j] = 99999
                    continue

                # 匹配成功
                self.tracks[i].detections.append(detections[j])
                self.tracks[i].missed = 0
                self.tracks[i].age += 1
                self.tracks[i].last_seen = now

                # 更新速度
                if len(self.tracks[i].detections) >= 2:
                    d_prev = self.tracks[i].detections[-2]
                    d_curr = self.tracks[i].detections[-1]
                    dt = d_curr.timestamp - d_prev.timestamp
                    if dt > 0:
                        self.tracks[i].velocity_x = (d_curr.cx - d_prev.cx) / dt * 0.033
                        self.tracks[i].velocity_y = (d_curr.cy - d_prev.cy) / dt * 0.033
                        speed = np.sqrt(
                            (d_curr.cx - d_prev.cx) ** 2 +
                            (d_curr.cy - d_prev.cy) ** 2
                        ) / dt
                        # 指數移動平均
                        self.tracks[i].speed_px_per_sec = (
                            0.7 * self.tracks[i].speed_px_per_sec + 0.3 * speed
                        )

                used_trk.add(i)
                used_det.add(j)
                costs[i, :] = 99999
                costs[:, j] = 99999

        # 未匹配的偵測 → 新軌跡
        for j, d in enumerate(detections):
            if j not in used_det:
                t = Track(color=self._get_color(), first_seen=now, last_seen=now)
                t.detections.append(d)
                t.predicted_x = d.cx
                t.predicted_y = d.cy
                self.tracks.append(t)

        # 未匹配的軌跡 → 增加 missed
        for i, t in enumerate(self.tracks):
            if i not in used_trk:
                t.missed += 1

        # 移除過期軌跡
        self.tracks = [t for t in self.tracks if t.missed <= self.max_missed]

        # 回傳已確認的軌跡（至少 min_hits 次偵測）
        return [t for t in self.tracks if t.age >= self.min_hits]


# ---------------------------------------------------------------------------
# UFO 偵測引擎
# ---------------------------------------------------------------------------

class UFODetector:
    """
    UFO 偵測引擎

    流程：
    1. 背景建模（MOG2 或累積平均）
    2. 前景提取 + 形態學清理
    3. 星點遮罩（靜態亮點排除）
    4. 輪廓偵測 + 過濾
    5. 多物體追蹤
    6. 分類 + 事件記錄
    """

    def __init__(self, sensitivity: float = 0.5,
                 min_area: int = 8, max_area: int = 5000,
                 star_mask_frames: int = 60,
                 output_dir: str = "ufo_events"):
        self.sensitivity = sensitivity
        self.min_area = min_area
        self.max_area = max_area
        self.star_mask_frames = star_mask_frames
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "screenshots").mkdir(exist_ok=True)
        (self.output_dir / "trails").mkdir(exist_ok=True)

        # 背景模型
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=300,
            varThreshold=int(16 + (1 - sensitivity) * 30),
            detectShadows=False
        )

        # 星點遮罩
        self.star_mask = None
        self.star_accumulator = None
        self.star_frame_count = 0

        # 追蹤器
        self.tracker = MultiTracker(max_missed=15, min_hits=3, max_distance=80)
        self.classifier = SkyObjectClassifier()

        # 狀態
        self.frame_id = 0
        self.events: List[UFOEvent] = []
        self.active_events = {}  # track_id → event_id
        self.fps_estimate = 15.0
        self.running = False

        # 偵測參數
        thresh_base = 20 + int((1 - sensitivity) * 40)
        self.fg_threshold = thresh_base

    def build_star_mask(self, gray: np.ndarray):
        """累積建立星點遮罩 — 靜態亮點（星星）會在累積影像中保持高亮度"""
        if self.star_accumulator is None:
            self.star_accumulator = gray.astype(np.float64)
        else:
            self.star_accumulator = (
                self.star_accumulator * self.star_frame_count + gray.astype(np.float64)
            ) / (self.star_frame_count + 1)
        self.star_frame_count += 1

        if self.star_frame_count >= self.star_mask_frames:
            avg = self.star_accumulator.astype(np.uint8)
            # 靜態亮點 = 星星
            _, self.star_mask = cv2.threshold(avg, 30, 255, cv2.THRESH_BINARY)
            # 膨脹一點確保完全遮蓋
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            self.star_mask = cv2.dilate(self.star_mask, kernel, iterations=1)

    def detect_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Detection], List[Track]]:
        """
        處理單幀，回傳 (標註影像, 偵測列表, 確認軌跡列表)
        """
        now = time.time()
        self.frame_id += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 1. 建立/更新星點遮罩
        if self.star_mask is None:
            self.build_star_mask(gray)

        # 2. 背景差分
        fg_mask = self.bg_subtractor.apply(gray, learningRate=0.002)

        # 3. 閾值化
        _, fg_mask = cv2.threshold(fg_mask, self.fg_threshold, 255, cv2.THRESH_BINARY)

        # 4. 排除星點
        if self.star_mask is not None:
            fg_mask = cv2.bitwise_and(fg_mask, cv2.bitwise_not(self.star_mask))

        # 5. 形態學清理
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel_open)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel_close)

        # 6. 輪廓偵測
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area or area > self.max_area:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            cx = x + w / 2.0
            cy = y + h / 2.0

            # 計算亮度
            roi = gray[y:y+h, x:x+w]
            avg_b = float(np.mean(roi)) if roi.size > 0 else 0
            max_b = float(np.max(roi)) if roi.size > 0 else 0

            detections.append(Detection(
                x=x, y=y, w=w, h=h, cx=cx, cy=cy,
                area=area, brightness=avg_b, max_brightness=max_b,
                frame_id=self.frame_id, timestamp=now
            ))

        # 7. 追蹤
        confirmed = self.tracker.update(detections)

        # 8. 分類確認的軌跡
        for track in confirmed:
            cls, conf = self.classifier.classify(track, self.fps_estimate)
            track.classification = cls
            track.confidence = conf

            # 閃爍偵測
            b_hist = [d.brightness for d in track.detections]
            flash = self.classifier.detect_flashing(b_hist, self.fps_estimate)
            track.is_flashing = flash["is_flashing"]
            track.flash_frequency = flash["frequency"]

        # 9. 事件管理
        self._manage_events(confirmed, frame)

        # 10. 繪製標註
        annotated = self._draw_annotations(frame.copy(), detections, confirmed, fg_mask)

        return annotated, detections, confirmed

    def _manage_events(self, confirmed: List[Track], frame: np.ndarray):
        """管理事件：新事件建立、結束事件記錄"""
        now = time.time()
        active_ids = {t.track_id for t in confirmed}

        # 新軌跡 → 新事件
        for track in confirmed:
            if track.track_id not in self.active_events:
                event_id = f"UFO-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{track.track_id}"
                self.active_events[track.track_id] = event_id

                # 自動截圖
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                ss_path = str(self.output_dir / "screenshots" / f"{event_id}.png")
                cv2.imwrite(ss_path, frame)

        # 結束的軌跡 → 完成事件
        ended = [tid for tid in self.active_events if tid not in active_ids]
        for tid in ended:
            # 找到對應的 track（可能已從 tracker 移除）
            track = None
            for t in self.tracker.tracks:
                if t.track_id == tid:
                    track = t
                    break

            if track and len(track.detections) >= 3:
                event = self._build_event(track, frame)
                if event:
                    self.events.append(event)
                    self._save_event(event)

            del self.active_events[tid]

    def _build_event(self, track: Track, frame: np.ndarray) -> Optional[UFOEvent]:
        """從軌跡建立事件"""
        if len(track.detections) < 3:
            return None

        event_id = self.active_events.get(track.track_id,
                    f"UFO-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{track.track_id}")

        points = [(d.cx, d.cy) for d in track.detections]
        speeds = []
        for i in range(1, len(track.detections)):
            d0 = track.detections[i - 1]
            d1 = track.detections[i]
            dt = d1.timestamp - d0.timestamp
            if dt > 0:
                dist = np.sqrt((d1.cx - d0.cx)**2 + (d1.cy - d0.cy)**2)
                speeds.append(dist / dt)

        # 軌跡長度
        traj_len = sum(
            np.sqrt((points[i][0] - points[i-1][0])**2 + (points[i][1] - points[i-1][1])**2)
            for i in range(1, len(points))
        )

        # 繪製軌跡圖
        trail_path = str(self.output_dir / "trails" / f"{event_id}_trail.png")
        self._draw_trail_image(track, frame.shape[:2], trail_path)

        d_first = track.detections[0]
        d_last = track.detections[-1]

        return UFOEvent(
            event_id=event_id,
            track_id=track.track_id,
            classification=track.classification,
            confidence=track.confidence,
            start_time=datetime.fromtimestamp(track.first_seen).isoformat(),
            end_time=datetime.fromtimestamp(track.last_seen).isoformat(),
            duration_sec=round(track.last_seen - track.first_seen, 2),
            avg_speed=round(np.mean(speeds), 1) if speeds else 0,
            max_speed=round(np.max(speeds), 1) if speeds else 0,
            trajectory_points=len(points),
            trajectory_length_px=round(traj_len, 1),
            avg_brightness=round(np.mean([d.brightness for d in track.detections]), 1),
            is_flashing=track.is_flashing,
            flash_frequency=track.flash_frequency,
            bbox_first={"x": d_first.x, "y": d_first.y, "w": d_first.w, "h": d_first.h},
            bbox_last={"x": d_last.x, "y": d_last.y, "w": d_last.w, "h": d_last.h},
            screenshot_path=str(self.output_dir / "screenshots" / f"{event_id}.png"),
            trail_image_path=trail_path,
        )

    def _draw_trail_image(self, track: Track, frame_shape: tuple, output_path: str):
        """繪製軌跡圖"""
        h, w = frame_shape
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        points = [(int(d.cx), int(d.cy)) for d in track.detections]

        # 漸變軌跡
        for i in range(1, len(points)):
            alpha = i / len(points)
            color = (
                int(track.color[0] * alpha),
                int(track.color[1] * alpha),
                int(track.color[2] * alpha),
            )
            thickness = max(1, int(3 * alpha))
            cv2.line(canvas, points[i-1], points[i], color, thickness, cv2.LINE_AA)

        # 起點和終點
        if points:
            cv2.circle(canvas, points[0], 6, (0, 255, 0), -1)   # 綠色起點
            cv2.circle(canvas, points[-1], 6, (0, 0, 255), -1)  # 紅色終點

        # 標註
        label = f"{track.classification} ({track.confidence:.0%})"
        cv2.putText(canvas, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (255, 255, 255), 2, cv2.LINE_AA)
        speed_text = f"Speed: {track.speed_px_per_sec:.1f} px/s"
        cv2.putText(canvas, speed_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (200, 200, 200), 1, cv2.LINE_AA)

        cv2.imwrite(output_path, canvas)

    def _draw_annotations(self, frame: np.ndarray, detections: List[Detection],
                          confirmed: List[Track], fg_mask: np.ndarray) -> np.ndarray:
        """在影像上繪製偵測標註"""
        h, w = frame.shape[:2]

        # 繪製所有原始偵測（小灰框）
        for d in detections:
            cv2.rectangle(frame, (d.x, d.y), (d.x + d.w, d.y + d.h),
                          (80, 80, 80), 1)

        # 繪製確認軌跡
        for track in confirmed:
            if not track.detections:
                continue
            d = track.detections[-1]
            color = track.color

            # 分類顏色
            cls_colors = {
                "airplane": (255, 200, 0),    # 青色
                "satellite": (200, 200, 200),  # 灰白
                "meteor": (0, 100, 255),       # 橘色
                "drone": (255, 0, 255),        # 紫色
                "ufo": (0, 0, 255),            # 紅色！
                "unknown": (128, 128, 128),
            }
            color = cls_colors.get(track.classification, track.color)

            # 框
            pad = 4
            cv2.rectangle(frame, (d.x - pad, d.y - pad),
                          (d.x + d.w + pad, d.y + d.h + pad), color, 2)

            # 標籤
            label = f"{track.classification} {track.confidence:.0%}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (d.x - pad, d.y - pad - th - 6),
                          (d.x - pad + tw + 4, d.y - pad), color, -1)
            cv2.putText(frame, label, (d.x - pad + 2, d.y - pad - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

            # 軌跡線
            pts = [(int(det.cx), int(det.cy)) for det in track.detections[-60:]]
            for i in range(1, len(pts)):
                alpha = i / len(pts)
                line_color = tuple(int(c * alpha) for c in color)
                cv2.line(frame, pts[i-1], pts[i], line_color, 2, cv2.LINE_AA)

            # 速度
            spd_text = f"{track.speed_px_per_sec:.0f}px/s"
            cv2.putText(frame, spd_text, (d.x, d.y + d.h + 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)

            # 閃爍標記
            if track.is_flashing:
                cv2.putText(frame, "FLASH", (d.x, d.y + d.h + 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)

        # HUD 資訊
        hud_y = 25
        cv2.putText(frame, f"UFO Detector | Frame: {self.frame_id}",
                    (10, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
        hud_y += 20
        cv2.putText(frame, f"Detections: {len(detections)} | Tracks: {len(confirmed)} | Events: {len(self.events)}",
                    (10, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 0), 1, cv2.LINE_AA)
        hud_y += 20
        star_status = "Ready" if self.star_mask is not None else f"Building ({self.star_frame_count}/{self.star_mask_frames})"
        cv2.putText(frame, f"Star Mask: {star_status}",
                    (10, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 180, 0), 1, cv2.LINE_AA)

        # 小型前景遮罩預覽（右下角）
        mask_small = cv2.resize(fg_mask, (w // 5, h // 5))
        mask_color = cv2.cvtColor(mask_small, cv2.COLOR_GRAY2BGR)
        frame[h - h//5 - 5:h - 5, w - w//5 - 5:w - 5] = mask_color

        return frame

    def _save_event(self, event: UFOEvent):
        """儲存事件到 JSON"""
        event_path = self.output_dir / f"{event.event_id}.json"
        with open(event_path, "w", encoding="utf-8") as f:
            json.dump(asdict(event), f, ensure_ascii=False, indent=2)
        print(f"📡 事件記錄：{event.event_id} [{event.classification}] "
              f"信心度={event.confidence:.0%} 持續={event.duration_sec}s "
              f"速度={event.avg_speed:.0f}px/s")

    def get_stats(self) -> dict:
        """取得統計資訊"""
        cls_count = {}
        for e in self.events:
            cls_count[e.classification] = cls_count.get(e.classification, 0) + 1
        return {
            "total_frames": self.frame_id,
            "total_events": len(self.events),
            "active_tracks": len(self.tracker.tracks),
            "confirmed_tracks": len([t for t in self.tracker.tracks if t.age >= self.tracker.min_hits]),
            "star_mask_ready": self.star_mask is not None,
            "classification_counts": cls_count,
        }


# ---------------------------------------------------------------------------
# CLI 即時偵測
# ---------------------------------------------------------------------------

def run_live_detection(rtsp_url: str, sensitivity: float = 0.5,
                       width: int = 640, height: int = 480,
                       output_dir: str = "ufo_events"):
    """即時 RTSP 偵測模式"""
    detector = UFODetector(sensitivity=sensitivity, output_dir=output_dir)

    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("錯誤：無法開啟 RTSP 串流")
        return
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    win_name = "UFO Detector | Q=quit S=snapshot"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, width, height)

    print(f"🛸 UFO 偵測啟動 — 靈敏度: {sensitivity}")
    print(f"   前 {detector.star_mask_frames} 幀建立星點遮罩...")
    print(f"   按 Q 退出，S 截圖")

    fps_timer = time.time()
    fps_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                cap.release()
                cap = cv2.VideoCapture(rtsp_url)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                continue

            frame = cv2.resize(frame, (width, height))
            annotated, dets, tracks = detector.detect_frame(frame)

            # FPS 計算
            fps_count += 1
            elapsed = time.time() - fps_timer
            if elapsed >= 1.0:
                detector.fps_estimate = fps_count / elapsed
                fps_count = 0
                fps_timer = time.time()

            cv2.imshow(win_name, annotated)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("s"):
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(f"ufo_snapshot_{ts}.png", annotated)
                print(f"📸 截圖已儲存")

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        stats = detector.get_stats()
        print(f"\n=== 偵測結束 ===")
        print(f"總幀數：{stats['total_frames']}")
        print(f"事件數：{stats['total_events']}")
        print(f"分類統計：{stats['classification_counts']}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Tapo C230 UFO 偵測引擎")
    parser.add_argument("-u", "--url", help="RTSP URL（或從 .env 讀取 TAPO_RTSP_URL）")
    parser.add_argument("-s", "--sensitivity", type=float, default=0.5,
                        help="偵測靈敏度 0.0~1.0（預設 0.5）")
    parser.add_argument("-W", "--width", type=int, default=640, help="畫面寬度")
    parser.add_argument("-H", "--height", type=int, default=480, help="畫面高度")
    parser.add_argument("-o", "--output", default="ufo_events", help="事件輸出目錄")
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

    run_live_detection(rtsp_url, args.sensitivity, args.width, args.height, args.output)


if __name__ == "__main__":
    main()

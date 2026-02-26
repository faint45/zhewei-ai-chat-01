#!/usr/bin/env python3
"""
UFO 偵測 — Web 即時偵測服務
FastAPI + WebSocket，整合 UFO 偵測引擎
功能：
  - RTSP 即時串流 + UFO 偵測 → WebSocket 推送標註畫面
  - 事件列表 / 詳情 / 截圖 / 軌跡圖
  - 偵測參數即時調整
  - 統計 API
  - 告警推播（可選 Ntfy 整合）
"""

import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"

import asyncio
import base64
import json
import time
import threading
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ufo_detector import UFODetector, UFOEvent
from virtual_cam_params import (VirtualParams, apply_params, night_sky_preset,
    starfield_preset, raw_preset, daytime_preset, stacked_raw_preset, ai_enhanced_preset,
    auto_select_preset, apply_stacked, apply_ai_enhanced, get_stack_depth,
    get_smart_info, get_progressive_info,
    TemporalDenoiser, FrameStackDenoiser, SmartEnhancer, ProgressiveEnhancer)


# ---------------------------------------------------------------------------
# 全域狀態
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
EVENT_DIR = SCRIPT_DIR / "ufo_events"
EVENT_DIR.mkdir(exist_ok=True)


class AppState:
    def __init__(self):
        self.cap = None
        self.rtsp_url = ""
        self.connected = False
        self.detecting = False
        self.detector: UFODetector = None
        self.params = night_sky_preset()  # 預設夜空優化（大光圈 + ISO 50）
        self.lock = threading.Lock()
        self.frame_count = 0
        self.fps = 0.0
        self.last_annotated = None
        self.last_raw = None
        self.sensitivity = 0.5
        self.use_params = True  # 預設啟用影像優化
        self.preset_name = "auto"  # 目前預設模式（auto = 自動偵測）
        self.auto_detected = False  # 是否已自動偵測過
        self.temporal = TemporalDenoiser()
        # 告警
        self.alert_enabled = True
        self.alert_cooldown = 30  # 同一分類冷卻秒數
        self.last_alert_time = {}  # classification → timestamp
        # 來源資訊
        self.source_type = "none"  # rtsp / http / local / none
        self.source_resolution = "unknown"
        # WebSocket 客戶端
        self.ws_clients = set()

    def connect(self, url: str) -> bool:
        """
        連線攝影機 — 自動偵測來源類型
        支援：
        - rtsp://  → Tapo C230 / IP Cam（RTSP）
        - http://  → iPhone MJPEG 串流（IPCamera App 等）
        - 數字     → 本機 USB/內建攝影機（0, 1, ...）
        """
        with self.lock:
            if self.cap:
                self.cap.release()
                self.cap = None

            # 偵測來源類型
            if url.startswith("rtsp://"):
                self.source_type = "rtsp"
            elif url.startswith("http://") or url.startswith("https://"):
                self.source_type = "http"
            elif url.isdigit():
                self.source_type = "local"
                url = int(url)
            else:
                self.source_type = "rtsp"  # 預設

            self.cap = cv2.VideoCapture(url)
            if not self.cap.isOpened():
                self.connected = False
                return False

            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            # iPhone HTTP 串流通常是 MJPEG，設定較高超時
            if self.source_type == "http":
                self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
                self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)

            self.rtsp_url = url
            self.connected = True
            self.frame_count = 0

            # 讀取一幀測試 + 取得解析度
            ret, test = self.cap.read()
            if ret and test is not None:
                h, w = test.shape[:2]
                self.source_resolution = f"{w}x{h}"
                print(f"📷 來源: {self.source_type} | 解析度: {w}x{h}")
            else:
                self.source_resolution = "unknown"

            return True

    def disconnect(self):
        with self.lock:
            self.detecting = False
            if self.cap:
                self.cap.release()
                self.cap = None
            self.connected = False
            self.source_type = "none"

    def read_frame(self):
        with self.lock:
            if not self.cap or not self.connected:
                return None
            ret, frame = self.cap.read()
            if not ret:
                # 自動重連
                self.cap.release()
                self.cap = cv2.VideoCapture(self.rtsp_url)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                return None
            self.frame_count += 1
            self.last_raw = frame
            return frame

    def init_detector(self):
        self.detector = UFODetector(
            sensitivity=self.sensitivity,
            output_dir=str(EVENT_DIR)
        )


state = AppState()


# ---------------------------------------------------------------------------
# 偵測背景執行緒
# ---------------------------------------------------------------------------

def detection_loop():
    """背景偵測迴圈"""
    fps_timer = time.time()
    fps_count = 0
    presets_map = {
        "night_sky": night_sky_preset,
        "starfield": starfield_preset,
        "daytime": daytime_preset,
        "raw": raw_preset,
    }

    last_iphone_frame_id = 0
    while state.detecting and state.connected:
        # iPhone PWA 來源：從 WebSocket 寫入的 last_raw 讀取
        if state.source_type == "iphone-pwa":
            with state.lock:
                frame = state.last_raw
                fid = state.frame_count
            if frame is None or fid == last_iphone_frame_id:
                time.sleep(0.02)
                continue
            last_iphone_frame_id = fid
            frame = frame.copy()
        else:
            frame = state.read_frame()
            if frame is None:
                time.sleep(0.05)
                continue

        frame = cv2.resize(frame, (640, 480))

        # 自動偵測亮度 → 選擇預設（僅首幀或 auto 模式）
        if state.preset_name == "auto" and not state.auto_detected:
            best = auto_select_preset(frame)
            state.params = presets_map[best]()
            state.use_params = (best != "raw")
            state.preset_name = "auto"  # 保持 auto 標記
            state.auto_detected = True
            state.temporal.reset()
            print(f"🔍 自動偵測亮度 → 選擇模式：{best}")

        # 影像處理（依模式）
        if state.preset_name == "stacked_raw":
            frame = apply_stacked(frame)
        elif state.preset_name == "ai_enhanced":
            frame = apply_ai_enhanced(frame)
        elif state.use_params:
            frame = apply_params(frame, state.params)

        # UFO 偵測
        annotated, dets, tracks = state.detector.detect_frame(frame)
        state.last_annotated = annotated

        # FPS
        fps_count += 1
        elapsed = time.time() - fps_timer
        if elapsed >= 1.0:
            state.fps = fps_count / elapsed
            state.detector.fps_estimate = state.fps
            fps_count = 0
            fps_timer = time.time()

        # 檢查新事件 → 告警
        check_alerts(tracks)

        time.sleep(0.01)  # 避免 CPU 100%


def check_alerts(tracks):
    """檢查是否需要發送告警"""
    if not state.alert_enabled:
        return
    now = time.time()
    for t in tracks:
        if t.classification in ("ufo", "unknown") and t.confidence > 0.3:
            last = state.last_alert_time.get(t.track_id, 0)
            if now - last > state.alert_cooldown:
                state.last_alert_time[t.track_id] = now
                send_alert(t)


def send_alert(track):
    """發送告警（print + 可選 Ntfy）"""
    msg = (f"🛸 UFO 偵測告警！\n"
           f"分類: {track.classification} ({track.confidence:.0%})\n"
           f"速度: {track.speed_px_per_sec:.0f} px/s\n"
           f"閃爍: {'是' if track.is_flashing else '否'}\n"
           f"時間: {datetime.now().strftime('%H:%M:%S')}")
    print(msg)

    # 嘗試 Ntfy 推播（非必要）
    try:
        import httpx
        ntfy_server = os.environ.get("NTFY_SERVER", "")
        ntfy_topic = os.environ.get("NTFY_UFO_TOPIC", "zhewei_ufo_alert")
        if ntfy_server:
            httpx.post(
                f"{ntfy_server}/{ntfy_topic}",
                content=msg.encode("utf-8"),
                headers={"Title": "UFO Detected!", "Priority": "high", "Tags": "ufo,warning"},
                timeout=5
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from dotenv import load_dotenv
        load_dotenv(SCRIPT_DIR / ".env")
    except ImportError:
        pass
    url = os.environ.get("TAPO_RTSP_URL", "")
    if url:
        ok = state.connect(url)
        if ok:
            state.init_detector()
            print(f"✅ 自動連線 RTSP 成功")
    yield
    state.disconnect()


app = FastAPI(title="UFO 偵測系統", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


# --- 頁面 ---

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = SCRIPT_DIR / "ufo_dashboard.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>UFO 偵測系統</h1><p>Dashboard 未找到</p>")


# --- PWA 攝影機 App ---

PWA_DIR = SCRIPT_DIR / "pwa"

@app.get("/cam", response_class=HTMLResponse)
async def cam_page():
    html_path = PWA_DIR / "cam.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>PWA 未找到</h1>")

@app.get("/cam/{filename}")
async def cam_static(filename: str):
    fp = PWA_DIR / filename
    if fp.exists():
        ct = "application/json" if filename.endswith(".json") else \
             "application/javascript" if filename.endswith(".js") else \
             "image/svg+xml" if filename.endswith(".svg") else \
             "image/png" if filename.endswith(".png") else "text/plain"
        return FileResponse(str(fp), media_type=ct)
    return JSONResponse({"error": "not found"}, status_code=404)


@app.websocket("/ws/cam-feed")
async def ws_cam_feed(ws: WebSocket):
    """接收 iPhone PWA 串流的 JPEG 幀"""
    await ws.accept()
    print("📱 iPhone 攝影機已連線")

    # 標記為 iPhone 來源
    state.source_type = "iphone-pwa"
    state.connected = True

    # 自動啟動偵測 + AI 漸進增強
    if not state.detector:
        state.init_detector()
    if not state.detecting:
        state.preset_name = "ai_enhanced"
        state.params = ai_enhanced_preset()
        state.use_params = True
        state.auto_detected = True
        state.detecting = True
        threading.Thread(target=detection_loop, daemon=True).start()
        print("📱 自動啟動偵測 + AI 漸進增強模式")

    cam_fps_count = 0
    cam_fps_time = time.time()

    try:
        while True:
            data = await ws.receive()

            if "text" in data:
                # JSON 控制訊息
                msg = json.loads(data["text"])
                if msg.get("type") == "init":
                    w = msg.get("width", 0)
                    h = msg.get("height", 0)
                    state.source_resolution = f"{w}x{h}"
                    print(f"📱 iPhone 解析度: {w}x{h} | UA: {msg.get('userAgent','')[:50]}")

            elif "bytes" in data:
                # 二進位 JPEG 幀
                jpg_bytes = data["bytes"]
                arr = np.frombuffer(jpg_bytes, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is not None:
                    with state.lock:
                        state.last_raw = frame
                        state.frame_count += 1
                    # FPS 計算
                    cam_fps_count += 1
                    now = time.time()
                    if now - cam_fps_time >= 1.0:
                        state.fps = cam_fps_count / (now - cam_fps_time)
                        cam_fps_count = 0
                        cam_fps_time = now
                    # 回傳 ack（用於延遲計算）
                    await ws.send_text(json.dumps({
                        "type": "ack",
                        "ts": int(time.time() * 1000),
                        "frame": state.frame_count,
                    }))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"📱 iPhone WebSocket 錯誤：{e}")
    finally:
        print("📱 iPhone 攝影機已斷線")
        if state.source_type == "iphone-pwa":
            state.detecting = False
            state.connected = False
            state.source_type = "none"


# --- 連線 ---

@app.get("/api/status")
async def get_status():
    stats = state.detector.get_stats() if state.detector else {}
    return {
        "connected": state.connected,
        "detecting": state.detecting,
        "fps": round(state.fps, 1),
        "frame_count": state.frame_count,
        "sensitivity": state.sensitivity,
        "use_params": state.use_params,
        "preset": state.preset_name,
        "alert_enabled": state.alert_enabled,
        "source_type": state.source_type,
        "source_resolution": state.source_resolution,
        "stats": stats,
    }


@app.post("/api/connect")
async def connect(url: str = Query(...)):
    ok = state.connect(url)
    if ok:
        state.init_detector()
    return {"success": ok}


@app.post("/api/disconnect")
async def disconnect():
    state.disconnect()
    return {"success": True}


# --- 偵測控制 ---

@app.post("/api/detect/start")
async def start_detection():
    if not state.connected:
        return JSONResponse({"error": "未連線攝影機"}, status_code=400)
    if state.detecting:
        return {"success": True, "message": "已在偵測中"}
    if not state.detector:
        state.init_detector()
    state.detecting = True
    threading.Thread(target=detection_loop, daemon=True).start()
    return {"success": True}


@app.post("/api/detect/stop")
async def stop_detection():
    state.detecting = False
    return {"success": True}


@app.post("/api/preset")
async def set_preset(name: str = Query(...)):
    """切換影像優化預設：auto / night_sky / starfield / daytime / stacked_raw / ai_enhanced / raw"""
    presets = {
        "night_sky": night_sky_preset,
        "starfield": starfield_preset,
        "daytime": daytime_preset,
        "stacked_raw": stacked_raw_preset,
        "ai_enhanced": ai_enhanced_preset,
        "raw": raw_preset,
    }
    if name == "auto":
        state.preset_name = "auto"
        state.auto_detected = False  # 重新偵測
        state.temporal.reset()
        return {"success": True, "preset": "auto", "use_params": True}
    if name not in presets:
        return JSONResponse({"error": f"不支援的預設：{name}"}, status_code=400)
    state.params = presets[name]()
    state.preset_name = name
    state.use_params = (name != "raw")
    state.auto_detected = True  # 手動選擇，不再自動切換
    state.temporal.reset()
    return {"success": True, "preset": name, "use_params": state.use_params}


@app.post("/api/sensitivity")
async def set_sensitivity(value: float = Query(..., ge=0, le=1)):
    state.sensitivity = value
    if state.detector:
        state.detector.sensitivity = value
        thresh = 20 + int((1 - value) * 40)
        state.detector.fg_threshold = thresh
        state.detector.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=300, varThreshold=int(16 + (1 - value) * 30), detectShadows=False)
        state.detector.star_mask = None
        state.detector.star_accumulator = None
        state.detector.star_frame_count = 0
    return {"success": True, "sensitivity": value}


@app.post("/api/params")
async def update_params(data: dict):
    for k, v in data.items():
        if hasattr(state.params, k):
            setattr(state.params, k, v)
    state.use_params = data.get("use_params", state.use_params)
    return {"success": True}


@app.post("/api/alert")
async def set_alert(enabled: bool = Query(True)):
    state.alert_enabled = enabled
    return {"success": True, "alert_enabled": enabled}


# --- 事件 ---

@app.get("/api/events")
async def list_events(limit: int = Query(50), classification: str = Query("")):
    if not state.detector:
        return {"events": []}
    events = state.detector.events[-limit:]
    if classification:
        events = [e for e in events if e.classification == classification]
    result = []
    for e in reversed(events):
        result.append({
            "event_id": e.event_id,
            "classification": e.classification,
            "confidence": e.confidence,
            "start_time": e.start_time,
            "duration_sec": e.duration_sec,
            "avg_speed": e.avg_speed,
            "is_flashing": e.is_flashing,
            "trajectory_points": e.trajectory_points,
        })
    return {"events": result, "total": len(state.detector.events)}


@app.get("/api/events/{event_id}")
async def get_event(event_id: str):
    # 從檔案讀取
    path = EVENT_DIR / f"{event_id}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return JSONResponse({"error": "事件不存在"}, status_code=404)


@app.get("/api/events/{event_id}/screenshot")
async def get_screenshot(event_id: str):
    path = EVENT_DIR / "screenshots" / f"{event_id}.png"
    if path.exists():
        return FileResponse(str(path), media_type="image/png")
    return JSONResponse({"error": "截圖不存在"}, status_code=404)


@app.get("/api/events/{event_id}/trail")
async def get_trail(event_id: str):
    path = EVENT_DIR / "trails" / f"{event_id}_trail.png"
    if path.exists():
        return FileResponse(str(path), media_type="image/png")
    return JSONResponse({"error": "軌跡圖不存在"}, status_code=404)


@app.get("/api/stats")
async def get_stats():
    if not state.detector:
        return {"error": "偵測器未初始化"}
    stats = state.detector.get_stats()
    # 加入歷史事件統計
    all_events = state.detector.events
    if all_events:
        durations = [e.duration_sec for e in all_events]
        speeds = [e.avg_speed for e in all_events if e.avg_speed > 0]
        stats["avg_duration"] = round(np.mean(durations), 1) if durations else 0
        stats["avg_speed"] = round(np.mean(speeds), 1) if speeds else 0
        stats["ufo_count"] = sum(1 for e in all_events if e.classification == "ufo")
    return stats


# --- 歷史事件（從檔案系統讀取） ---

@app.get("/api/history")
async def list_history(limit: int = Query(100)):
    events = []
    for f in sorted(EVENT_DIR.glob("UFO-*.json"), reverse=True)[:limit]:
        try:
            with open(f, encoding="utf-8") as fp:
                events.append(json.load(fp))
        except Exception:
            pass
    return {"events": events, "total": len(events)}


# --- WebSocket 即時串流 ---

@app.websocket("/ws/detect")
async def ws_detect(ws: WebSocket):
    await ws.accept()
    state.ws_clients.add(ws)
    print(f"🔌 WebSocket 客戶端連線（共 {len(state.ws_clients)}）")
    prev_event_count = len(state.detector.events) if state.detector else 0

    try:
        while True:
            if state.last_annotated is not None and state.detecting:
                _, buf = cv2.imencode(".jpg", state.last_annotated,
                                      [cv2.IMWRITE_JPEG_QUALITY, 70])
                b64 = base64.b64encode(buf).decode("utf-8")

                stats = state.detector.get_stats() if state.detector else {}
                # 檢查新事件
                new_events = []
                if state.detector:
                    current_count = len(state.detector.events)
                    if current_count > prev_event_count:
                        for e in state.detector.events[prev_event_count:]:
                            new_events.append({
                                "event_id": e.event_id,
                                "classification": e.classification,
                                "confidence": e.confidence,
                                "duration_sec": e.duration_sec,
                                "avg_speed": e.avg_speed,
                            })
                        prev_event_count = current_count

                await ws.send_text(json.dumps({
                    "type": "frame",
                    "data": b64,
                    "fps": round(state.fps, 1),
                    "frame_id": state.frame_count,
                    "preset": state.preset_name,
                    "stack_depth": get_stack_depth(),
                    "smart_info": get_smart_info(),
                    "progressive": get_progressive_info(),
                    "stats": stats,
                    "new_events": new_events,
                }))
            await asyncio.sleep(0.04)  # ~25fps
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket 錯誤：{e}")
    finally:
        state.ws_clients.discard(ws)
        print(f"🔌 WebSocket 客戶端斷線（剩 {len(state.ws_clients)}）")


# ---------------------------------------------------------------------------
# 啟動
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="UFO 偵測 Web 服務")
    parser.add_argument("-p", "--port", type=int, default=8035, help="Port（預設 8035）")
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    print(f"🛸 UFO 偵測系統：http://localhost:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

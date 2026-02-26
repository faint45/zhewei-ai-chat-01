#!/usr/bin/env python3
"""
星空攝影 — Web 即時預覽服務
FastAPI + WebSocket 串流處理後畫面到瀏覽器
不需要本地 GUI，遠端也能看

功能：
  - RTSP 即時串流 → WebSocket MJPEG 推送
  - 即時套用虛擬參數（亮度/對比/伽瑪/飽和度/銳利度/降噪/CLAHE/星空模式）
  - 遠端擷取幀 + 進階疊圖 + 縮時合成
  - 系統狀態 API
  - 靜態檔案服務（Dashboard HTML）
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
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from virtual_cam_params import VirtualParams, apply_params
from advanced_stack import (
    advanced_stack, load_images, filter_bright_frames, frame_brightness
)
from timelapse import create_timelapse, create_startrail_video


# ---------------------------------------------------------------------------
# 全域狀態
# ---------------------------------------------------------------------------

class CameraState:
    def __init__(self):
        self.cap = None
        self.rtsp_url = ""
        self.connected = False
        self.params = VirtualParams()
        self.lock = threading.Lock()
        self.frame_count = 0
        self.last_frame = None
        self.last_frame_time = 0
        self.fps_actual = 0.0
        self.capturing = False
        self.capture_progress = {"active": False, "current": 0, "total": 0, "dir": ""}

    def connect(self, url: str) -> bool:
        with self.lock:
            if self.cap:
                self.cap.release()
            self.cap = cv2.VideoCapture(url)
            if not self.cap.isOpened():
                self.connected = False
                return False
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.rtsp_url = url
            self.connected = True
            self.frame_count = 0
            return True

    def disconnect(self):
        with self.lock:
            if self.cap:
                self.cap.release()
                self.cap = None
            self.connected = False

    def read_frame(self) -> np.ndarray:
        with self.lock:
            if not self.cap or not self.connected:
                return None
            ret, frame = self.cap.read()
            if not ret:
                self.cap.release()
                self.cap = cv2.VideoCapture(self.rtsp_url)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                return None
            self.frame_count += 1
            now = time.time()
            if self.last_frame_time > 0:
                dt = now - self.last_frame_time
                if dt > 0:
                    self.fps_actual = 0.9 * self.fps_actual + 0.1 * (1.0 / dt)
            self.last_frame_time = now
            self.last_frame = frame
            return frame

    def update_params(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self.params, k):
                setattr(self.params, k, v)


camera = CameraState()
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "starfield_frames"
OUTPUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時嘗試從 .env 讀取 RTSP URL
    try:
        from dotenv import load_dotenv
        load_dotenv(SCRIPT_DIR / ".env")
    except ImportError:
        pass
    url = os.environ.get("TAPO_RTSP_URL", "")
    if url:
        ok = camera.connect(url)
        print(f"自動連線 RTSP: {'✅ 成功' if ok else '❌ 失敗'}")
    yield
    camera.disconnect()


app = FastAPI(title="星空攝影 Web 預覽", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


# ---------------------------------------------------------------------------
# API 端點
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = SCRIPT_DIR / "starfield_dashboard.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>星空攝影 Web 預覽</h1><p>Dashboard HTML 未找到</p>")


@app.get("/api/status")
async def get_status():
    return {
        "connected": camera.connected,
        "rtsp_url": camera.rtsp_url[:20] + "..." if camera.rtsp_url else "",
        "frame_count": camera.frame_count,
        "fps": round(camera.fps_actual, 1),
        "params": {
            "brightness": camera.params.brightness,
            "contrast": camera.params.contrast,
            "gamma": camera.params.gamma,
            "saturation": camera.params.saturation,
            "sharpen": camera.params.sharpen,
            "denoise": camera.params.denoise,
            "clahe": camera.params.clahe,
            "star_mode": camera.params.star_mode,
        },
        "capturing": camera.capture_progress,
    }


@app.post("/api/connect")
async def connect_camera(url: str = Query(...)):
    ok = camera.connect(url)
    return {"success": ok, "message": "連線成功" if ok else "連線失敗"}


@app.post("/api/disconnect")
async def disconnect_camera():
    camera.disconnect()
    return {"success": True}


@app.post("/api/params")
async def update_params(data: dict):
    camera.update_params(**data)
    return {"success": True, "params": data}


@app.get("/api/snapshot")
async def take_snapshot():
    frame = camera.read_frame()
    if frame is None:
        return JSONResponse({"error": "無法讀取畫面"}, status_code=503)
    processed = apply_params(frame, camera.params)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_dir = SCRIPT_DIR / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    path = snap_dir / f"snap_{ts}.png"
    cv2.imwrite(str(path), processed)
    _, buf = cv2.imencode(".jpg", processed, [cv2.IMWRITE_JPEG_QUALITY, 90])
    b64 = base64.b64encode(buf).decode("utf-8")
    return {"path": str(path), "base64": b64}


@app.post("/api/capture/start")
async def start_capture(count: int = Query(100), interval: float = Query(2.0),
                        use_params: bool = Query(True)):
    if camera.capture_progress["active"]:
        return JSONResponse({"error": "擷取中，請等待完成"}, status_code=409)
    if not camera.connected:
        return JSONResponse({"error": "未連線攝影機"}, status_code=400)

    frame_dir = OUTPUT_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    frame_dir.mkdir(parents=True, exist_ok=True)
    camera.capture_progress = {
        "active": True, "current": 0, "total": count, "dir": str(frame_dir)
    }

    def capture_worker():
        cap = cv2.VideoCapture(camera.rtsp_url)
        if not cap.isOpened():
            camera.capture_progress["active"] = False
            return
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        captured = 0
        try:
            while captured < count and camera.capture_progress["active"]:
                ret, frame = cap.read()
                if not ret:
                    cap.release()
                    cap = cv2.VideoCapture(camera.rtsp_url)
                    continue
                if use_params:
                    frame = apply_params(frame, camera.params)
                cv2.imwrite(str(frame_dir / f"frame_{captured:05d}.png"), frame)
                captured += 1
                camera.capture_progress["current"] = captured
                skip = max(0, int(interval * fps) - 1)
                for _ in range(skip):
                    cap.grab()
        finally:
            cap.release()
            camera.capture_progress["active"] = False

    threading.Thread(target=capture_worker, daemon=True).start()
    return {"success": True, "dir": str(frame_dir), "count": count}


@app.post("/api/capture/stop")
async def stop_capture():
    camera.capture_progress["active"] = False
    return {"success": True}


@app.get("/api/frames")
async def list_frame_dirs():
    dirs = []
    if OUTPUT_DIR.exists():
        for d in sorted(OUTPUT_DIR.iterdir()):
            if d.is_dir():
                pngs = list(d.glob("*.png"))
                dirs.append({"name": d.name, "count": len(pngs)})
    return {"dirs": dirs}


@app.post("/api/stack")
async def run_stack(data: dict):
    input_dir = data.get("input_dir", "")
    method = data.get("method", "sigma_clip")
    align = data.get("align", False)
    dark_dir = data.get("dark_dir", None)
    sigma = data.get("sigma", 2.5)
    max_brightness = data.get("max_brightness", 80.0)
    min_brightness = data.get("min_brightness", 5.0)
    trail_decay = data.get("trail_decay", 0.95)

    full_path = OUTPUT_DIR / input_dir if not Path(input_dir).is_absolute() else Path(input_dir)
    if not full_path.exists():
        return JSONResponse({"error": f"目錄不存在：{full_path}"}, status_code=404)

    def stack_worker():
        try:
            report = advanced_stack(
                str(full_path), method=method, align=align,
                dark_dir=dark_dir, sigma=sigma,
                max_brightness=max_brightness, min_brightness=min_brightness,
                trail_decay=trail_decay
            )
            return report
        except Exception as e:
            return {"error": str(e)}

    loop = asyncio.get_event_loop()
    report = await loop.run_in_executor(None, stack_worker)
    return report


@app.post("/api/timelapse")
async def run_timelapse(data: dict):
    input_dir = data.get("input_dir", "")
    fps = data.get("fps", 24)
    max_brightness = data.get("max_brightness", 0)
    timestamp = data.get("timestamp", False)
    mode = data.get("mode", "timelapse")
    decay = data.get("decay", 0.95)

    full_path = OUTPUT_DIR / input_dir if not Path(input_dir).is_absolute() else Path(input_dir)
    if not full_path.exists():
        return JSONResponse({"error": f"目錄不存在：{full_path}"}, status_code=404)

    def tl_worker():
        try:
            if mode == "startrail":
                return create_startrail_video(str(full_path), fps=fps, decay=decay)
            else:
                return create_timelapse(str(full_path), fps=fps,
                                        max_brightness=max_brightness,
                                        add_timestamp=timestamp)
        except Exception as e:
            return {"error": str(e)}

    loop = asyncio.get_event_loop()
    report = await loop.run_in_executor(None, tl_worker)
    return report


@app.get("/api/outputs")
async def list_outputs():
    outputs = []
    parent = OUTPUT_DIR
    for f in sorted(parent.glob("*_stacked.png")) + sorted(parent.glob("*_timelapse.mp4")) + \
             sorted(parent.glob("*_startrail*.mp4")) + sorted(parent.glob("*_sigma-clip.png")) + \
             sorted(parent.glob("*_star-trails*.png")):
        outputs.append({"name": f.name, "size_mb": round(f.stat().st_size / 1048576, 2),
                         "path": str(f)})
    # Also check parent for outputs
    for f in sorted(parent.parent.glob("*_stacked.png")) + \
             sorted(parent.parent.glob("*_timelapse.mp4")) + \
             sorted(parent.parent.glob("*_star*")):
        if f.is_file():
            outputs.append({"name": f.name, "size_mb": round(f.stat().st_size / 1048576, 2),
                             "path": str(f)})
    return {"outputs": outputs}


@app.get("/output/{filename}")
async def serve_output(filename: str):
    for search_dir in [OUTPUT_DIR, OUTPUT_DIR.parent]:
        path = search_dir / filename
        if path.exists() and path.is_file():
            media = "image/png" if filename.endswith(".png") else "video/mp4"
            return FileResponse(str(path), media_type=media)
    return JSONResponse({"error": "檔案不存在"}, status_code=404)


# ---------------------------------------------------------------------------
# WebSocket 即時串流
# ---------------------------------------------------------------------------

@app.websocket("/ws/stream")
async def websocket_stream(ws: WebSocket):
    await ws.accept()
    print("WebSocket 客戶端已連線")
    try:
        while True:
            frame = camera.read_frame()
            if frame is None:
                await asyncio.sleep(0.1)
                continue
            processed = apply_params(frame, camera.params)
            processed = cv2.resize(processed, (640, 480))
            _, buf = cv2.imencode(".jpg", processed, [cv2.IMWRITE_JPEG_QUALITY, 70])
            b64 = base64.b64encode(buf).decode("utf-8")
            await ws.send_text(json.dumps({
                "type": "frame",
                "data": b64,
                "frame_id": camera.frame_count,
                "fps": round(camera.fps_actual, 1),
                "brightness": round(frame_brightness(processed), 1),
            }))
            await asyncio.sleep(0.033)  # ~30fps max
    except WebSocketDisconnect:
        print("WebSocket 客戶端已斷線")
    except Exception as e:
        print(f"WebSocket 錯誤：{e}")


@app.websocket("/ws/control")
async def websocket_control(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            cmd = msg.get("cmd")
            if cmd == "params":
                camera.update_params(**msg.get("data", {}))
                await ws.send_text(json.dumps({"ok": True, "cmd": "params"}))
            elif cmd == "snapshot":
                frame = camera.read_frame()
                if frame is not None:
                    processed = apply_params(frame, camera.params)
                    _, buf = cv2.imencode(".jpg", processed, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    b64 = base64.b64encode(buf).decode("utf-8")
                    await ws.send_text(json.dumps({"ok": True, "cmd": "snapshot", "data": b64}))
                else:
                    await ws.send_text(json.dumps({"ok": False, "cmd": "snapshot"}))
            elif cmd == "status":
                await ws.send_text(json.dumps({
                    "ok": True, "cmd": "status",
                    "connected": camera.connected,
                    "frames": camera.frame_count,
                    "fps": round(camera.fps_actual, 1),
                    "capturing": camera.capture_progress,
                }))
    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------------------
# 啟動
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="星空攝影 Web 預覽服務")
    parser.add_argument("-p", "--port", type=int, default=8035, help="服務 Port（預設 8035）")
    parser.add_argument("--host", default="0.0.0.0", help="綁定位址")
    args = parser.parse_args()
    print(f"🌟 星空攝影 Web 預覽：http://localhost:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

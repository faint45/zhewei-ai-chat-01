# -*- coding: utf-8 -*-
"""
水情預警系統 — Pi5 站端主控程式
感測器輪詢 + 本地決策 + LoRa 發送 + 本地錄影

運行於 Raspberry Pi 5（每個觀測站一台）
"""
import json
import logging
import os
import struct
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger("water_alert.station")

DATA_DIR = Path(os.environ.get("WA_DATA_DIR", "/home/pi/water_alert/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR = DATA_DIR / "videos"
VIDEO_DIR.mkdir(exist_ok=True)


class StationController:
    """
    Pi5 站端主控程式

    主迴圈：
    1. 每 30s 讀取雷達水位
    2. 每 30s 讀取 DHT22 溫濕度
    3. 每 5min 擷取天空影像 + 雲量分析
    4. 本地決策引擎判斷警報等級
    5. LoRa 上報數據到總機
    6. 警報時自動錄影
    """

    def __init__(self, station_config):
        """
        Args:
            station_config: water_alert.config.StationConfig
        """
        self.config = station_config
        self._running = False
        self._radar = None
        self._cloud = None
        self._lora = None
        self._decision_engine = None
        self._latest_data = {
            "water_level": None,
            "temperature": None,
            "humidity": None,
            "cloud": None,
            "decision": None,
        }
        self._lock = threading.Lock()
        self._recording = False

    def init_sensors(self) -> dict:
        """初始化所有感測器"""
        status = {}

        # 雷達水位計
        if self.config.radar_installed:
            try:
                from water_alert.radar_water_level import RadarWaterLevel
                self._radar = RadarWaterLevel(
                    station_id=self.config.station_id,
                    mount_height_m=self.config.radar_mount_height_m,
                    serial_port=self.config.radar_serial_port,
                )
                ok = self._radar.connect()
                status["radar"] = "ok" if ok else "connect_failed"
            except Exception as e:
                status["radar"] = f"error: {e}"
                log.error(f"雷達初始化失敗: {e}")
        else:
            status["radar"] = "not_installed"

        # 雲量辨識
        if self.config.camera_installed and self.config.camera_fisheye:
            try:
                from water_alert.cloud_sky_analyzer import CloudSkyAnalyzer
                self._cloud = CloudSkyAnalyzer(
                    station_id=self.config.station_id,
                    camera_index=self.config.camera_index,
                )
                status["cloud"] = "ok"
            except Exception as e:
                status["cloud"] = f"error: {e}"
        else:
            status["cloud"] = "not_installed"

        # 決策引擎
        try:
            from water_alert.flood_decision_engine import FloodDecisionEngine
            from water_alert.config import DEFAULT_SYSTEM
            self._decision_engine = FloodDecisionEngine(self.config, DEFAULT_SYSTEM)
            status["decision"] = "ok"
        except Exception as e:
            status["decision"] = f"error: {e}"

        # LoRa
        try:
            from water_alert.lora_gateway import LoRaGateway
            from water_alert.config import LORA_SERIAL_PORT, LORA_BAUD_RATE
            self._lora = LoRaGateway(
                my_addr=self.config.lora_address,
                serial_port=LORA_SERIAL_PORT,
                baud_rate=LORA_BAUD_RATE,
            )
            ok = self._lora.connect()
            status["lora"] = "ok" if ok else "connect_failed"
        except Exception as e:
            status["lora"] = f"error: {e}"

        log.info(f"感測器初始化: {status}")
        return status

    def start(self):
        """啟動主迴圈"""
        if self._running:
            return
        self._running = True

        # 啟動感測器輪詢執行緒
        threading.Thread(target=self._sensor_loop, daemon=True, name="sensor").start()
        # 啟動雲量辨識執行緒（間隔較長）
        if self._cloud:
            threading.Thread(target=self._cloud_loop, daemon=True, name="cloud").start()
        # 啟動 LoRa 上報執行緒
        if self._lora:
            threading.Thread(target=self._upload_loop, daemon=True, name="upload").start()

        log.info(f"站端 {self.config.station_id} 已啟動")

    def stop(self):
        """停止"""
        self._running = False
        if self._radar:
            self._radar.disconnect()
        if self._lora:
            self._lora.stop()
        log.info("站端已停止")

    def get_latest_data(self) -> dict:
        """取得最新數據"""
        with self._lock:
            return dict(self._latest_data)

    # ===== 內部迴圈 =====

    def _sensor_loop(self):
        """感測器輪詢迴圈（每 30s）"""
        from water_alert.config import DEFAULT_SYSTEM
        interval = DEFAULT_SYSTEM.poll_interval_sec

        while self._running:
            try:
                inputs = []

                # 讀取雷達水位
                if self._radar:
                    reading = self._radar.read()
                    with self._lock:
                        self._latest_data["water_level"] = reading.to_dict()
                    if reading.valid and self._decision_engine:
                        inputs.append(
                            self._decision_engine.normalize_radar(reading.water_level_m)
                        )

                # 讀取 DHT22
                if self.config.dht_installed:
                    temp, hum = self._read_dht()
                    with self._lock:
                        self._latest_data["temperature"] = temp
                        self._latest_data["humidity"] = hum
                    if self._decision_engine and hum is not None:
                        inputs.append(
                            self._decision_engine.normalize_dht(temp or 25, hum)
                        )

                # 加入最近的雲量數據
                with self._lock:
                    cloud_data = self._latest_data.get("cloud")
                if cloud_data and self._decision_engine:
                    inputs.append(
                        self._decision_engine.normalize_cloud(
                            cloud_data.get("cloud_cover_pct", 0),
                            cloud_data.get("cloud_type", ""),
                        )
                    )

                # 決策
                if self._decision_engine and inputs:
                    decision = self._decision_engine.decide(inputs)
                    with self._lock:
                        self._latest_data["decision"] = decision.to_dict()

                    # 高警報 → 錄影
                    if decision.alert_level >= 3 and not self._recording:
                        self._start_recording()

                    log.debug(f"決策: {decision.alert_name} ({decision.weighted_score:.1f})")

            except Exception as e:
                log.error(f"感測器迴圈錯誤: {e}")

            time.sleep(interval)

    def _cloud_loop(self):
        """雲量辨識迴圈（每 5min）"""
        while self._running:
            try:
                if self._cloud:
                    image = self._cloud.capture_sky()
                    if image:
                        result = self._cloud.analyze_color(image)
                        with self._lock:
                            self._latest_data["cloud"] = result.to_dict()
                        log.debug(f"雲量: {result.cloud_cover_pct:.0f}% ({result.cloud_type_zh})")
            except Exception as e:
                log.error(f"雲量辨識錯誤: {e}")
            time.sleep(300)  # 5 分鐘

    def _upload_loop(self):
        """LoRa 上報迴圈（每 60s）"""
        from water_alert.lora_gateway import MsgType
        from water_alert.config import DEFAULT_SYSTEM
        interval = DEFAULT_SYSTEM.upload_interval_sec

        while self._running:
            try:
                with self._lock:
                    data = dict(self._latest_data)

                # 上報水位
                wl = data.get("water_level")
                if wl and self._lora:
                    level_mm = int(wl.get("water_level_m", 0) * 1000)
                    payload = struct.pack(">H", level_mm)
                    self._lora.send(0, MsgType.WATER_LEVEL, payload)

                # 上報決策
                decision = data.get("decision")
                if decision and self._lora:
                    alert_level = decision.get("alert_level", 0)
                    score = int(decision.get("weighted_score", 0))
                    payload = struct.pack(">BB", alert_level, score)
                    self._lora.send(0, MsgType.ALERT, payload)

            except Exception as e:
                log.error(f"LoRa 上報錯誤: {e}")

            time.sleep(interval)

    def _read_dht(self) -> tuple:
        """讀取 DHT22 溫濕度"""
        try:
            import adafruit_dht
            import board
            pin = getattr(board, f"D{self.config.dht_pin}", board.D4)
            dht = adafruit_dht.DHT22(pin)
            temp = dht.temperature
            hum = dht.humidity
            dht.exit()
            return temp, hum
        except ImportError:
            return None, None
        except Exception as e:
            log.warning(f"DHT22 讀取失敗: {e}")
            return None, None

    def _start_recording(self):
        """啟動警報錄影"""
        if self._recording or not self.config.camera_installed:
            return
        self._recording = True

        def _record():
            try:
                import cv2
                from water_alert.config import DEFAULT_SYSTEM
                cap = cv2.VideoCapture(self.config.camera_index)
                if not cap.isOpened():
                    return
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = str(VIDEO_DIR / f"{self.config.station_id}_{ts}.avi")
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"XVID"), 10, (w, h))
                end_time = time.time() + DEFAULT_SYSTEM.record_duration_sec
                while time.time() < end_time and self._running:
                    ret, frame = cap.read()
                    if ret:
                        out.write(frame)
                out.release()
                cap.release()
                log.info(f"錄影完成: {path}")
            except Exception as e:
                log.error(f"錄影失敗: {e}")
            finally:
                self._recording = False

        threading.Thread(target=_record, daemon=True, name="record").start()

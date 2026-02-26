# -*- coding: utf-8 -*-
"""
水情預警系統 — 80GHz FMCW 雷達波水位計
讀取 Modbus RTU / UART 雷達模組，輸出即時水位

硬體：
  - 80GHz FMCW 雷達（如 VEGAPULS C21 或國產 LD-80）
  - 測量範圍 0.1-30m，精度 ±2mm
  - 介面：RS485 Modbus RTU 或 UART TTL
"""
import logging
import os
import struct
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

log = logging.getLogger("water_alert.radar")


@dataclass
class WaterLevelReading:
    """水位讀值"""
    timestamp: str
    station_id: str
    distance_m: float        # 雷達到水面距離 (m)
    water_level_m: float     # 水位高度 (m) = mount_height - distance
    temperature_c: float     # 雷達模組溫度（補償用）
    signal_strength: float   # 信號強度 (dB)
    valid: bool = True
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "station_id": self.station_id,
            "distance_m": round(self.distance_m, 3),
            "water_level_m": round(self.water_level_m, 3),
            "temperature_c": round(self.temperature_c, 1),
            "signal_strength": round(self.signal_strength, 1),
            "valid": self.valid,
            "error": self.error,
        }


class RadarWaterLevel:
    """
    80GHz FMCW 雷達水位計驅動

    支援協議：
    1. Modbus RTU (RS485) — 工業級
    2. UART TTL — 低成本模組
    """

    def __init__(self, station_id: str = "WA-001", mount_height_m: float = 5.0,
                 serial_port: str = "/dev/ttyUSB1", baud_rate: int = 9600,
                 protocol: str = "modbus"):
        self.station_id = station_id
        self.mount_height_m = mount_height_m
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.protocol = protocol  # "modbus" or "uart"
        self._serial = None
        self._calibration_offset = 0.0
        self._last_reading: Optional[WaterLevelReading] = None
        # 移動平均濾波
        self._readings_buffer: list = []
        self._buffer_size = 5

    def connect(self) -> bool:
        """連接雷達模組"""
        try:
            import serial
            self._serial = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=2,
            )
            log.info(f"雷達連接成功: {self.serial_port} @ {self.baud_rate}")
            return True
        except ImportError:
            log.error("pyserial 未安裝: pip install pyserial")
            return False
        except Exception as e:
            log.error(f"雷達連接失敗: {e}")
            return False

    def disconnect(self):
        """斷開連接"""
        if self._serial and self._serial.is_open:
            self._serial.close()
            log.info("雷達已斷開")

    def read(self) -> WaterLevelReading:
        """
        讀取一次水位

        Returns:
            WaterLevelReading（含水位、距離、信號強度）
        """
        now = datetime.now().isoformat()

        if not self._serial or not self._serial.is_open:
            return WaterLevelReading(
                timestamp=now, station_id=self.station_id,
                distance_m=0, water_level_m=0, temperature_c=0,
                signal_strength=0, valid=False, error="未連接",
            )

        try:
            if self.protocol == "modbus":
                distance, temp, signal = self._read_modbus()
            else:
                distance, temp, signal = self._read_uart()

            # 計算水位 = 安裝高度 - 距離 + 校準偏移
            water_level = self.mount_height_m - distance + self._calibration_offset

            # 移動平均濾波
            self._readings_buffer.append(water_level)
            if len(self._readings_buffer) > self._buffer_size:
                self._readings_buffer.pop(0)
            filtered_level = sum(self._readings_buffer) / len(self._readings_buffer)

            reading = WaterLevelReading(
                timestamp=now,
                station_id=self.station_id,
                distance_m=distance,
                water_level_m=filtered_level,
                temperature_c=temp,
                signal_strength=signal,
                valid=True,
            )
            self._last_reading = reading
            return reading

        except Exception as e:
            log.error(f"雷達讀取失敗: {e}")
            return WaterLevelReading(
                timestamp=now, station_id=self.station_id,
                distance_m=0, water_level_m=0, temperature_c=0,
                signal_strength=0, valid=False, error=str(e),
            )

    def calibrate(self, known_level_m: float):
        """
        校準水位計（以已知水位校正偏移量）

        Args:
            known_level_m: 人工量測的實際水位 (m)
        """
        if self._last_reading and self._last_reading.valid:
            raw_level = self.mount_height_m - self._last_reading.distance_m
            self._calibration_offset = known_level_m - raw_level
            log.info(f"校準完成: offset={self._calibration_offset:.3f}m")
        else:
            log.warning("無有效讀值，無法校準")

    def get_last_reading(self) -> Optional[WaterLevelReading]:
        return self._last_reading

    # ===== Modbus RTU 協議 =====

    def _read_modbus(self) -> tuple:
        """
        Modbus RTU 讀取（預設暫存器地址）
        Register 0x0001: 距離 (mm, uint16)
        Register 0x0002: 溫度 (0.1°C, int16)
        Register 0x0003: 信號強度 (0.1dB, uint16)
        """
        # Modbus Read Holding Registers: 地址 01, 功能碼 03, 起始 0001, 數量 0003
        cmd = bytes([0x01, 0x03, 0x00, 0x01, 0x00, 0x03])
        cmd += self._modbus_crc(cmd)
        self._serial.write(cmd)
        time.sleep(0.1)

        resp = self._serial.read(11)  # addr(1) + func(1) + byte_count(1) + data(6) + crc(2)
        if len(resp) < 11:
            raise IOError(f"Modbus 回應不完整: {len(resp)} bytes")

        # 解析
        distance_mm = struct.unpack(">H", resp[3:5])[0]
        temp_raw = struct.unpack(">h", resp[5:7])[0]
        signal_raw = struct.unpack(">H", resp[7:9])[0]

        distance_m = distance_mm / 1000.0
        temperature = temp_raw / 10.0
        signal_db = signal_raw / 10.0

        return distance_m, temperature, signal_db

    def _read_uart(self) -> tuple:
        """
        UART 協議讀取（簡易文字協議）
        格式：$DIST,1234,25.3,45.2*XX\r\n
              $DIST,距離mm,溫度,信號強度*校驗\r\n
        """
        self._serial.write(b"$READ\r\n")
        time.sleep(0.2)
        line = self._serial.readline().decode("ascii", errors="ignore").strip()

        if not line.startswith("$DIST"):
            raise IOError(f"UART 回應格式錯誤: {line}")

        # 去掉校驗碼
        data_part = line.split("*")[0]
        parts = data_part.split(",")
        if len(parts) < 4:
            raise IOError(f"UART 資料欄位不足: {line}")

        distance_m = int(parts[1]) / 1000.0
        temperature = float(parts[2])
        signal_db = float(parts[3])

        return distance_m, temperature, signal_db

    @staticmethod
    def _modbus_crc(data: bytes) -> bytes:
        """計算 Modbus CRC16"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return struct.pack("<H", crc)

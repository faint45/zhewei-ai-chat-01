# -*- coding: utf-8 -*-
"""
水情預警系統 — LoRa SX1276 通訊閘道器
站端 ↔ 總機 雙向通訊 + Mesh 網路 + 下行廣播觸發

硬體：
  - SX1276 LoRa 模組（433MHz / 868MHz / 915MHz）
  - 介面：SPI（Pi5 GPIO）或 UART（USB dongle）
  - 有效距離：鄉村 5-10km / 城市 1-3km
"""
import json
import logging
import struct
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Callable, Optional

log = logging.getLogger("water_alert.lora")


class MsgType(IntEnum):
    """LoRa 訊息類型"""
    HEARTBEAT = 0x01        # 心跳
    WATER_LEVEL = 0x02      # 水位數據
    WEATHER = 0x03          # 溫濕度
    CLOUD_COVER = 0x04      # 雲量
    ALERT = 0x10            # 警報觸發
    BROADCAST_CMD = 0x11    # 廣播指令（總機→站端）
    SIREN_CMD = 0x12        # 警報器指令
    CALIBRATE_CMD = 0x20    # 校準指令
    ACK = 0xF0              # 確認回覆
    NACK = 0xF1             # 否認回覆


@dataclass
class LoRaPacket:
    """LoRa 封包結構"""
    src_addr: int           # 來源地址 (0-255, 0=總機)
    dst_addr: int           # 目的地址 (0xFF=廣播)
    msg_type: int           # MsgType
    seq_num: int            # 序列號 (0-255)
    payload: bytes          # 資料內容
    rssi: int = 0           # 接收信號強度
    snr: float = 0.0        # 信噪比
    timestamp: str = ""

    def encode(self) -> bytes:
        """編碼為傳輸格式: [SYNC(2)] [SRC(1)] [DST(1)] [TYPE(1)] [SEQ(1)] [LEN(2)] [PAYLOAD] [CRC(2)]"""
        header = struct.pack(">BBBBH",
                             self.src_addr, self.dst_addr,
                             self.msg_type, self.seq_num,
                             len(self.payload))
        data = b"\xAA\x55" + header + self.payload
        crc = self._crc16(data[2:])  # CRC 不含 SYNC
        return data + struct.pack(">H", crc)

    @classmethod
    def decode(cls, raw: bytes) -> Optional["LoRaPacket"]:
        """解碼接收封包"""
        if len(raw) < 10 or raw[0:2] != b"\xAA\x55":
            return None
        src, dst, mtype, seq, plen = struct.unpack(">BBBBH", raw[2:8])
        if len(raw) < 8 + plen + 2:
            return None
        payload = raw[8:8 + plen]
        crc_recv = struct.unpack(">H", raw[8 + plen:10 + plen])[0]
        crc_calc = cls._crc16(raw[2:8 + plen])
        if crc_recv != crc_calc:
            log.warning(f"CRC 錯誤: recv={crc_recv:#06x} calc={crc_calc:#06x}")
            return None
        return cls(
            src_addr=src, dst_addr=dst, msg_type=mtype,
            seq_num=seq, payload=payload,
            timestamp=datetime.now().isoformat(),
        )

    @staticmethod
    def _crc16(data: bytes) -> int:
        crc = 0xFFFF
        for b in data:
            crc ^= b
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc & 0xFFFF


class LoRaGateway:
    """
    LoRa 閘道器（總機端）

    功能：
    1. 接收站端上報數據（水位/溫濕度/雲量）
    2. 下行廣播觸發（警報器/喇叭）
    3. Mesh 中繼（多跳轉發）
    4. 心跳監控（斷線偵測）
    """

    BROADCAST_ADDR = 0xFF

    def __init__(self, my_addr: int = 0, serial_port: str = "/dev/ttyUSB0",
                 baud_rate: int = 9600):
        self.my_addr = my_addr
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self._serial = None
        self._running = False
        self._rx_thread: Optional[threading.Thread] = None
        self._seq = 0
        self._callbacks: dict = {}  # msg_type -> [callback]
        self._node_status: dict = {}  # addr -> {last_seen, rssi, snr}
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """連接 LoRa 模組"""
        try:
            import serial
            self._serial = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=1,
            )
            log.info(f"LoRa 閘道器連接: {self.serial_port}")
            return True
        except ImportError:
            log.error("pyserial 未安裝: pip install pyserial")
            return False
        except Exception as e:
            log.error(f"LoRa 連接失敗: {e}")
            return False

    def start(self):
        """啟動接收迴圈"""
        if self._running:
            return
        self._running = True
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._rx_thread.start()
        log.info("LoRa 接收迴圈已啟動")

    def stop(self):
        """停止接收"""
        self._running = False
        if self._rx_thread:
            self._rx_thread.join(timeout=3)
        if self._serial and self._serial.is_open:
            self._serial.close()
        log.info("LoRa 閘道器已停止")

    def on(self, msg_type: int, callback: Callable):
        """註冊訊息回呼"""
        if msg_type not in self._callbacks:
            self._callbacks[msg_type] = []
        self._callbacks[msg_type].append(callback)

    def send(self, dst_addr: int, msg_type: int, payload: bytes = b"") -> bool:
        """發送封包"""
        if not self._serial or not self._serial.is_open:
            return False
        self._seq = (self._seq + 1) % 256
        pkt = LoRaPacket(
            src_addr=self.my_addr,
            dst_addr=dst_addr,
            msg_type=msg_type,
            seq_num=self._seq,
            payload=payload,
        )
        try:
            self._serial.write(pkt.encode())
            return True
        except Exception as e:
            log.error(f"LoRa 發送失敗: {e}")
            return False

    def broadcast_alert(self, alert_level: int, message: str = "") -> bool:
        """
        廣播警報指令到所有站端
        alert_level: 1=注意, 2=警戒, 3=危險, 4=撤離
        """
        payload = struct.pack(">B", alert_level) + message.encode("utf-8")[:100]
        ok = self.send(self.BROADCAST_ADDR, MsgType.ALERT, payload)
        if ok:
            log.info(f"已廣播警報: level={alert_level}")
        return ok

    def send_siren_cmd(self, dst_addr: int, on: bool, duration_sec: int = 10) -> bool:
        """發送警報器開關指令"""
        payload = struct.pack(">BH", 1 if on else 0, duration_sec)
        return self.send(dst_addr, MsgType.SIREN_CMD, payload)

    def send_broadcast_cmd(self, dst_addr: int, text: str, repeat: int = 3) -> bool:
        """發送語音廣播指令"""
        payload = struct.pack(">B", repeat) + text.encode("utf-8")[:200]
        return self.send(dst_addr, MsgType.BROADCAST_CMD, payload)

    def get_node_status(self) -> dict:
        """取得所有節點狀態"""
        with self._lock:
            return dict(self._node_status)

    def is_node_online(self, addr: int, timeout_sec: int = 120) -> bool:
        """檢查節點是否在線"""
        with self._lock:
            status = self._node_status.get(addr)
            if not status:
                return False
            elapsed = time.time() - status.get("last_seen_ts", 0)
            return elapsed < timeout_sec

    # ===== 內部 =====

    def _rx_loop(self):
        """接收迴圈（背景執行緒）"""
        buffer = b""
        while self._running:
            try:
                if not self._serial or not self._serial.is_open:
                    time.sleep(1)
                    continue
                chunk = self._serial.read(256)
                if not chunk:
                    continue
                buffer += chunk
                # 搜尋封包
                while len(buffer) >= 10:
                    idx = buffer.find(b"\xAA\x55")
                    if idx < 0:
                        buffer = b""
                        break
                    if idx > 0:
                        buffer = buffer[idx:]
                    # 嘗試解碼
                    if len(buffer) < 8:
                        break
                    plen = struct.unpack(">H", buffer[6:8])[0]
                    total_len = 8 + plen + 2
                    if len(buffer) < total_len:
                        break
                    pkt = LoRaPacket.decode(buffer[:total_len])
                    buffer = buffer[total_len:]
                    if pkt:
                        self._handle_packet(pkt)
            except Exception as e:
                log.error(f"LoRa 接收錯誤: {e}")
                time.sleep(1)

    def _handle_packet(self, pkt: LoRaPacket):
        """處理收到的封包"""
        # 更新節點狀態
        with self._lock:
            self._node_status[pkt.src_addr] = {
                "last_seen": pkt.timestamp,
                "last_seen_ts": time.time(),
                "rssi": pkt.rssi,
                "snr": pkt.snr,
                "msg_type": pkt.msg_type,
            }

        # 如果不是給我的，且不是廣播，則忽略（或中繼）
        if pkt.dst_addr != self.my_addr and pkt.dst_addr != self.BROADCAST_ADDR:
            return

        # 觸發回呼
        callbacks = self._callbacks.get(pkt.msg_type, [])
        for cb in callbacks:
            try:
                cb(pkt)
            except Exception as e:
                log.error(f"LoRa callback 錯誤: {e}")

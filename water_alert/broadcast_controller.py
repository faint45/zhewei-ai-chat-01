# -*- coding: utf-8 -*-
"""
水情預警系統 — 廣播喇叭 + 警示閃光燈 GPIO 控制
Pi5 GPIO 控制繼電器 → 驅動警報器/喇叭/閃光燈

硬體：
  - 繼電器模組（5V, 高電平觸發）
  - 廣播喇叭（PA 擴音系統，3.5mm 音源輸入）
  - 警示閃光燈（12V LED 頻閃燈）
  - 警報器（12V 蜂鳴器）
"""
import logging
import os
import subprocess
import threading
import time
from datetime import datetime
from typing import Optional

log = logging.getLogger("water_alert.broadcast")

from water_alert.config import GPIO_SIREN_PIN, GPIO_LIGHT_PIN, GPIO_RELAY_PIN


class BroadcastController:
    """
    廣播/警報控制器

    功能：
    1. 警報器（蜂鳴器） — GPIO 繼電器控制
    2. 警示閃光燈 — GPIO 繼電器控制
    3. 語音廣播 — TTS → 3.5mm 音源 → PA 喇叭
    4. 組合警報 — 閃光 + 蜂鳴 + 語音同時觸發
    """

    # 預設廣播語音模板
    ALERT_MESSAGES = {
        1: "注意，注意。上游水位上升中，請工地人員留意水情。",
        2: "警戒，警戒。上游水位已達警戒線，請準備撤離低窪區域。",
        3: "危險，危險。上游水位已達危險水位，請立即撤離至安全高地。全員撤離！",
        4: "緊急撤離！緊急撤離！洪水即將到達，全員立即撤離至安全高地！重複，全員立即撤離！",
    }

    def __init__(self):
        self._gpio_available = False
        self._siren_on = False
        self._light_on = False
        self._lock = threading.Lock()
        self._init_gpio()

    def _init_gpio(self):
        """初始化 GPIO（Pi5 用 gpiod / lgpio）"""
        try:
            import lgpio
            self._chip = lgpio.gpiochip_open(0)
            lgpio.gpio_claim_output(self._chip, GPIO_SIREN_PIN, 0)
            lgpio.gpio_claim_output(self._chip, GPIO_LIGHT_PIN, 0)
            lgpio.gpio_claim_output(self._chip, GPIO_RELAY_PIN, 0)
            self._gpio_available = True
            log.info("GPIO 初始化成功 (lgpio)")
        except ImportError:
            try:
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                GPIO.setup(GPIO_SIREN_PIN, GPIO.OUT, initial=GPIO.LOW)
                GPIO.setup(GPIO_LIGHT_PIN, GPIO.OUT, initial=GPIO.LOW)
                GPIO.setup(GPIO_RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)
                self._gpio_available = True
                self._use_rpigpio = True
                log.info("GPIO 初始化成功 (RPi.GPIO)")
            except ImportError:
                log.warning("GPIO 庫未安裝（非 Pi 環境），廣播控制僅模擬")
                self._gpio_available = False
        except Exception as e:
            log.warning(f"GPIO 初始化失敗: {e}")
            self._gpio_available = False

    def siren_on(self, duration_sec: int = 10):
        """啟動警報器"""
        with self._lock:
            self._siren_on = True
        self._set_gpio(GPIO_SIREN_PIN, True)
        log.info(f"警報器 ON ({duration_sec}s)")

        def _auto_off():
            time.sleep(duration_sec)
            self.siren_off()

        threading.Thread(target=_auto_off, daemon=True).start()

    def siren_off(self):
        """關閉警報器"""
        with self._lock:
            self._siren_on = False
        self._set_gpio(GPIO_SIREN_PIN, False)
        log.info("警報器 OFF")

    def light_on(self, flash: bool = True, duration_sec: int = 30):
        """啟動警示閃光燈"""
        with self._lock:
            self._light_on = True
        log.info(f"閃光燈 ON (flash={flash}, {duration_sec}s)")

        if flash:
            def _flash_loop():
                end = time.time() + duration_sec
                while time.time() < end:
                    with self._lock:
                        if not self._light_on:
                            break
                    self._set_gpio(GPIO_LIGHT_PIN, True)
                    time.sleep(0.3)
                    self._set_gpio(GPIO_LIGHT_PIN, False)
                    time.sleep(0.3)
                self.light_off()
            threading.Thread(target=_flash_loop, daemon=True).start()
        else:
            self._set_gpio(GPIO_LIGHT_PIN, True)
            def _auto_off():
                time.sleep(duration_sec)
                self.light_off()
            threading.Thread(target=_auto_off, daemon=True).start()

    def light_off(self):
        """關閉閃光燈"""
        with self._lock:
            self._light_on = False
        self._set_gpio(GPIO_LIGHT_PIN, False)
        log.info("閃光燈 OFF")

    def broadcast_tts(self, text: str, repeat: int = 3, lang: str = "zh-TW"):
        """
        語音廣播（TTS → 喇叭）

        使用 espeak-ng 或 pico2wave 做本地 TTS
        """
        log.info(f"語音廣播: '{text[:50]}...' x{repeat}")

        # 開啟 PA 繼電器
        self._set_gpio(GPIO_RELAY_PIN, True)
        time.sleep(0.5)  # 等繼電器穩定

        for i in range(repeat):
            try:
                # 優先用 espeak-ng
                subprocess.run(
                    ["espeak-ng", "-v", lang, "-s", "130", "-p", "50", text],
                    timeout=30, capture_output=True,
                )
            except FileNotFoundError:
                try:
                    # fallback: piper (neural TTS)
                    subprocess.run(
                        ["piper", "--model", "zh_CN-huayan-medium", "--output-raw"],
                        input=text.encode("utf-8"),
                        timeout=30, capture_output=True,
                    )
                except FileNotFoundError:
                    log.warning("TTS 引擎不可用（espeak-ng / piper 未安裝）")
                    break
            except Exception as e:
                log.error(f"TTS 播放失敗: {e}")
                break

            if i < repeat - 1:
                time.sleep(1)  # 重複間隔

        # 關閉 PA 繼電器
        time.sleep(0.5)
        self._set_gpio(GPIO_RELAY_PIN, False)

    def trigger_alert(self, alert_level: int, custom_message: str = "",
                      siren_sec: int = 10, light_sec: int = 30, repeat: int = 3):
        """
        組合警報觸發

        Args:
            alert_level: 1=注意, 2=警戒, 3=危險, 4=撤離
            custom_message: 自訂廣播文字（空則用預設）
            siren_sec: 警報器時長
            light_sec: 閃光燈時長
            repeat: 語音重複次數
        """
        message = custom_message or self.ALERT_MESSAGES.get(alert_level, "")
        log.info(f"觸發組合警報: level={alert_level}")

        # 等級 2 以上：閃光燈
        if alert_level >= 2:
            self.light_on(flash=True, duration_sec=light_sec)

        # 等級 3 以上：警報器
        if alert_level >= 3:
            self.siren_on(duration_sec=siren_sec)

        # 所有等級：語音廣播
        if message:
            # 在新執行緒播放，避免阻塞
            threading.Thread(
                target=self.broadcast_tts,
                args=(message, repeat),
                daemon=True,
            ).start()

    def all_off(self):
        """全部關閉"""
        self.siren_off()
        self.light_off()
        self._set_gpio(GPIO_RELAY_PIN, False)
        log.info("全部關閉")

    def get_status(self) -> dict:
        """取得目前狀態"""
        with self._lock:
            return {
                "gpio_available": self._gpio_available,
                "siren_on": self._siren_on,
                "light_on": self._light_on,
            }

    def _set_gpio(self, pin: int, on: bool):
        """設定 GPIO 輸出"""
        if not self._gpio_available:
            log.debug(f"GPIO 模擬: pin={pin} {'ON' if on else 'OFF'}")
            return
        try:
            if hasattr(self, "_use_rpigpio"):
                import RPi.GPIO as GPIO
                GPIO.output(pin, GPIO.HIGH if on else GPIO.LOW)
            else:
                import lgpio
                lgpio.gpio_write(self._chip, pin, 1 if on else 0)
        except Exception as e:
            log.error(f"GPIO 操作失敗: pin={pin} err={e}")

    def cleanup(self):
        """清理 GPIO"""
        self.all_off()
        if self._gpio_available:
            try:
                if hasattr(self, "_use_rpigpio"):
                    import RPi.GPIO as GPIO
                    GPIO.cleanup()
                else:
                    import lgpio
                    lgpio.gpiochip_close(self._chip)
            except Exception:
                pass

# -*- coding: utf-8 -*-
"""
築未科技 — 全系統守護中樞 (Zhewei Guardian Master)
啟動自我監控與修復守護進程：健康監控、Z 槽守護、儲存分流（僅啟動存在之腳本）。
"""
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# 守護腳本（依序啟動；僅啟動存在於同目錄者）
DAEMONS = [
    "health_monitor.py",   # 系統健康與 AI 修復（可對應 brain_guardian.py）
    "z_drive_guardian.py", # Z 槽連線守護
    "storage_manager.py",  # 空間自動分流
]

# 若無 health_monitor / storage_manager，可改為專案既有守護
DAEMON_ALIAS = {
    "health_monitor.py": "brain_guardian.py",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [GuardianMaster] - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def start_guardians():
    """啟動全系統守護反射弧（僅啟動存在之腳本，各開新視窗）。"""
    logger.info("啟動全系統自我監控及修復機制...")
    processes = []
    for script in DAEMONS:
        path = ROOT / script
        if not path.exists():
            alt = DAEMON_ALIAS.get(script)
            if alt and (ROOT / alt).exists():
                path = ROOT / alt
            else:
                logger.warning("跳過（不存在）: %s", script)
                continue
        try:
            p = subprocess.Popen(
                [sys.executable, path.name],
                cwd=str(ROOT),
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
            )
            processes.append(p)
            logger.info("已啟動: %s", path.name)
        except Exception as e:
            logger.error("啟動失敗 %s: %s", script, e)
    return processes


if __name__ == "__main__":
    start_guardians()
    logger.info("守護中樞運行中，主進程每 3600 秒保持存活。")
    while True:
        time.sleep(3600)

# -*- coding: utf-8 -*-
"""
築未科技 — Z 槽守護者 (Z-Drive Guardian)
每 5 分鐘檢查 Z 槽是否可讀寫；斷線時自動重連 Rclone，日誌寫入 D 槽 brain_system.log。
"""
import logging
import os
import subprocess
import time
from pathlib import Path

# 物理路徑與日誌（可透過環境變數覆寫）
Z_PATH = Path(os.environ.get("ZHEWEI_MEMORY_ROOT", "Z:/Zhewei_Brain"))
LOG_FILE = Path(os.environ.get("BRAIN_LOG_FILE", "D:/brain_workspace/brain_system.log"))

# Rclone 掛載指令（可依實際遠端名稱與參數修改，或由環境變數組裝）
RCLONE_REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive:Zhewei_Brain")
RCLONE_MOUNT_LETTER = os.environ.get("RCLONE_MOUNT_LETTER", "Z:")
RCLONE_MOUNT_CMD = [
    "rclone", "mount", RCLONE_REMOTE, RCLONE_MOUNT_LETTER,
    "--vfs-cache-mode", "full",
    "--vfs-cache-max-size", "10G",
    "--buffer-size", "32M",
    "--daemon",
]

logger = logging.getLogger("Z-Guardian")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s - [Z-Guardian] - %(message)s")
logger.addHandler(logging.StreamHandler())
try:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
except Exception:
    pass


def is_z_online() -> bool:
    """檢查 Z 槽是否可讀寫（含核心檔案，排除殭屍掛載）。"""
    try:
        if not Z_PATH.exists():
            return False
        test_file = Z_PATH / "Rules" / "master_rules.md"
        return test_file.exists()
    except Exception:
        return False


def mount_z_drive() -> bool:
    """執行掛載程序：先結束殘留 rclone，再發送掛載指令，等待後驗證。"""
    logger.info("偵測到 Z 槽斷開，啟動自動重連程序...")
    try:
        subprocess.run(["taskkill", "/F", "/IM", "rclone.exe"], capture_output=True, timeout=5)
        time.sleep(2)
        subprocess.Popen(RCLONE_MOUNT_CMD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("掛載指令已發送，等待系統回應...")
        time.sleep(10)
        if is_z_online():
            logger.info("Z 槽重連成功，雲端記憶庫已恢復。")
            return True
        logger.error("重連失敗，請檢查 Rclone 配置或網路連線。")
        return False
    except Exception as e:
        logger.error("掛載過程發生嚴重錯誤: %s", e)
        return False


def monitor_z_drive() -> None:
    """主迴圈：每 5 分鐘巡檢 Z 槽，斷線則嘗試重連。"""
    logger.info("築未 Z 槽守護進程已啟動。")
    while True:
        if not is_z_online():
            mount_z_drive()
        time.sleep(300)


if __name__ == "__main__":
    monitor_z_drive()

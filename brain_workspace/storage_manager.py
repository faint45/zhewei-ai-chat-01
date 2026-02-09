# -*- coding: utf-8 -*-
"""
築未科技 — 儲存管理員（部署於 D:\\brain_workspace）
監控 SSD processed 與外接硬碟 E 槽，簡化版：確保目錄存在，可擴充搬移邏輯。
"""
import os
import time
from pathlib import Path

SSD_PATH = Path(os.environ.get("BRAIN_WORKSPACE", "D:/brain_workspace")) / "processed"
HDD_PATH = Path(os.environ.get("ZHEWEI_ARCHIVE_ROOT", "E:/Zhewei_Archive")) / "processed_videos"


def run_cleanup():
    if not SSD_PATH.exists():
        SSD_PATH.mkdir(parents=True, exist_ok=True)
    print("📦 儲存管理員：監控中...")
    if not HDD_PATH.exists():
        print("⚠️ 外接硬碟未連結，跳過搬移。")
        return
    HDD_PATH.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    run_cleanup()

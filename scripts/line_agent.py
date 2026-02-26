#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LINE 桌面代理（主機端）
- open: 開啟 LINE 應用
- read_ocr: 截圖 + OCR 嘗試讀取目前 LINE 視窗訊息區文字（不保證穩定）
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pyautogui


def _line_candidates() -> list[str]:
    user = os.environ.get("USERNAME", "")
    env_path = (os.environ.get("LINE_EXE_PATH") or "").strip()
    candidates = [
        env_path,
        rf"C:\Users\{user}\AppData\Local\LINE\bin\Line.exe",
        r"C:\Program Files\LINE\bin\Line.exe",
        r"C:\Program Files (x86)\LINE\bin\Line.exe",
    ]
    return [x for x in candidates if x]


def open_line() -> dict:
    for p in _line_candidates():
        if Path(p).exists():
            try:
                subprocess.Popen([p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(6)
                return {"ok": True, "result": f"LINE 已啟動：{p}"}
            except Exception as e:
                return {"ok": False, "error": f"啟動失敗：{e}"}
    return {"ok": False, "error": f"找不到 LINE 執行檔，已嘗試：{_line_candidates()}"}


def _find_line_window():
    try:
        import pygetwindow as gw
    except Exception:
        return None
    windows = []
    try:
        windows = gw.getWindowsWithTitle("LINE")
    except Exception:
        windows = []
    for w in windows:
        try:
            if not w.isMinimized and w.width > 300 and w.height > 300:
                return w
        except Exception:
            continue
    return None


def read_line_ocr() -> dict:
    win = _find_line_window()
    if win is None:
        return {"ok": False, "error": "找不到 LINE 視窗（請先開啟 LINE 並保持在前景）"}

    # 粗略訊息區域：排除左側聊天室列表，保留中右內容區
    left = int(win.left + max(180, win.width * 0.26))
    top = int(win.top + max(70, win.height * 0.10))
    width = int(max(220, win.width * 0.68))
    height = int(max(220, win.height * 0.78))
    region = (left, top, width, height)

    try:
        snap = pyautogui.screenshot(region=region)
    except Exception as e:
        return {"ok": False, "error": f"截圖失敗：{e}"}

    out_dir = Path(__file__).resolve().parent.parent / "reports" / "line_ocr"
    out_dir.mkdir(parents=True, exist_ok=True)
    img_path = out_dir / f"line_region_{int(time.time())}.png"
    snap.save(str(img_path))

    try:
        import pytesseract
    except Exception:
        return {
            "ok": False,
            "error": "未安裝 pytesseract（先執行 pip install pytesseract 並安裝 Tesseract OCR）",
            "screenshot": str(img_path),
        }

    try:
        text = pytesseract.image_to_string(snap, lang="chi_tra+eng")
    except Exception as e:
        return {"ok": False, "error": f"OCR 失敗：{e}", "screenshot": str(img_path)}

    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    parsed = "\n".join(lines[:80])
    return {
        "ok": True,
        "result": parsed or "(OCR 無可用文字)",
        "line_count": len(lines),
        "screenshot": str(img_path),
        "warning": "LINE 無官方讀訊 API，本結果為 OCR 估測，可能不準確或受介面更新影響。",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["open", "read_ocr"], required=True)
    args = parser.parse_args()

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1

    if args.action == "open":
        res = open_line()
    else:
        res = read_line_ocr()
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

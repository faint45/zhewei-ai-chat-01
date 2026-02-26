#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
即時顯示滑鼠座標
按 Ctrl + C 結束
"""

import time

import pyautogui


def main() -> int:
    print("Press Ctrl-C to quit.")
    try:
        while True:
            x, y = pyautogui.position()
            msg = f"X: {str(x).rjust(4)} Y: {str(y).rjust(4)}"
            print(msg, end="\r", flush=True)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

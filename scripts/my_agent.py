#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyAutoGUI 基本示範腳本
- 5 秒倒數
- 移動滑鼠並點擊
- 輸入文字
- 按下 Enter
"""

import time

import pyautogui


def main() -> int:
    # 安全機制：滑鼠移到左上角可強制中止
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.15

    print("程式即將啟動，請在 5 秒內準備視窗...")
    time.sleep(5)

    print("開始移動滑鼠並點擊...")
    pyautogui.moveTo(500, 500, duration=1)
    pyautogui.click()

    print("開始打字...")
    pyautogui.write("Hello from your agent!", interval=0.08)

    time.sleep(1)
    print("按下 Enter...")
    pyautogui.press("enter")

    print("自動化腳本執行完畢。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

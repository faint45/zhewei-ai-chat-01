#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PM2 用：每 60 秒執行一次 monitor_runtime_and_notify，常駐迴圈。"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "monitor_runtime_and_notify.py"
INTERVAL = 60

def main():
    while True:
        try:
            subprocess.run([sys.executable, str(SCRIPT)], cwd=str(ROOT), timeout=300)
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            print(f"[monitor_loop] {e}", file=sys.stderr)
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()

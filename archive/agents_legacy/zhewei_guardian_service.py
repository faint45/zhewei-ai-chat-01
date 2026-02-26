"""
築未科技 - 24/7 全時監控與自動修復服務
偵測 Ollama / Discord 連線，異常時自動喚醒
優化：Session 重用、穩定時拉長檢查間隔以降低 CPU 與網路負擔
"""
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

BASE_DIR = Path(__file__).parent.resolve()
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
CHECK_INTERVAL = int(os.environ.get("GUARDIAN_CHECK_INTERVAL", "30"))
CHECK_INTERVAL_STABLE = int(os.environ.get("GUARDIAN_CHECK_STABLE_INTERVAL", "60"))
STABLE_COUNT_BEFORE_SLOW = 3


def check_ollama(session=None) -> bool:
    if not requests:
        return False
    try:
        url = f"{OLLAMA_URL.rstrip('/')}/api/tags"
        if session:
            r = session.get(url, timeout=5)
        else:
            r = requests.get(url, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def wake_ollama():
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(BASE_DIR),
        )
        return True
    except FileNotFoundError:
        return False


def main():
    print("[守護] 築未 24/7 監控啟動")
    stable_ok = 0
    session = requests.Session() if requests else None
    while True:
        ok = check_ollama(session)
        if not ok:
            stable_ok = 0
            print("[守護] Ollama 離線，嘗試喚醒...")
            wake_ollama()
            time.sleep(10)
        else:
            stable_ok += 1
            if stable_ok >= STABLE_COUNT_BEFORE_SLOW:
                print("[守護] Ollama 正常（穩定，降低檢查頻率）")
                time.sleep(CHECK_INTERVAL_STABLE)
            else:
                print("[守護] Ollama 正常")
                time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[守護] 已停止")

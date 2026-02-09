# -*- coding: utf-8 -*-
"""
築未科技 — brain_server 健康與靜態測試（Port 8000）
驗證 /health、/、/static/index.html 可存取；不啟動 WebSocket。
"""
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

BASE_URL = os.environ.get("BRAIN_SERVER_URL", "http://127.0.0.1:8000")
TIMEOUT = 5
FAILED = []


def req(method: str, path: str) -> tuple[int, str]:
    url = BASE_URL.rstrip("/") + path
    try:
        r = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(r, timeout=TIMEOUT) as res:
            return res.status, res.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


def ok(name: str, cond: bool, msg: str = ""):
    if cond:
        print(f"  [OK] {name}" + (f" — {msg}" if msg else ""))
    else:
        print(f"  [X]  {name}" + (f" — {msg}" if msg else ""))
        FAILED.append(name)


def main():
    print()
    print("  築未科技 — brain_server 健康與靜態測試")
    print(f"  BASE_URL = {BASE_URL}")
    print()

    code, body = req("GET", "/health")
    ok("/health", code == 200, f"status={code}")
    if code == 200 and "status" in body:
        ok("/health 含 status", "healthy" in body or "status" in body)

    code, body = req("GET", "/")
    ok("/ 根路由", code == 200, f"status={code}")
    if code == 200:
        ok("/ 可讀", len(body) > 0, "有內容")

    code, body = req("GET", "/static/index.html")
    if code != 200:
        code, body = req("GET", "/admin")
    ok("/static/index.html 或 /admin", code == 200, f"status={code}")
    if code == 200:
        ok("管理介面含 Vue", "vue" in body.lower() or "Vue" in body, "有 Vue 引用")
        ok("管理介面含 WebSocket", "ws" in body or "WebSocket" in body, "有 WS")

    code, body = req("GET", "/chat")
    if code != 200:
        code, body = req("GET", "/static/chat.html")
    ok("/chat 或 /static/chat.html", code == 200, f"status={code}")
    if code == 200:
        ok("對話頁含 WebSocket", "ws" in body or "WebSocket" in body, "有 WS")

    print()
    if FAILED:
        print(f"  失敗：{', '.join(FAILED)}")
        return 1
    print("  全部通過。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

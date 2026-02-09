"""
築未科技大腦 - API 冒煙測試
部署或改版後執行，確認 /health、/ready、/login、/compute 等基本可用。
"""
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

try:
    from dotenv import load_dotenv
    load_dotenv()
    ue = Path.home() / ".openclaw" / ".env"
    if ue.exists():
        load_dotenv(ue, override=True)
except ImportError:
    pass

import urllib.request
import json

BASE_URL = os.environ.get("BRAIN_BRIDGE_BASE_URL", "http://127.0.0.1:5100")
TIMEOUT = 10
FAILED = []


def req(method: str, path: str, body: dict = None, headers: dict = None) -> tuple[int, dict]:
    url = BASE_URL.rstrip("/") + path
    h = {"Content-Type": "application/json", **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read().decode("utf-8", errors="replace")
            return r.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        return e.code, json.loads(raw) if raw.strip() else {}
    except Exception as e:
        return 0, {"error": str(e)}


def ok(name: str, cond: bool, msg: str = ""):
    if cond:
        print(f"  [OK] {name}" + (f" — {msg}" if msg else ""))
    else:
        print(f"  [X]  {name}" + (f" — {msg}" if msg else ""))
        FAILED.append(name)


def main():
    print()
    print("  築未科技大腦 — API 冒煙測試")
    print(f"  BASE_URL = {BASE_URL}")
    print()

    # 1. /health
    code, data = req("GET", "/health")
    ok("/health", code == 200 and data.get("ok"), f"status={code}")

    # 2. /ready（有 200 即通過）
    code, data = req("GET", "/ready")
    ok("/ready", code == 200, f"deps={data.get('deps', {})}")

    # 3. /auth/login（若未設 AUTH_USERS 則 503 也算通過）
    code, data = req("POST", "/auth/login", body={"username": "smoke", "password": "test"})
    ok("/auth/login", code in (200, 401, 503), f"status={code}")

    # 4. /compute 需認證；無認證應 401
    code, data = req("POST", "/compute", body={"message": "hi", "source": "web"})
    ok("/compute (no auth -> 401)", code == 401, f"status={code}")

    # 5. 若有 AUTH_USERS，登入後再打 /compute
    api_key = os.environ.get("BRAIN_BRIDGE_API_KEY", "").strip()
    if api_key and not api_key.startswith("your-"):
        code, data = req("POST", "/compute", body={"message": "1+1", "source": "web"}, headers={"X-API-Key": api_key})
        ok("/compute (with API Key)", code == 200 and "reply" in data, f"status={code}")
    else:
        print("  [skip] /compute with API Key (no BRAIN_BRIDGE_API_KEY)")

    # 6. /usage（有 200 即通過）
    code, data = req("GET", "/usage")
    ok("/usage", code == 200, data.get("formatted", "") or str(data))

    print()
    if FAILED:
        print(f"  失敗：{', '.join(FAILED)}")
        return 1
    print("  全部通過。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

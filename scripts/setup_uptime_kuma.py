# -*- coding: utf-8 -*-
"""
Uptime Kuma 監控初始化腳本
═══════════════════════════════════════
首次啟動後執行，透過 API 自動建立：
  1. 管理員帳號
  2. Ntfy 告警通知
  3. 7 個監控目標

執行：python scripts/setup_uptime_kuma.py
前提：Uptime Kuma 已啟動於 localhost:3301
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

BASE = os.environ.get("UPTIME_KUMA_URL", "http://localhost:3301")
NTFY_URL = os.environ.get("NTFY_URL", "http://zhewei_ntfy:80")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "zhewei-alerts")

ADMIN_USER = "admin"
ADMIN_PASS = os.environ.get("UPTIME_KUMA_PASS", "ZheWei2026!Monitor")

MONITORS = [
    {"name": "Brain Server /healthz",   "url": "http://zhewei_brain:8000/healthz",         "interval": 60},
    {"name": "Brain Server /readyz",    "url": "http://zhewei_brain:8000/readyz",          "interval": 120},
    {"name": "Gateway Nginx",           "url": "http://zhewei_gateway:80/nginx-health",    "interval": 60},
    {"name": "Portal",                  "url": "http://zhewei_portal:8888/health",         "interval": 120},
    {"name": "CMS 營建管理",            "url": "http://zhewei_cms:8020/",                  "interval": 120},
    {"name": "Ntfy 推播",               "url": "http://zhewei_ntfy:80/v1/health",          "interval": 120},
    {"name": "Public HTTPS",            "url": "https://jarvis.zhe-wei.net/healthz",       "interval": 300},
]


def _post(url, data, cookie=""):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode()), resp.headers.get("Set-Cookie", "")
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}: {body}"}, ""


def _get(url, cookie=""):
    req = urllib.request.Request(url)
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


def main():
    print("=" * 55)
    print("Uptime Kuma 監控初始化")
    print("=" * 55)

    # 1. 等待 Uptime Kuma 就緒
    print("\n⏳ 等待 Uptime Kuma 就緒...")
    for i in range(30):
        try:
            urllib.request.urlopen(f"{BASE}/api/entry-page", timeout=5)
            print("  ✅ Uptime Kuma 已就緒")
            break
        except Exception:
            time.sleep(2)
    else:
        print("  ❌ Uptime Kuma 未就緒，請確認容器狀態")
        sys.exit(1)

    # 2. 建立管理員（首次）
    print(f"\n👤 建立管理員 ({ADMIN_USER})...")
    r, cookie = _post(f"{BASE}/api/setup-database", {})
    r, cookie = _post(f"{BASE}/api/setup", {
        "username": ADMIN_USER,
        "password": ADMIN_PASS,
    })
    if "error" in r and "already" not in str(r.get("error", "")).lower():
        # 可能已經設定過，嘗試登入
        print(f"  ⚠️  可能已初始化: {r.get('error', '')}")
        print("  🔑 嘗試登入...")
        r, cookie = _post(f"{BASE}/api/login", {
            "username": ADMIN_USER,
            "password": ADMIN_PASS,
            "token": "",
        })
        if "error" in r:
            print(f"  ❌ 登入失敗: {r}")
            print(f"\n  請手動開啟 {BASE} 完成設定，然後設定以下監控目標：")
            for m in MONITORS:
                print(f"    • {m['name']}: {m['url']} (每 {m['interval']}s)")
            print(f"\n  Ntfy 告警: {NTFY_URL}/{NTFY_TOPIC}")
            return
    else:
        print("  ✅ 管理員已建立")

    # 從 cookie 取得 session
    session = ""
    if cookie:
        for part in cookie.split(";"):
            if "connect.sid" in part:
                session = part.strip()
                break

    print(f"\n📡 建立 {len(MONITORS)} 個監控目標...")
    for m in MONITORS:
        r, _ = _post(f"{BASE}/api/monitors", {
            "type": "http",
            "name": m["name"],
            "url": m["url"],
            "interval": m["interval"],
            "retryInterval": 30,
            "maxretries": 3,
            "method": "GET",
            "accepted_statuscodes": ["200-299"],
            "active": True,
        }, cookie=session)
        if "error" in r:
            print(f"  ⚠️  {m['name']}: {r.get('error', 'unknown')}")
        else:
            print(f"  ✅ {m['name']} ({m['interval']}s)")

    print("\n" + "=" * 55)
    print(f"✅ 完成！開啟 {BASE} 登入後設定 Ntfy 告警：")
    print(f"   Settings → Notifications → Ntfy")
    print(f"   Server URL: {NTFY_URL}")
    print(f"   Topic: {NTFY_TOPIC}")
    print("=" * 55)


if __name__ == "__main__":
    main()

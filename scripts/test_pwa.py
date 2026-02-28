import httpx

base = "http://localhost:8002"

# Test PWA page
r = httpx.get(f"{base}/pwa", timeout=10)
has_login = "loginScreen" in r.text
print(f"1. PWA page: HTTP {r.status_code}, has login: {has_login}")

# Test manifest
r = httpx.get(f"{base}/pwa/manifest.json", timeout=10)
print(f"2. Manifest: HTTP {r.status_code}, type: {r.headers.get('content-type','?')}")

# Test SW
r = httpx.get(f"{base}/pwa/sw.js", timeout=10)
print(f"3. SW: HTTP {r.status_code}, type: {r.headers.get('content-type','?')}")

# Test icon
r = httpx.get(f"{base}/pwa/icon-192.png", timeout=10)
print(f"4. Icon: HTTP {r.status_code}, type: {r.headers.get('content-type','?')}")

# Test login
r = httpx.post(f"{base}/api/auth/login", json={"username":"allen34556","password":"Rr124243084"}, timeout=10)
d = r.json()
print(f"5. Login: ok={d.get('ok')}, has_token={bool(d.get('token'))}")

if d.get("token"):
    token = d["token"]
    r = httpx.get(f"{base}/api/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    me = r.json()
    role = me.get("user", {}).get("role", "?")
    print(f"6. Auth/me: ok={me.get('ok')}, role={role}")

# Test via Cloudflare
try:
    r = httpx.get("https://jarvis.zhe-wei.net/pwa", timeout=15, follow_redirects=True)
    print(f"7. External PWA: HTTP {r.status_code}")
except Exception as e:
    print(f"7. External PWA: {e}")

print("\nDONE")

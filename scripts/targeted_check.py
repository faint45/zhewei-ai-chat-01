import socket, sys
try:
    import httpx
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "-q"])
    import httpx

def check_port(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except:
        s.close()
        return False

print("=== 1. Port Scan (standalone services) ===")
ports = {7860: "Forge", 9188: "ComfyUI", 8030: "Vision", 8025: "Predict", 8001: "CodeSim-direct", 8020: "CMS-direct"}
for p, n in ports.items():
    status = "OPEN" if check_port(p) else "CLOSED"
    print(f"  :{p} ({n}) = {status}")

print("\n=== 2. Brain Chat endpoint ===")
try:
    r = httpx.get("http://localhost:8002/api/chat/remote/status", timeout=10)
    print(f"  /api/chat/remote/status: HTTP {r.status_code} | {r.text[:150]}")
except Exception as e:
    print(f"  FAIL: {e}")

print("\n=== 3. CodeSim via Gateway ===")
try:
    r = httpx.get("http://localhost:8888", headers={"Host": "codesim.zhe-wei.net"}, timeout=10, follow_redirects=True)
    print(f"  CodeSim via GW: HTTP {r.status_code}")
except Exception as e:
    print(f"  FAIL: {e}")

print("\n=== 4. CMS via Gateway ===")
try:
    r = httpx.get("http://localhost:8888", headers={"Host": "cms.zhe-wei.net"}, timeout=10, follow_redirects=True)
    print(f"  CMS via GW: HTTP {r.status_code}")
except Exception as e:
    print(f"  FAIL: {e}")

print("\n=== 5. Auth Login (wrong password) ===")
try:
    r = httpx.post("http://localhost:8002/api/auth/login", json={"username": "wrong_test", "password": "wrong"}, timeout=10)
    print(f"  Auth: HTTP {r.status_code} | {r.text[:200]}")
except Exception as e:
    print(f"  FAIL: {e}")

print("\n=== 6. Ntfy DNS ===")
for domain in ["notify.zhewei.tech", "ntfy.zhewei.tech", "notify.zhe-wei.net"]:
    try:
        ip = socket.gethostbyname(domain)
        print(f"  {domain} -> {ip}")
    except:
        print(f"  {domain} -> DNS FAIL")

print("\n=== 7. Jarvis Self-Check ===")
try:
    r = httpx.get("http://localhost:8002/api/jarvis/self-check", timeout=15)
    data = r.json()
    for k, v in data.get("checks", {}).items():
        if isinstance(v, dict):
            ok = v.get("ok", "?")
            detail = str(v)[:100]
        else:
            ok = v
            detail = ""
        icon = "OK" if ok else "NO"
        print(f"  [{icon}] {k}: {detail}")
except Exception as e:
    print(f"  FAIL: {e}")

print("\n=== 8. Cloudflare External ===")
for domain, label in [("zhe-wei.net", "Main"), ("jarvis.zhe-wei.net", "Jarvis"), ("bridge.zhe-wei.net", "Bridge"), ("codesim.zhe-wei.net", "CodeSim"), ("cms.zhe-wei.net", "CMS")]:
    try:
        r = httpx.get(f"https://{domain}", timeout=10, follow_redirects=True, verify=False)
        print(f"  {label} ({domain}): HTTP {r.status_code}")
    except Exception as e:
        print(f"  {label} ({domain}): FAIL - {str(e)[:60]}")

print("\n=== DONE ===")

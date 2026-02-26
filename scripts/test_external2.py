import urllib.request
import urllib.error
import ssl

# Test 1: Direct IP with Host header (bypass local DNS)
print("=== Test 1: Direct IP + Host header ===")
try:
    req = urllib.request.Request("https://104.21.26.59/health")
    req.add_header("Host", "brain.zhe-wei.net")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    r = urllib.request.urlopen(req, timeout=10, context=ctx)
    print("OK", r.status)
    print(r.read().decode()[:300])
except urllib.error.HTTPError as e:
    print("ERR", e.code)
    body = e.read().decode()[:300]
    print(body)
except Exception as e:
    print("FAIL", e)

# Test 2: Login page
print("\n=== Test 2: Login page ===")
try:
    req = urllib.request.Request("https://104.21.26.59/jarvis-login")
    req.add_header("Host", "brain.zhe-wei.net")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    r = urllib.request.urlopen(req, timeout=10, context=ctx)
    print("OK", r.status)
    print(r.read().decode()[:200])
except urllib.error.HTTPError as e:
    print("ERR", e.code)
    body = e.read().decode()[:200]
    print(body)
except Exception as e:
    print("FAIL", e)

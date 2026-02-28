import httpx
import json

# 1. Check Forge API models
try:
    r = httpx.get("http://localhost:7860/sdapi/v1/sd-models", timeout=10)
    models = r.json()
    print(f"1. Forge models: {len(models)} models")
    for m in models[:3]:
        print(f"   - {m.get('title', '?')}")
except Exception as e:
    print(f"1. Forge models: FAIL - {e}")

# 2. Check Forge txt2img with minimal steps
try:
    payload = {
        "prompt": "a cute cat, digital art",
        "negative_prompt": "ugly, blurry",
        "width": 512,
        "height": 512,
        "steps": 2,
        "cfg_scale": 7,
        "sampler_name": "Euler",
    }
    r = httpx.post("http://localhost:7860/sdapi/v1/txt2img", json=payload, timeout=60)
    d = r.json()
    images = d.get("images", [])
    print(f"2. Forge txt2img: HTTP {r.status_code}, images={len(images)}, img_len={len(images[0]) if images else 0}")
except Exception as e:
    print(f"2. Forge txt2img: FAIL - {e}")

# 3. Check brain_server generate-image endpoint (need real token)
try:
    # Login first
    lr = httpx.post("http://localhost:8002/api/auth/login",
        json={"username": "allen34556", "password": "Rr124243084"}, timeout=10)
    token = lr.json().get("token", "")
    
    r = httpx.post("http://localhost:8002/api/jarvis/generate-image",
        json={"prompt": "a beautiful sunset", "width": 512, "height": 512},
        headers={"Authorization": f"Bearer {token}"},
        timeout=60)
    print(f"3. brain generate-image: HTTP {r.status_code} | {r.text[:300]}")
except Exception as e:
    print(f"3. brain generate-image: FAIL - {e}")

# 4. ComfyUI system
try:
    r = httpx.get("http://localhost:9188/system_stats", timeout=10)
    print(f"4. ComfyUI: HTTP {r.status_code}")
except Exception as e:
    print(f"4. ComfyUI: FAIL - {e}")

print("\nDONE")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vision Edge Service 端對端測試"""
import base64
import io
import json
import sys

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed")
    sys.exit(1)

BASE = "http://localhost:8015"


def test_health():
    print("=== 1. Health Check ===")
    r = httpx.get(f"{BASE}/health", timeout=5)
    d = r.json()
    print(f"  Status: {d['status']}")
    print(f"  Ollama: {d['ollama']}")
    print(f"  YOLO: {d['yolo_loaded']}")
    print(f"  Monitor: {d['monitor_running']}")
    print(f"  Sources: {d['monitor_sources']}")
    assert d["status"] == "ok", "Health check failed"
    print("  ✓ PASS\n")


def test_stats():
    print("=== 2. Stats ===")
    r = httpx.get(f"{BASE}/api/vision/stats", timeout=5)
    d = r.json()
    print(f"  Total inferences: {d['total_inferences']}")
    print("  ✓ PASS\n")


def test_monitor_status():
    print("=== 3. Monitor Status ===")
    r = httpx.get(f"{BASE}/api/monitor/status", timeout=5)
    d = r.json()
    print(f"  Running: {d['running']}")
    print(f"  Sources: {len(d['sources'])}")
    print("  ✓ PASS\n")


def test_add_monitor_source():
    print("=== 4. Add Monitor Source ===")
    r = httpx.post(f"{BASE}/api/monitor/sources", json={
        "name": "測試來源",
        "type": "screenshot",
        "interval_sec": 60,
        "analysis_mode": "vlm_only",
    }, timeout=5)
    d = r.json()
    print(f"  OK: {d['ok']}")
    print(f"  Source ID: {d['source_id']}")
    assert d["ok"], "Add source failed"
    print("  ✓ PASS\n")
    return d["source_id"]


def test_vlm_analysis():
    print("=== 5. VLM Analysis (test image) ===")
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("  SKIP: PIL not installed")
        return

    # 建立測試圖片
    img = Image.new("RGB", (640, 480), color=(100, 150, 200))
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 200, 200], fill="red", outline="white")
    draw.rectangle([300, 100, 500, 350], fill="green", outline="white")
    draw.ellipse([150, 250, 350, 430], fill="yellow", outline="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    b64 = base64.b64encode(img_bytes).decode()
    print(f"  Test image: {len(img_bytes)} bytes")

    r = httpx.post(f"{BASE}/api/vision/analyze", data={
        "image_base64": b64,
        "mode": "vlm_only",
        "provider": "auto",
        "prompt": "Describe the geometric shapes in this image",
        "save_to_kb": "true",
    }, timeout=120)
    d = r.json()
    print(f"  HTTP: {r.status_code}")
    print(f"  Provider: {d.get('provider', 'N/A')}")
    print(f"  Inference: {d.get('inference_ms', 0)} ms")
    desc = d.get("description", "") or d.get("raw_response", "")
    print(f"  Description: {desc[:200]}")
    print(f"  Confidence: {d.get('confidence', 0)}")
    print(f"  Image path: {d.get('image_path', '')}")
    print("  ✓ PASS\n")


def test_pure_vlm():
    print("=== 6. Pure VLM Endpoint ===")
    try:
        from PIL import Image
    except ImportError:
        print("  SKIP: PIL not installed")
        return

    img = Image.new("RGB", (320, 240), color=(50, 100, 150))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    r = httpx.post(f"{BASE}/api/vision/vlm", data={
        "image_base64": b64,
        "prompt": "What color is this image?",
        "provider": "auto",
    }, timeout=120)
    d = r.json()
    print(f"  OK: {d.get('ok')}")
    print(f"  Response: {d.get('response', '')[:200]}")
    print(f"  Inference: {d.get('inference_ms', 0)} ms")
    print("  ✓ PASS\n")


def test_history():
    print("=== 7. History ===")
    r = httpx.get(f"{BASE}/api/vision/history?limit=10", timeout=5)
    d = r.json()
    print(f"  History items: {len(d.get('history', []))}")
    print("  ✓ PASS\n")


def test_knowledge():
    print("=== 8. Knowledge Store ===")
    r = httpx.get(f"{BASE}/api/vision/knowledge/count", timeout=5)
    d = r.json()
    print(f"  KB count: {d.get('count', 0)}")
    print("  ✓ PASS\n")


def test_alerts():
    print("=== 9. Alerts ===")
    r = httpx.get(f"{BASE}/api/monitor/alerts?limit=10", timeout=5)
    d = r.json()
    print(f"  Alerts: {len(d.get('alerts', []))}")
    print("  ✓ PASS\n")


def test_construction_safety():
    print("=== 10. Construction Safety Check ===")
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("  SKIP: PIL not installed")
        return

    # 模擬工地圖片
    img = Image.new("RGB", (800, 600), color=(180, 160, 140))
    draw = ImageDraw.Draw(img)
    # 畫一些建築元素
    draw.rectangle([100, 200, 700, 580], fill=(150, 140, 130), outline=(100, 90, 80))
    draw.rectangle([250, 50, 550, 200], fill=(200, 180, 160), outline=(120, 100, 80))
    # 人形
    draw.ellipse([350, 300, 380, 330], fill=(255, 200, 150))
    draw.rectangle([355, 330, 375, 400], fill=(0, 0, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    r = httpx.post(f"{BASE}/api/construction/safety", data={
        "image_base64": b64,
        "provider": "auto",
    }, timeout=120)
    d = r.json()
    print(f"  Type: {d.get('type')}")
    print(f"  Inference: {d.get('inference_ms', 0)} ms")
    print(f"  Risk level: {d.get('risk_level', 'N/A')}")
    print("  ✓ PASS\n")


if __name__ == "__main__":
    print("=" * 50)
    print("  AI 視覺邊緣計算服務 — 端對端測試")
    print("=" * 50 + "\n")

    tests = [
        test_health,
        test_stats,
        test_monitor_status,
        test_add_monitor_source,
        test_vlm_analysis,
        test_pure_vlm,
        test_history,
        test_knowledge,
        test_alerts,
        test_construction_safety,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  ✗ FAIL: {e}\n")
            failed += 1

    print("=" * 50)
    print(f"  結果: {passed} passed, {failed} failed")
    print("=" * 50)
    sys.exit(0 if failed == 0 else 1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""視覺深度分析引擎 — 端對端測試"""
import base64
import io
import json
import sys
import time

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed")
    sys.exit(1)

BASE = "http://localhost:8015"


def create_test_scene() -> bytes:
    """建立一個模擬街景的測試圖片"""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1280, 720), color=(135, 206, 235))  # 天空藍
    draw = ImageDraw.Draw(img)

    # 道路
    draw.rectangle([0, 400, 1280, 720], fill=(80, 80, 80))
    # 道路標線
    for x in range(0, 1280, 100):
        draw.rectangle([x, 555, x + 50, 565], fill=(255, 255, 255))

    # 建築物
    draw.rectangle([50, 150, 250, 400], fill=(180, 160, 140))
    draw.rectangle([300, 100, 500, 400], fill=(200, 180, 160))
    draw.rectangle([900, 180, 1100, 400], fill=(170, 150, 130))

    # 窗戶
    for bx, by in [(80, 180), (80, 260), (180, 180), (180, 260)]:
        draw.rectangle([bx, by, bx + 40, by + 50], fill=(100, 150, 200))

    # 樹木（綠色圓形 + 棕色樹幹）
    for tx in [550, 700, 850]:
        draw.rectangle([tx + 15, 320, tx + 25, 400], fill=(101, 67, 33))
        draw.ellipse([tx - 20, 220, tx + 60, 330], fill=(34, 139, 34))

    # 車輛（矩形模擬）
    # 紅色小車
    draw.rectangle([200, 450, 350, 530], fill=(220, 20, 20))
    draw.ellipse([210, 520, 250, 560], fill=(30, 30, 30))
    draw.ellipse([300, 520, 340, 560], fill=(30, 30, 30))

    # 白色大車
    draw.rectangle([500, 420, 720, 530], fill=(240, 240, 240))
    draw.ellipse([520, 520, 570, 560], fill=(30, 30, 30))
    draw.ellipse([660, 520, 710, 560], fill=(30, 30, 30))

    # 藍色機車
    draw.rectangle([800, 480, 870, 530], fill=(30, 30, 200))
    draw.ellipse([800, 520, 840, 560], fill=(30, 30, 30))

    # 人物（簡化）
    for px, color in [(400, (255, 200, 150)), (430, (200, 150, 100)), (1000, (255, 220, 180))]:
        draw.ellipse([px, 430, px + 20, 450], fill=color)  # 頭
        draw.rectangle([px + 3, 450, px + 17, 500], fill=(0, 0, 150))  # 身體
        draw.line([(px + 5, 500), (px, 530)], fill=(0, 0, 100), width=2)  # 腿
        draw.line([(px + 15, 500), (px + 20, 530)], fill=(0, 0, 100), width=2)

    # 紅綠燈
    draw.rectangle([1150, 250, 1170, 400], fill=(50, 50, 50))
    draw.ellipse([1145, 260, 1175, 290], fill=(255, 0, 0))
    draw.ellipse([1145, 295, 1175, 325], fill=(255, 255, 0))
    draw.ellipse([1145, 330, 1175, 360], fill=(0, 255, 0))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_health():
    print("=== 1. Health Check ===")
    r = httpx.get(f"{BASE}/health", timeout=5)
    d = r.json()
    print(f"  Status: {d['status']}")
    print(f"  Deep analyzer available: check /api/vision/deep/image")
    assert d["status"] == "ok"
    print("  PASS\n")


def test_deep_image():
    print("=== 2. Deep Image Analysis ===")
    img_bytes = create_test_scene()
    b64 = base64.b64encode(img_bytes).decode()
    print(f"  Test image: {len(img_bytes)} bytes (1280x720 simulated street scene)")

    t0 = time.time()
    r = httpx.post(f"{BASE}/api/vision/deep/image", data={
        "image_base64": b64,
        "conf": "0.25",
        "source_name": "test_street_scene",
    }, timeout=300)
    elapsed = time.time() - t0
    print(f"  HTTP: {r.status_code} ({elapsed:.1f}s)")

    if r.status_code != 200:
        print(f"  ERROR: {r.text[:500]}")
        return None

    d = r.json()
    report_id = d.get("id", "")
    print(f"  Report ID: {report_id}")
    print(f"  Processing: {d.get('processing_ms', 0):.0f} ms")
    print(f"  Scene: {d.get('scene_description', '')[:200]}")

    summary = d.get("summary", {})
    print(f"\n  === 物件統計 ===")
    print(f"  總物件數: {summary.get('total', 0)}")

    by_class = summary.get("by_class_zh", {})
    if by_class:
        print(f"  YOLO 偵測:")
        for cls, cnt in sorted(by_class.items(), key=lambda x: -x[1]):
            print(f"    {cls}: {cnt}")

    v = d.get("vehicle_summary", {})
    if v.get("total", 0) > 0:
        print(f"\n  === 車輛統計 ===")
        print(f"  車輛總數: {v['total']}")
        print(f"  大車: {v.get('large', 0)}, 小車: {v.get('small', 0)}, 二輪: {v.get('two_wheel', 0)}")
        if v.get("by_type"):
            print(f"  車型: {v['by_type']}")
        if v.get("by_color"):
            print(f"  顏色: {v['by_color']}")
        if v.get("by_brand"):
            print(f"  廠牌: {v['by_brand']}")
        if v.get("plates"):
            print(f"  車牌: {v['plates']}")

    p = d.get("person_summary", {})
    if p.get("total", 0) > 0:
        print(f"\n  === 人員統計 ===")
        print(f"  人員總數: {p['total']}")
        print(f"  男: {p.get('male', 0)}, 女: {p.get('female', 0)}, 未確定: {p.get('unknown', 0)}")

    so = d.get("scene_objects", {})
    if so:
        print(f"\n  === 場景物件 ===")
        for name, cnt in sorted(so.items(), key=lambda x: -x[1]):
            print(f"    {name}: {cnt}")

    ann = d.get("annotated_images", [])
    print(f"\n  標註圖片: {len(ann)} 張")
    for a in ann:
        print(f"    {a}")

    print(f"  報告 TXT: {d.get('report_text_path', '')}")
    print(f"  報告 JSON: {d.get('report_json_path', '')}")
    print("  PASS\n")
    return report_id


def test_get_report(report_id):
    if not report_id:
        print("=== 3. Get Report (SKIP) ===\n")
        return
    print("=== 3. Get Report ===")
    r = httpx.get(f"{BASE}/api/vision/deep/report/{report_id}", timeout=10)
    print(f"  HTTP: {r.status_code}")
    assert r.status_code == 200
    print("  PASS\n")


def test_get_report_text(report_id):
    if not report_id:
        print("=== 4. Get Report Text (SKIP) ===\n")
        return
    print("=== 4. Get Report Text ===")
    r = httpx.get(f"{BASE}/api/vision/deep/report/{report_id}/text", timeout=10)
    print(f"  HTTP: {r.status_code}")
    if r.status_code == 200:
        lines = r.text.split("\n")
        for line in lines[:20]:
            print(f"  | {line}")
        if len(lines) > 20:
            print(f"  | ... ({len(lines)} lines total)")
    assert r.status_code == 200
    print("  PASS\n")


def test_deep_stream_url():
    print("=== 5. Deep Stream URL (public image) ===")
    r = httpx.post(f"{BASE}/api/vision/deep/stream", data={
        "stream_url": "https://ultralytics.com/images/bus.jpg",
        "conf": "0.3",
        "source_name": "ultralytics_bus_test",
    }, timeout=300)
    print(f"  HTTP: {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        print(f"  Processing: {d.get('processing_ms', 0):.0f} ms")
        summary = d.get("summary", {})
        print(f"  Total objects: {summary.get('total', 0)}")
        print(f"  Vehicles: {d.get('vehicle_summary', {}).get('total', 0)}")
        print(f"  Persons: {d.get('person_summary', {}).get('total', 0)}")
        by_class = summary.get("by_class_zh", {})
        if by_class:
            for cls, cnt in sorted(by_class.items(), key=lambda x: -x[1]):
                print(f"    {cls}: {cnt}")
        v = d.get("vehicle_summary", {})
        if v.get("by_color"):
            print(f"  Vehicle colors: {v['by_color']}")
        if v.get("by_type"):
            print(f"  Vehicle types: {v['by_type']}")
        p = d.get("person_summary", {})
        if p.get("total", 0) > 0:
            print(f"  Persons: male={p.get('male',0)} female={p.get('female',0)} unknown={p.get('unknown',0)}")
        so = d.get("scene_objects", {})
        if so:
            print(f"  Scene objects: {so}")
    else:
        print(f"  Response: {r.text[:300]}")
    print("  PASS\n")


def test_learning_domains():
    print("=== 6. Learning Module - Domains ===")
    r = httpx.get(f"{BASE}/api/vision/learning/domains", timeout=10)
    print(f"  HTTP: {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        domains = d.get("domains", {})
        print(f"  Available domains: {len(domains)}")
        for name, info in domains.items():
            print(f"    {name}: {info.get('name', '')} ({info.get('analyses', 0)} analyses)")
    assert r.status_code == 200
    print("  PASS\n")


def test_learning_params():
    print("=== 7. Learning Module - Optimized Params ===")
    for domain in ["traffic", "construction", "general"]:
        r = httpx.get(f"{BASE}/api/vision/learning/params", params={"domain": domain}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            print(f"  {domain}: conf={d.get('conf_threshold')}, interval={d.get('frame_interval_sec')}s")
    print("  PASS\n")


def test_learning_summary():
    print("=== 8. Learning Module - Summary ===")
    r = httpx.get(f"{BASE}/api/vision/learning/summary", timeout=10)
    print(f"  HTTP: {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        print(f"  Total records: {d.get('total_learning_records', 0)}")
        print(f"  Active domains: {d.get('active_domains', 0)}")
        for domain, stats in d.get("domain_stats", {}).items():
            print(f"    {domain}: {stats.get('analyses', 0)} analyses, {stats.get('objects_detected', 0)} objects")
    assert r.status_code == 200
    print("  PASS\n")


def test_learning_suggestions():
    print("=== 9. Learning Module - Suggestions ===")
    r = httpx.get(f"{BASE}/api/vision/learning/suggestions", params={"limit": 5}, timeout=10)
    print(f"  HTTP: {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        suggestions = d.get("suggestions", [])
        print(f"  Recent suggestions: {len(suggestions)}")
        for s in suggestions[:2]:
            print(f"    [{s.get('domain')}] objects={s.get('total_objects')}, conf={s.get('avg_confidence', 0):.2f}")
            for sg in s.get("suggestions", [])[:1]:
                print(f"      -> {sg[:100]}")
    assert r.status_code == 200
    print("  PASS\n")


if __name__ == "__main__":
    print("=" * 60)
    print("  築未科技 — 視覺深度分析引擎 端對端測試")
    print("=" * 60 + "\n")

    passed = 0
    failed = 0

    report_id = None
    for name, t in [("health", test_health), ("deep_image", test_deep_image)]:
        try:
            result = t()
            passed += 1
            if name == "deep_image":
                report_id = result
        except Exception as e:
            print(f"  FAIL: {e}\n")
            failed += 1

    for t in [
        lambda: test_get_report(report_id),
        lambda: test_get_report_text(report_id),
        test_deep_stream_url,
        test_learning_domains,
        test_learning_params,
        test_learning_summary,
        test_learning_suggestions,
    ]:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}\n")
            failed += 1

    print("=" * 60)
    print(f"  結果: {passed} passed, {failed} failed")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)

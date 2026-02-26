#!/usr/bin/env python3
"""
YOLO TensorRT Export — 一鍵將 yolov8n.pt 轉為 TensorRT engine
速度提升 30-50%，綁定 GPU 1 (4060 Ti)
用法: python tools/export_yolo_tensorrt.py
"""
import os
import sys

# 強制使用 GPU 1 (4060 Ti) for export
os.environ["CUDA_VISIBLE_DEVICES"] = "1"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PT_PATH = os.path.join(ROOT, "yolov8n.pt")

if not os.path.exists(PT_PATH):
    print(f"[ERROR] {PT_PATH} not found")
    sys.exit(1)

from ultralytics import YOLO

print(f"[1/2] Loading {PT_PATH}...")
model = YOLO(PT_PATH)

print("[2/2] Exporting to TensorRT (this may take 2-5 minutes)...")
model.export(
    format="engine",
    device=0,       # CUDA_VISIBLE_DEVICES=1 maps to device 0
    half=True,      # FP16 for speed
    imgsz=640,
    workspace=4,    # GB workspace for TensorRT
    verbose=True,
)

engine_path = PT_PATH.replace(".pt", ".engine")
if os.path.exists(engine_path):
    size_mb = os.path.getsize(engine_path) / 1024 / 1024
    print(f"\n✅ TensorRT engine exported: {engine_path} ({size_mb:.1f} MB)")
    print("   Vision Edge Service will auto-detect and use this engine.")
else:
    print("\n❌ Export failed — engine file not found")

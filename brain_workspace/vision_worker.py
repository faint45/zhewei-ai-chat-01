# -*- coding: utf-8 -*-
"""
築未科技 — 視覺執行中樞（D:\brain_workspace）
專供 venv_vision (Python 3.12) 調用 YOLOv8 模型，RTX 4060 Ti CUDA 加速。
輸出 JSON 至 stdout，供 agent_tools.run_vision_engine 解析。
"""
import json
import os
import sys

import torch
from ultralytics import YOLO


def main(image_path: str) -> None:
    """
    視覺執行中樞：調用 RTX 4060 Ti 進行辨識。
    輸出 JSON：status, detected, detected_classes, progress, device, timestamp。
    """
    model_path = r"D:\brain_workspace\models\best.pt"
    if not os.path.exists(model_path):
        model_path = "yolov8n.pt"

    if not os.path.exists(image_path):
        print(json.dumps({"status": "error", "error": "Image not found", "detected": []}, ensure_ascii=False))
        return

    try:
        device = "0" if torch.cuda.is_available() else "cpu"
        model = YOLO(model_path)
        results = model.predict(source=image_path, device=device, verbose=False)

        detected_objects = []
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0]) if hasattr(box.cls, "__getitem__") else int(box.cls)
                conf = float(box.conf[0]) if hasattr(box.conf, "__getitem__") else float(box.conf)
                detected_objects.append({
                    "class": model.names[cls_id],
                    "confidence": round(conf, 4),
                    "bbox": box.xyxy[0].tolist(),
                })

        progress_val = 85
        detected_classes = [x["class"] for x in detected_objects]

        output = {
            "status": "success",
            "ok": True,
            "detected": detected_objects,
            "detected_classes": detected_classes,
            "detected_objects": detected_classes,
            "progress": progress_val,
            "device": "CUDA" if device == "0" else "CPU",
            "timestamp": os.path.getmtime(image_path),
        }
        print(json.dumps(output, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e), "detected": []}, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print(json.dumps({"status": "error", "error": "Usage: vision_worker.py <image_path>", "detected": []}, ensure_ascii=False))

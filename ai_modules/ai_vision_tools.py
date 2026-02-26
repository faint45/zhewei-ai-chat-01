"""
築未科技大腦 - AI 視覺模擬與邊緣分析
邊緣偵測、影像分析、物件偵測（需 opencv-python，可選 ultralytics）
"""
import os
from pathlib import Path

BASE = Path(__file__).parent
try:
    from brain_data_config import VISION_OUTPUT_DIR
    OUTPUT_DIR = VISION_OUTPUT_DIR
except ImportError:
    OUTPUT_DIR = BASE / "vision_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def edge_detect(image_path: str, output_name: str = "edges.png", low: int = 50, high: int = 150) -> str:
    """
    邊緣偵測（Canny）。需 opencv-python。
    image_path: 專案內圖片路徑
    low, high: Canny 閾值（預設 50, 150）
    """
    try:
        import cv2
    except ImportError:
        return "[需安裝] pip install opencv-python"

    path = (BASE / image_path.lstrip("./")).resolve()
    if not path.exists():
        return f"[錯誤] 找不到圖片: {image_path}"
    if not str(path).startswith(str(BASE)):
        return "[拒絕] 僅能處理專案內圖片"

    try:
        img = cv2.imread(str(path))
        if img is None:
            return f"[錯誤] 無法讀取: {image_path}"
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, int(low), int(high))
        out = OUTPUT_DIR / (output_name or "edges.png")
        cv2.imwrite(str(out), edges)
        return f"邊緣圖已儲存: {out}"
    except Exception as e:
        return f"[錯誤] {e}"


def image_analyze(image_path: str) -> str:
    """
    影像基本分析：尺寸、通道、亮度統計。需 opencv-python。
    """
    try:
        import cv2
    except ImportError:
        return "[需安裝] pip install opencv-python"

    path = (BASE / image_path.lstrip("./")).resolve()
    if not path.exists():
        return f"[錯誤] 找不到圖片: {image_path}"
    if not str(path).startswith(str(BASE)):
        return "[拒絕] 僅能處理專案內圖片"

    try:
        img = cv2.imread(str(path))
        if img is None:
            return f"[錯誤] 無法讀取: {image_path}"
        h, w, c = img.shape
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_bright = float(gray.mean())
        std_bright = float(gray.std())
        lines = [
            f"尺寸: {w} x {h}, 通道: {c}",
            f"亮度平均: {mean_bright:.1f}, 標準差: {std_bright:.1f}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"[錯誤] {e}"


def object_detect(image_path: str, output_name: str = "detected.png") -> str:
    """
    物件偵測（YOLO）。需 opencv-python 與 ultralytics。
    pip install ultralytics
    """
    try:
        from ultralytics import YOLO
        import cv2
    except ImportError:
        return "[需安裝] pip install ultralytics opencv-python"

    path = (BASE / image_path.lstrip("./")).resolve()
    if not path.exists():
        return f"[錯誤] 找不到圖片: {image_path}"
    if not str(path).startswith(str(BASE)):
        return "[拒絕] 僅能處理專案內圖片"

    try:
        model = YOLO("yolov8n.pt")  # nano，輕量
        results = model(str(path))
        out = OUTPUT_DIR / (output_name or "detected.png")
        annotated = results[0].plot()
        cv2.imwrite(str(out), annotated)
        dets = results[0].boxes
        labels = []
        if dets is not None:
            names = results[0].names
            for b in dets:
                cls_id = int(b.cls[0])
                conf = float(b.conf[0])
                labels.append(f"{names.get(cls_id, cls_id)} {conf:.2f}")
        summary = ", ".join(labels[:15]) if labels else "無偵測到物件"
        return f"已儲存: {out}\n偵測: {summary}"
    except Exception as e:
        return f"[錯誤] {e}"


def scene_simulate(image_path: str, prompt: str = "") -> str:
    """
    視覺模擬：結合 AI 描述影像內容。需 ai_providers。
    """
    try:
        from ai_providers import ask_sync
    except ImportError:
        return "[錯誤] 無法載入 ai_providers"

    path = (BASE / image_path.lstrip("./")).resolve()
    if not path.exists():
        return f"[錯誤] 找不到圖片: {image_path}"

    analyze = image_analyze(image_path)
    if analyze.startswith("[") and "錯誤" in analyze:
        return analyze

    q = prompt.strip() or "請簡述此影像可能包含的內容、場景與重點。"
    full = f"【影像資訊】{analyze}\n\n【請描述】{q}"
    try:
        resp, _ = ask_sync(full, ensemble=False)
        return resp or "[無回覆]"
    except Exception as e:
        return f"[錯誤] {e}"


VISION_TOOL_MAP = {
    "edge_detect": lambda args: edge_detect(
        args[0] if args else "",
        args[1] if len(args) > 1 else "edges.png",
        int(args[2]) if len(args) > 2 else 50,
        int(args[3]) if len(args) > 3 else 150,
    ),
    "image_analyze": lambda args: image_analyze(args[0] if args else ""),
    "object_detect": lambda args: object_detect(
        args[0] if args else "",
        args[1] if len(args) > 1 else "detected.png",
    ),
    "scene_simulate": lambda args: scene_simulate(
        args[0] if args else "",
        args[1] if len(args) > 1 else "",
    ),
}


def tool_descriptions_vision() -> str:
    """視覺工具說明，供 Agent 參考。"""
    return """
AI 視覺與邊緣分析工具：
- edge_detect: 邊緣偵測(Canny) → TOOL: edge_detect(["圖片路徑", "輸出檔名", low, high])
- image_analyze: 影像基本分析 → TOOL: image_analyze(["圖片路徑"])
- object_detect: 物件偵測(YOLO) → TOOL: object_detect(["圖片路徑", "輸出檔名"])
- scene_simulate: 以 AI 描述影像場景 → TOOL: scene_simulate(["圖片路徑", "描述提示"])
"""

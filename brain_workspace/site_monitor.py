# -*- coding: utf-8 -*-
"""
築未科技 — 工地視覺監控（D:\\brain_workspace）
監看 input 目錄，以 Python 3.12 venv_vision 執行 YOLOv8 辨識，結果寫入 Z 槽報表，影像移至 processed。
路徑與 D:\\brain_workspace、Z:\\Zhewei_Brain 對齊。
"""
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(r"D:\brain_workspace")
INPUT_DIR = ROOT / "input"
PROCESSED_DIR = ROOT / "processed"
# 3.12 虛擬環境 Python（請依實際路徑調整）
VENV_PY = ROOT / "venv_vision" / "Scripts" / "python.exe"
if not VENV_PY.exists():
    VENV_PY = ROOT / "venv_vision" / "bin" / "python"
VISION_SCRIPT = ROOT / "vision_worker.py"
REPORT_SCRIPT = ROOT / "report_tools.py"
POLL_INTERVAL = 10


def run_vision(image_path: str) -> dict:
    """以 3.12 venv 執行 vision_worker.py，回傳 JSON 結果。"""
    cmd = [str(VENV_PY), str(VISION_SCRIPT), image_path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace", cwd=str(ROOT))
        out = r.stdout.strip() or r.stderr.strip()
        if not out:
            return {"ok": False, "status": "error", "message": "視覺引擎無輸出", "detected": []}
        return json.loads(out)
    except subprocess.TimeoutExpired:
        return {"ok": False, "status": "error", "message": "視覺引擎逾時", "detected": []}
    except json.JSONDecodeError:
        return {"ok": False, "status": "error", "message": out[:200], "detected": []}
    except Exception as e:
        return {"ok": False, "status": "error", "message": str(e), "detected": []}


def save_report(vision_results: dict) -> dict:
    """將辨識結果寫入 Z 槽報表（直接 import report_tools）。"""
    try:
        import sys
        sys.path.insert(0, str(ROOT))
        from report_tools import save_results_and_report
        return save_results_and_report(vision_results)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"監控目錄: {INPUT_DIR}，每 {POLL_INTERVAL} 秒檢查一次。")
    while True:
        try:
            images = [p for p in INPUT_DIR.glob("*.*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")]
            for img in images:
                result = run_vision(str(img))
                save_report(result)
                dest = PROCESSED_DIR / img.name
                if dest.exists():
                    dest.unlink()
                img.rename(dest)
                print(f"已處理: {img.name} -> {result.get('detected', [])}")
        except Exception as e:
            print(f"錯誤: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()

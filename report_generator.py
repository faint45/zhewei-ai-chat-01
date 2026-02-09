# -*- coding: utf-8 -*-
"""
築未科技 — 進度報表生成
根據視覺辨識結果自動對應合約項目、寫入 JSONL 日誌與 CSV 週報，同步至 Z 槽。數值進度以 LaTeX 格式 $X\%$ 呈現。
"""
import csv
import json
import os
from datetime import datetime
from pathlib import Path

Z_ROOT = Path(os.environ.get("ZHEWEI_MEMORY_ROOT", "Z:/Zhewei_Brain"))
REPORT_ROOT = Z_ROOT / "Reports"
CONTRACT_DATA = Z_ROOT / "Contract" / "items.json"


def _latex_percent(pct: int | float) -> str:
    """進度數值轉 LaTeX 格式，例：85 -> \"$85\\%$\" """
    return f"${int(pct)}\\%$"


def generate_progress_report(vision_results: dict) -> str:
    """
    根據視覺辨識結果，自動對應合約項目並生成報表。
    vision_results 需含 "detected"（物件名稱列表）；可選 "summary"、"device" 等。
    進度以 LaTeX 格式 $X\%$ 呈現。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    detected_items = vision_results.get("detected", vision_results.get("detected_objects", []))
    if isinstance(detected_items, str):
        detected_items = [x.strip() for x in detected_items.split(",") if x.strip()]

    status = "施工中" if any(x in detected_items for x in ["Excavator", "Crane"]) else "巡檢中"
    progress_pct = vision_results.get("progress", 100)
    progress_latex = _latex_percent(progress_pct)

    report_entry = {
        "日期": now,
        "地點": "國道民雄段",
        "偵測物件": ", ".join(detected_items),
        "當前狀態": status,
        "進度": progress_latex,
        "備註": "由 築未大腦 自動生成",
    }

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    log_file = REPORT_ROOT / f"Daily_Log_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report_entry, ensure_ascii=False) + "\n")

    csv_path = REPORT_ROOT / "Weekly_Progress_Summary.csv"
    header = not csv_path.exists()
    try:
        import pandas as pd
        df = pd.DataFrame([report_entry])
        df.to_csv(csv_path, mode="a", index=False, header=header, encoding="utf-8-sig")
    except ImportError:
        with csv_path.open("a", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=report_entry.keys())
            if header:
                w.writeheader()
            w.writerow(report_entry)

    return f"報表已更新並同步至 Z 槽：{csv_path.name}，進度：{progress_latex}"
# -*- coding: utf-8 -*-
"""
築未科技 — 報表工具（D:\\brain_workspace）
負責將辨識結果轉為 Excel 相容 CSV；存檔路徑依 ZHEWEI_MEMORY_ROOT（可設 D 槽，資料都放 D）。
"""
import csv
import json
import os
from datetime import datetime
from pathlib import Path

Z_ROOT = Path(os.environ.get("ZHEWEI_MEMORY_ROOT", "Z:/Zhewei_Brain"))
Z_REPORTS = Z_ROOT / "Reports"
ROOT = Path(os.environ.get("BRAIN_WORKSPACE", r"D:\brain_workspace"))


def results_to_csv(vision_results: dict, location: str = "國道民雄段") -> str:
    """
    將視覺辨識結果轉為一筆報表並寫入 Z 槽 CSV（Excel 相容 utf-8-sig）。
    vision_results 需含 "detected" 或 "detected_objects"。
    回傳寫入的檔案路徑字串。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    detected = vision_results.get("detected", vision_results.get("detected_objects", []))
    if isinstance(detected, str):
        detected = [x.strip() for x in detected.split(",") if x.strip()]

    status = "施工中" if any(x in detected for x in ["Excavator", "Crane"]) else "巡檢中"
    row = {
        "日期": now,
        "地點": location,
        "偵測物件": ", ".join(detected),
        "當前狀態": status,
        "備註": "築未大腦 視覺辨識自動生成",
    }

    Z_REPORTS.mkdir(parents=True, exist_ok=True)
    csv_path = Z_REPORTS / "Weekly_Progress_Summary.csv"
    header = not csv_path.exists()
    with csv_path.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=row.keys())
        if header:
            w.writeheader()
        w.writerow(row)

    # 同日 JSONL 詳細 Log
    log_path = Z_REPORTS / f"Daily_Log_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return str(csv_path)


def save_results_and_report(vision_results: dict, location: str = "國道民雄段") -> dict:
    """
    寫入 CSV + JSONL 後回傳摘要（供 agent_tools 或 site_monitor 使用）。
    """
    try:
        path = results_to_csv(vision_results, location)
        return {"ok": True, "message": f"報表已同步至 Z 槽：{path}", "path": path}
    except Exception as e:
        return {"ok": False, "error": str(e), "message": str(e)}


if __name__ == "__main__":
    # 測試：從 stdin 讀取一行 JSON 辨識結果
    line = input().strip() or '{"detected": ["LPC_Marker", "Worker"]}'
    data = json.loads(line)
    path = results_to_csv(data)
    print(f"✅ 已寫入 {path}")

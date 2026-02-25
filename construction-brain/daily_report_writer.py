# -*- coding: utf-8 -*-
"""
築未科技 Construction Brain
daily_report_writer.py

功能：讀取指定日期的所有 work_events，彙總輸出：
  - DailyReport.md（公共工程施工日誌格式）
  - Progress.csv（進度追蹤表）

用法：
    python daily_report_writer.py --project_id PRJ-001 --date 2026-02-24
    python daily_report_writer.py --project_id PRJ-001  # 使用今天日期
"""

import argparse
import csv
import json
import os
import sqlite3
import uuid
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(os.environ.get("ZHEWEI_BASE", r"C:\ZheweiConstruction"))
DB_PATH = BASE_DIR / "db" / "index.db"


def _load_project_config(project_id: str) -> dict:
    config_path = BASE_DIR / "config" / f"{project_id}.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {
        "project_name": project_id,
        "contractor": "",
        "contract_period": "",
        "start_date": "",
        "end_date": "",
        "supervisor": "",
    }


def _load_events(project_id: str, event_date: str) -> list[dict]:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT json_data FROM work_events WHERE project_id=? AND date=? AND parse_status='ok'",
        (project_id, event_date),
    ).fetchall()
    conn.close()
    return [json.loads(r[0]) for r in rows]


def _load_photos_index(project_id: str, event_date: str) -> list[dict]:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        """SELECT photo_type, sub_type, location_hint, classified_path, description
           FROM photos WHERE project_id=? AND date=? AND status='ok'""",
        (project_id, event_date),
    ).fetchall()
    conn.close()
    return [
        {"type": r[0], "sub_type": r[1], "location": r[2], "path": r[3], "desc": r[4]}
        for r in rows
    ]


def _calc_elapsed_days(start_date_str: str, event_date_str: str) -> int:
    try:
        start = date.fromisoformat(start_date_str)
        target = date.fromisoformat(event_date_str)
        return (target - start).days + 1
    except Exception:
        return 0


def _merge_lists(events: list[dict], key: str) -> list[dict]:
    result = []
    for ev in events:
        result.extend(ev.get(key, []))
    return result


def _first_non_null(events: list[dict], key: str):
    for ev in events:
        val = ev.get(key)
        if val and val != "null":
            return val
    return None


def generate_daily_report(project_id: str, event_date: str) -> Path:
    """
    彙總當日所有 work_events，輸出 DailyReport.md
    回傳輸出檔案路徑
    """
    cfg = _load_project_config(project_id)
    events = _load_events(project_id, event_date)
    photos = _load_photos_index(project_id, event_date)

    elapsed = _calc_elapsed_days(cfg.get("start_date", ""), event_date)
    weather_am = _first_non_null(events, "weather_am") or "—"
    weather_pm = _first_non_null(events, "weather_pm") or "—"

    work_items = _merge_lists(events, "work_items")
    materials = _merge_lists(events, "materials")
    labor = _merge_lists(events, "labor")
    equipment = _merge_lists(events, "equipment")
    safety_issues = _merge_lists(events, "safety_issues")
    problems = list({p for ev in events for p in ev.get("problems", [])})
    plan_tomorrow = list({p for ev in events for p in ev.get("plan_tomorrow", [])})
    notices = list({n for ev in events for n in ev.get("notices", [])})
    important_notes = list({n for ev in events for n in ev.get("important_notes", [])})

    lines = []
    lines.append("# 公共工程施工日誌")
    lines.append("")
    lines.append(f"**表格編號：** {event_date.replace('-','')}_{project_id}")
    lines.append(f"**本日天氣：** 上午 {weather_am}　下午 {weather_pm}")
    lines.append(f"**填表日期：** {event_date}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 工程基本資料")
    lines.append("")
    lines.append(f"| 項目 | 內容 |")
    lines.append(f"|------|------|")
    lines.append(f"| 工程名稱 | {cfg.get('project_name','')} |")
    lines.append(f"| 承攬廠商 | {cfg.get('contractor','')} |")
    lines.append(f"| 開工日期 | {cfg.get('start_date','')} |")
    lines.append(f"| 竣工日期 | {cfg.get('end_date','')} |")
    lines.append(f"| 累計工期 | {elapsed} 天 |")
    lines.append(f"| 預定進度 | {cfg.get('planned_progress_pct','')}% |")
    lines.append(f"| 工地主任 | {cfg.get('supervisor','')} |")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 一、依施工計畫行程之施工概況")
    lines.append("")
    if work_items:
        lines.append("| 工區/里程 | 工項 | 單位 | 本日完成量 | 累計完成量 | 進度% | 備註 |")
        lines.append("|----------|------|------|-----------|-----------|-------|------|")
        for wi in work_items:
            loc = wi.get("location") or ""
            item = wi.get("item") or ""
            unit = wi.get("unit") or ""
            qty = wi.get("qty_today") if wi.get("qty_today") is not None else "—"
            pct = wi.get("progress_pct") if wi.get("progress_pct") is not None else "—"
            note = wi.get("notes") or ""
            lines.append(f"| {loc} | {item} | {unit} | {qty} | — | {pct} | {note} |")
    else:
        lines.append("（本日無施工記錄）")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 二、工地材料管理概況")
    lines.append("")
    if materials:
        lines.append("| 材料名稱 | 單位 | 本日使用量 | 廠商 | 備註 |")
        lines.append("|---------|------|-----------|------|------|")
        for m in materials:
            name = m.get("name") or ""
            unit = m.get("unit") or ""
            qty = m.get("qty_today") if m.get("qty_today") is not None else "—"
            supplier = m.get("supplier") or ""
            note = m.get("notes") or ""
            lines.append(f"| {name} | {unit} | {qty} | {supplier} | {note} |")
    else:
        lines.append("（本日無材料記錄）")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 三、工地人員及機具管理")
    lines.append("")
    lines.append("### 人力")
    if labor:
        lines.append("| 工別 | 本日人數 |")
        lines.append("|------|---------|")
        for lb in labor:
            trade = lb.get("trade") or ""
            cnt = lb.get("count_today") if lb.get("count_today") is not None else "—"
            lines.append(f"| {trade} | {cnt} |")
    else:
        lines.append("（本日無人力記錄）")
    lines.append("")
    lines.append("### 機具")
    if equipment:
        lines.append("| 機具名稱 | 本日使用數量 |")
        lines.append("|---------|------------|")
        for eq in equipment:
            name = eq.get("name") or ""
            cnt = eq.get("count_today") if eq.get("count_today") is not None else "—"
            lines.append(f"| {name} | {cnt} |")
    else:
        lines.append("（本日無機具記錄）")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 四、本日施工項目之技術士（人工確認）")
    lines.append("")
    lines.append("- [ ] 施工項目需要技術士資格　□有　□無（此項如勾選「有」，應附表）")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 五、公共場所安全衛生事項")
    lines.append("")
    lines.append("### (一) 施工前檢查事項")
    lines.append("")
    lines.append("- [ ] 1. 施工勤前教育（含工地預防災害及危客告知）　□有　□無")
    lines.append("- [ ] 2. 確認新進勞工是否投保勞工保險　□有　□無　□新進勞工")
    lines.append("- [ ] 3. 檢查勞工個人防護具　□有　□無")
    lines.append("")
    lines.append("### (二) 工安缺失記錄")
    lines.append("")
    if safety_issues:
        lines.append("| 缺失描述 | 位置 | 嚴重度 | 建議改善 |")
        lines.append("|---------|------|-------|---------|")
        severity_map = {"high": "[CRIT] 高", "medium": "🟡 中", "low": "🟢 低"}
        for si in safety_issues:
            desc = si.get("description") or ""
            loc = si.get("location") or ""
            sev = severity_map.get(si.get("severity", ""), si.get("severity", ""))
            suggestion = "請立即改善" if si.get("severity") == "high" else "應於本日內改善"
            lines.append(f"| {desc} | {loc} | {sev} | {suggestion} |")
    else:
        lines.append("（本日無工安缺失記錄）")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 六、施工取樣試驗紀錄")
    lines.append("")
    lines.append("（人工填寫）")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 七、通知協力廠商辦理事項")
    lines.append("")
    if notices:
        for i, n in enumerate(notices, 1):
            lines.append(f"{i}. {n}")
    else:
        lines.append("（無）")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 八、重要事項記錄")
    lines.append("")
    all_important = problems + important_notes
    if all_important:
        for i, n in enumerate(all_important, 1):
            lines.append(f"{i}. {n}")
    else:
        lines.append("（無）")
    lines.append("")

    if plan_tomorrow:
        lines.append("---")
        lines.append("")
        lines.append("## 九、明日施工計畫")
        lines.append("")
        for i, p in enumerate(plan_tomorrow, 1):
            lines.append(f"{i}. {p}")
        lines.append("")

    if photos:
        lines.append("---")
        lines.append("")
        lines.append("## 今日附件索引")
        lines.append("")
        lines.append("| 類別 | 子類型 | 位置 | 說明 | 檔名 |")
        lines.append("|------|-------|------|------|------|")
        for ph in photos:
            fname = Path(ph["path"]).name if ph.get("path") else ""
            lines.append(
                f"| {ph.get('type','')} | {ph.get('sub_type','')} | "
                f"{ph.get('location','')} | {ph.get('desc','')} | {fname} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("**簽章：工地主任 ＿＿＿＿＿＿＿＿＿＿＿＿**")
    lines.append("")
    lines.append(f"> 本日誌由「築未科技 Construction Brain」自動彙整產生｜{datetime.now().strftime('%Y-%m-%d %H:%M')}")

    out_dir = BASE_DIR / "projects" / project_id / "02_Output" / "Reports" / event_date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "DailyReport.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[daily_report] [OK] DailyReport.md → {out_path}")
    return out_path


def generate_progress_csv(project_id: str, event_date: str) -> Path:
    """
    彙總當日所有 work_events 的 work_items，輸出 Progress.csv
    同一天重跑：覆蓋同 event_date 的列
    """
    events = _load_events(project_id, event_date)
    work_items = _merge_lists(events, "work_items")

    out_dir = BASE_DIR / "projects" / project_id / "02_Output" / "Reports" / event_date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "Progress.csv"

    cumulative_path = BASE_DIR / "projects" / project_id / "02_Output" / "Progress_cumulative.csv"

    fieldnames = [
        "project_id", "date", "section", "trade", "work_item",
        "unit", "qty_today", "qty_cumulative", "qty_contract",
        "progress_pct", "status", "notes", "source", "event_id",
    ]

    existing_rows = []
    if cumulative_path.exists():
        with open(cumulative_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            existing_rows = [r for r in reader if r.get("date") != event_date]

    new_rows = []
    for wi in work_items:
        qty_today = wi.get("qty_today")
        qty_prev = sum(
            float(r.get("qty_today") or 0)
            for r in existing_rows
            if r.get("work_item") == wi.get("item") and r.get("section") == wi.get("location")
        )
        qty_cumulative = (qty_prev + float(qty_today)) if qty_today is not None else qty_prev

        row = {
            "project_id": project_id,
            "date": event_date,
            "section": wi.get("location") or "",
            "trade": "",
            "work_item": wi.get("item") or "",
            "unit": wi.get("unit") or "",
            "qty_today": qty_today if qty_today is not None else "",
            "qty_cumulative": round(qty_cumulative, 3),
            "qty_contract": "",
            "progress_pct": wi.get("progress_pct") if wi.get("progress_pct") is not None else "",
            "status": "in_progress",
            "notes": wi.get("notes") or "",
            "source": "auto",
            "event_id": "",
        }
        new_rows.append(row)

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_rows)

    all_rows = existing_rows + new_rows
    with open(cumulative_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"[daily_report] [OK] Progress.csv → {out_path}")
    print(f"[daily_report] [OK] 累計進度表更新 → {cumulative_path}")
    return out_path


def run(project_id: str, event_date: str):
    print(f"\n{'='*50}")
    print(f"  築未科技 日報產生器")
    print(f"  專案：{project_id}　日期：{event_date}")
    print(f"{'='*50}\n")
    events = _load_events(project_id, event_date)
    if not events:
        print("[daily_report] [WARN] 找不到今日工項資料，日報將以空白格式輸出")

    report_path = generate_daily_report(project_id, event_date)
    csv_path = generate_progress_csv(project_id, event_date)
    print(f"\n完成！請查看：\n  {report_path}\n  {csv_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="築未科技 — 施工日誌 + 進度 CSV 產生器")
    parser.add_argument("--project_id", required=True, help="專案代碼")
    parser.add_argument("--date", default="", help="日期 YYYY-MM-DD（空=今天）")
    args = parser.parse_args()
    run(args.project_id, args.date or date.today().isoformat())

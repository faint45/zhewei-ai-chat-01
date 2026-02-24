# -*- coding: utf-8 -*-
"""
築未科技 Construction Brain
safety_engine.py

功能：
  整合來自 work_events（語音/文字抽取）與 photos（照片辨識）的工安缺失，
  輸出：
    - SafetyIssues.csv（缺失追蹤表，可用 Excel 開）
    - RectifyPlan.md（整改計畫書）

用法：
    python safety_engine.py --project_id PRJ-001 --date 2026-02-24
    python safety_engine.py --project_id PRJ-001  # 使用今天
"""

import argparse
import csv
import json
import os
import sqlite3
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_DIR = Path(os.environ.get("ZHEWEI_BASE", r"C:\ZheweiConstruction"))
DB_PATH = BASE_DIR / "db" / "index.db"

SEVERITY_LABEL = {"high": "🔴 高", "medium": "🟡 中", "low": "🟢 低"}
SEVERITY_DUE_DAYS = {"high": 0, "medium": 1, "low": 3}
SEVERITY_SUGGESTION = {
    "high": "立即停工改善，確認安全後方可復工",
    "medium": "應於本日工作結束前完成改善",
    "low": "應於 3 日內完成改善",
}

CSV_FIELDS = [
    "issue_id", "project_id", "date", "location", "issue_type",
    "severity", "description", "suggestion", "owner", "due_date",
    "status", "photo_path", "photo_hash", "source", "verified_by", "verified_at",
]


def _ensure_db():
    if not DB_PATH.exists():
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS safety_issues (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            date TEXT,
            location TEXT,
            issue_type TEXT,
            severity TEXT,
            description TEXT,
            suggestion TEXT,
            owner TEXT,
            due_date TEXT,
            status TEXT,
            photo_path TEXT,
            photo_hash TEXT,
            source TEXT,
            verified_by TEXT,
            verified_at TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def _load_from_work_events(project_id: str, event_date: str) -> list[dict]:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT json_data FROM work_events WHERE project_id=? AND date=? AND parse_status='ok'",
        (project_id, event_date),
    ).fetchall()
    conn.close()
    issues = []
    for row in rows:
        data = json.loads(row[0])
        for si in data.get("safety_issues", []):
            issues.append({
                "description": si.get("description", ""),
                "location": si.get("location", ""),
                "severity": si.get("severity", "medium"),
                "source": "line_text_or_voice",
                "photo_path": "",
                "photo_hash": "",
            })
    return issues


def _load_from_photos(project_id: str, event_date: str) -> list[dict]:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        """SELECT classified_path, hash, safety_json, location_hint
           FROM photos WHERE project_id=? AND date=? AND photo_type='工安缺失' AND status='ok'""",
        (project_id, event_date),
    ).fetchall()
    conn.close()
    issues = []
    for row in rows:
        photo_path, photo_hash, safety_json_str, location_hint = row
        try:
            safety_list = json.loads(safety_json_str or "[]")
        except Exception:
            safety_list = []
        if safety_list:
            for si in safety_list:
                issues.append({
                    "description": si.get("description", ""),
                    "location": si.get("location") or location_hint or "",
                    "severity": si.get("severity", "medium"),
                    "source": "line_photo",
                    "photo_path": photo_path,
                    "photo_hash": photo_hash,
                })
        else:
            issues.append({
                "description": "照片顯示工安缺失（待人工確認）",
                "location": location_hint or "",
                "severity": "medium",
                "source": "line_photo",
                "photo_path": photo_path,
                "photo_hash": photo_hash,
            })
    return issues


def _classify_issue_type(description: str) -> str:
    desc = description.lower()
    mapping = [
        (["安全帽", "頭盔"], "未戴安全帽"),
        (["反光背心", "背心"], "未穿反光背心"),
        (["安全帶", "繫掛"], "未繫安全帶"),
        (["安全鞋", "鋼頭鞋"], "未穿安全鞋"),
        (["防塵", "口罩"], "未戴防塵口罩"),
        (["開口", "護欄", "洞口", "護蓋"], "開口未設護欄"),
        (["邊緣", "安全網", "防墜網"], "邊緣未設安全網"),
        (["坑洞", "警示", "警戒"], "坑洞未設警示"),
        (["電線", "裸露", "電氣"], "電線裸露或亂拉"),
        (["漏電", "斷路器", "感電"], "臨時用電無漏電斷路器"),
        (["通道", "堆放", "雜物"], "通道堆放雜物"),
        (["圍籬", "施工圍"], "未設施工圍籬"),
        (["動火", "焊接", "切割"], "未辦理動火許可"),
    ]
    for keywords, issue_type in mapping:
        if any(k in desc for k in keywords):
            return issue_type
    return "其他工安缺失"


def _deduplicate(issues: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for iss in issues:
        key = (iss["description"][:30], iss["location"][:20])
        if key not in seen:
            seen.add(key)
            result.append(iss)
    return result


def _build_issue_rows(issues: list[dict], project_id: str, event_date: str) -> list[dict]:
    rows = []
    counter = 1
    for iss in issues:
        severity = iss.get("severity", "medium")
        due_days = SEVERITY_DUE_DAYS.get(severity, 1)
        due_date = (date.fromisoformat(event_date) + timedelta(days=due_days)).isoformat()
        issue_type = _classify_issue_type(iss.get("description", ""))
        row = {
            "issue_id": f"SAF-{event_date.replace('-','')}-{counter:03d}",
            "project_id": project_id,
            "date": event_date,
            "location": iss.get("location", ""),
            "issue_type": issue_type,
            "severity": severity,
            "description": iss.get("description", ""),
            "suggestion": SEVERITY_SUGGESTION.get(severity, ""),
            "owner": "",
            "due_date": due_date,
            "status": "open",
            "photo_path": iss.get("photo_path", ""),
            "photo_hash": iss.get("photo_hash", ""),
            "source": iss.get("source", ""),
            "verified_by": "",
            "verified_at": "",
        }
        rows.append(row)
        counter += 1
    return rows


def _save_to_db(rows: list[dict]):
    _ensure_db()
    if not rows:
        return
    conn = sqlite3.connect(DB_PATH)
    for row in rows:
        conn.execute(
            """INSERT OR IGNORE INTO safety_issues
               (id,project_id,date,location,issue_type,severity,description,
                suggestion,owner,due_date,status,photo_path,photo_hash,source,
                verified_by,verified_at,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (row["issue_id"], row["project_id"], row["date"], row["location"],
             row["issue_type"], row["severity"], row["description"], row["suggestion"],
             row["owner"], row["due_date"], row["status"], row["photo_path"],
             row["photo_hash"], row["source"], row["verified_by"], row["verified_at"],
             datetime.now().isoformat()),
        )
    conn.commit()
    conn.close()


def generate_safety_csv(project_id: str, event_date: str) -> Path:
    issues_from_events = _load_from_work_events(project_id, event_date)
    issues_from_photos = _load_from_photos(project_id, event_date)
    all_issues = _deduplicate(issues_from_events + issues_from_photos)
    rows = _build_issue_rows(all_issues, project_id, event_date)
    _save_to_db(rows)

    out_dir = BASE_DIR / "projects" / project_id / "02_Output" / "Reports" / event_date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "SafetyIssues.csv"

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    high_count = sum(1 for r in rows if r["severity"] == "high")
    med_count = sum(1 for r in rows if r["severity"] == "medium")
    print(f"[safety] ✅ SafetyIssues.csv → {out_path}")
    print(f"[safety]    高風險:{high_count} 件｜中風險:{med_count} 件｜合計:{len(rows)} 件")
    return out_path


def generate_rectify_plan(project_id: str, event_date: str) -> Path:
    if not DB_PATH.exists():
        return None

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        """SELECT issue_id,location,issue_type,severity,description,suggestion,due_date,photo_path
           FROM safety_issues WHERE project_id=? AND date=? AND status='open'
           ORDER BY CASE severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END""",
        (project_id, event_date),
    ).fetchall()
    conn.close()

    cfg_path = BASE_DIR / "config" / f"{project_id}.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}

    lines = []
    lines.append("# 工安缺失整改計畫書")
    lines.append("")
    lines.append(f"**工程名稱：** {cfg.get('project_name', project_id)}")
    lines.append(f"**發現日期：** {event_date}")
    lines.append(f"**工地主任：** {cfg.get('supervisor', '')}")
    lines.append(f"**產生時間：** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    if not rows:
        lines.append("本日無工安缺失記錄。")
    else:
        high_rows = [r for r in rows if r[3] == "high"]
        med_rows = [r for r in rows if r[3] == "medium"]
        low_rows = [r for r in rows if r[3] == "low"]

        lines.append(f"## 缺失摘要：共 {len(rows)} 項")
        lines.append("")
        lines.append(f"| 嚴重度 | 件數 |")
        lines.append(f"|-------|------|")
        lines.append(f"| 🔴 高風險（立即改善） | {len(high_rows)} 件 |")
        lines.append(f"| 🟡 中風險（本日改善） | {len(med_rows)} 件 |")
        lines.append(f"| 🟢 低風險（3日內改善）| {len(low_rows)} 件 |")
        lines.append("")
        lines.append("---")
        lines.append("")

        for i, row in enumerate(rows, 1):
            issue_id, location, issue_type, severity, description, suggestion, due_date, photo_path = row
            sev_label = SEVERITY_LABEL.get(severity, severity)
            lines.append(f"## 缺失 {i}：{issue_type}　{sev_label}")
            lines.append("")
            lines.append(f"| 項目 | 內容 |")
            lines.append(f"|------|------|")
            lines.append(f"| 缺失編號 | {issue_id} |")
            lines.append(f"| 位置 | {location} |")
            lines.append(f"| 描述 | {description} |")
            lines.append(f"| 整改建議 | {suggestion} |")
            lines.append(f"| 應改善期限 | {due_date} |")
            lines.append(f"| 責任單位 | （填寫） |")
            lines.append(f"| 確認狀態 | ⬜ 待確認 |")
            if photo_path:
                lines.append(f"| 照片 | `{Path(photo_path).name}` |")
            lines.append("")
            lines.append("**整改確認簽章：＿＿＿＿＿＿　日期：＿＿＿＿＿＿**")
            lines.append("")
            lines.append("---")
            lines.append("")

    lines.append("")
    lines.append("> 本整改計畫由「築未科技 Construction Brain」自動產生｜請工地主任確認後簽署")

    out_dir = BASE_DIR / "projects" / project_id / "02_Output" / "Reports" / event_date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "RectifyPlan.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[safety] ✅ RectifyPlan.md → {out_path}")
    return out_path


def run(project_id: str, event_date: str):
    print(f"\n{'='*50}")
    print(f"  築未科技 工安缺失引擎")
    print(f"  專案：{project_id}　日期：{event_date}")
    print(f"{'='*50}\n")
    csv_path = generate_safety_csv(project_id, event_date)
    rectify_path = generate_rectify_plan(project_id, event_date)
    if rectify_path:
        print(f"\n完成！請查看：\n  {csv_path}\n  {rectify_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="築未科技 — 工安缺失整合引擎")
    parser.add_argument("--project_id", required=True)
    parser.add_argument("--date", default="")
    args = parser.parse_args()
    run(args.project_id, args.date or date.today().isoformat())

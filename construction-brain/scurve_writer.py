# -*- coding: utf-8 -*-
"""
築未科技 Construction Brain
scurve_writer.py

功能：
  讀取 cpm_result.json（CPM 計算結果）+ schedule.json（工項清單）
  → 計算每週/每月計畫累積進度（S 曲線）
  → 讀取 Progress.csv（實際進度）對比
  → 輸出：
      SCurve.html（計畫線 vs 實際線，Plotly 互動式）
      SCurve.csv（數據表，可匯入 Excel）

用法：
    python scurve_writer.py --project_id PRJ-001
"""

import argparse
import csv
import json
import os
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(os.environ.get("ZHEWEI_BASE", r"C:\ZheweiConstruction"))


def _load_schedule(project_id: str) -> tuple[dict, dict]:
    sched_dir = BASE_DIR / "projects" / project_id / "02_Output" / "Schedule"
    schedule_path = sched_dir / "schedule.json"
    cpm_path = sched_dir / "cpm_result.json"

    if not schedule_path.exists():
        raise FileNotFoundError(f"找不到 schedule.json：{schedule_path}")
    if not cpm_path.exists():
        raise FileNotFoundError(f"找不到 cpm_result.json，請先執行 schedule_engine.py")

    schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
    cpm = json.loads(cpm_path.read_text(encoding="utf-8"))
    return schedule, cpm


def _calc_planned_scurve(work_items: list[dict], cpm: dict, freq: str = "week") -> list[dict]:
    """
    計算計畫 S 曲線
    freq: 'week' = 週報，'month' = 月報
    weight_pct 為各工項費用占比（總和應為100）；無則按工期均分
    """
    item_map = {item["id"]: item for item in work_items}

    # 決定各工項的 weight
    total_weight = sum(
        float(item.get("weight_pct") or 0)
        for item in work_items
        if item["id"] in cpm
    )
    if total_weight < 0.1:
        # 無 weight_pct 時，用工期均分
        total_dur = sum(
            int(cpm[item["id"]]["dur"]) for item in work_items if item["id"] in cpm
        )
        for item in work_items:
            nid = item["id"]
            if nid in cpm:
                cpm[nid]["_weight"] = int(cpm[nid]["dur"]) / total_dur * 100
    else:
        for item in work_items:
            nid = item["id"]
            if nid in cpm:
                cpm[nid]["_weight"] = float(item.get("weight_pct") or 0)

    if not cpm:
        return []

    project_start = min(date.fromisoformat(v["start_date"]) for v in cpm.values())
    project_end = max(date.fromisoformat(v["end_date"]) for v in cpm.values())

    # 建立時間軸
    checkpoints = []
    cur = project_start
    while cur <= project_end:
        checkpoints.append(cur)
        if freq == "week":
            cur += timedelta(weeks=1)
        else:
            # 下個月第一天
            year = cur.year + (cur.month // 12)
            month = (cur.month % 12) + 1
            cur = date(year, month, 1)
    if checkpoints[-1] < project_end:
        checkpoints.append(project_end)

    # 每個 checkpoint 計算計畫累積進度
    records = []
    for cp in checkpoints:
        cumulative = 0.0
        for nid, vals in cpm.items():
            start = date.fromisoformat(vals["start_date"])
            end = date.fromisoformat(vals["end_date"])
            dur = int(vals["dur"])
            weight = float(vals.get("_weight", 0))
            if cp < start:
                pct = 0.0
            elif cp >= end:
                pct = 1.0
            else:
                elapsed = (cp - start).days
                pct = min(elapsed / max(dur, 1), 1.0)
            cumulative += weight * pct

        records.append({
            "date": cp.isoformat(),
            "planned_pct": round(min(cumulative, 100.0), 2),
        })

    return records


def _load_actual_progress(project_id: str) -> dict[str, float]:
    """從 Progress_cumulative.csv 讀取每天的實際累積進度"""
    csv_path = BASE_DIR / "projects" / project_id / "02_Output" / "Progress_cumulative.csv"
    if not csv_path.exists():
        return {}

    daily = defaultdict(float)
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = row.get("date", "")
                pct = float(row.get("progress_pct") or 0)
                weight = float(row.get("qty_today") or 0)
                if d:
                    daily[d] = max(daily[d], pct)
    except Exception as e:
        print(f"[scurve] [WARN] 讀取實際進度失敗：{e}")

    return dict(daily)


def _merge_actual(planned: list[dict], actual_daily: dict[str, float]) -> list[dict]:
    """把實際進度合併到計畫資料（用最近一個有資料的日期做插值）"""
    if not actual_daily:
        return planned

    sorted_actual = sorted(actual_daily.items())
    last_known_pct = 0.0

    for rec in planned:
        cp = date.fromisoformat(rec["date"])
        pcts_up_to = [v for d, v in sorted_actual if date.fromisoformat(d) <= cp]
        if pcts_up_to:
            last_known_pct = max(pcts_up_to)
            rec["actual_pct"] = round(last_known_pct, 2)
        elif date.fromisoformat(sorted_actual[0][0]) > cp:
            rec["actual_pct"] = None
        else:
            rec["actual_pct"] = None

    return planned


def generate_scurve_csv(records: list[dict], out_path: Path):
    fieldnames = ["date", "planned_pct", "actual_pct"]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            writer.writerow({
                "date": rec["date"],
                "planned_pct": rec["planned_pct"],
                "actual_pct": rec.get("actual_pct", ""),
            })
    print(f"[scurve] [OK] SCurve.csv → {out_path}")


def generate_scurve_html(records: list[dict], out_path: Path, project_name: str = ""):
    dates = [r["date"] for r in records]
    planned = [r["planned_pct"] for r in records]
    actual = [r.get("actual_pct") for r in records]
    actual_dates = [d for d, v in zip(dates, actual) if v is not None]
    actual_vals = [v for v in actual if v is not None]

    try:
        import plotly.graph_objects as go

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=dates, y=planned,
            mode="lines+markers",
            name="計畫進度（Plan）",
            line=dict(color="#2980B9", width=3),
            marker=dict(size=6),
            hovertemplate="計畫 %{y:.1f}%<br>%{x}<extra></extra>",
        ))

        if actual_vals:
            today = date.today().isoformat()
            fig.add_trace(go.Scatter(
                x=actual_dates, y=actual_vals,
                mode="lines+markers",
                name="實際進度（Actual）",
                line=dict(color="#E74C3C", width=3, dash="dot"),
                marker=dict(size=8, symbol="circle-open"),
                hovertemplate="實際 %{y:.1f}%<br>%{x}<extra></extra>",
            ))
            fig.add_vline(
                x=today,
                line=dict(color="#F39C12", dash="dash", width=2),
                annotation_text="今日",
                annotation_position="top right",
            )

        fig.add_hline(y=100, line=dict(color="#27AE60", dash="dot", width=1))

        fig.update_layout(
            title=dict(
                text=f"{'　' if not project_name else project_name}　工程進度 S 曲線",
                font=dict(size=20)),
            xaxis=dict(title="日期", gridcolor="#ECF0F1", type="date"),
            yaxis=dict(title="累積進度（%）", range=[0, 105], gridcolor="#ECF0F1",
                       ticksuffix="%"),
            plot_bgcolor="#FAFAFA",
            paper_bgcolor="white",
            legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
            font=dict(family="Microsoft JhengHei, Arial", size=13),
            height=520,
            margin=dict(l=60, r=40, t=100, b=60),
            hovermode="x unified",
        )

        fig.write_html(str(out_path), include_plotlyjs="cdn")
        print(f"[scurve] [OK] SCurve.html → {out_path}")

    except ImportError:
        _write_scurve_fallback_html(dates, planned, actual_dates, actual_vals, out_path, project_name)


def _write_scurve_fallback_html(dates, planned, actual_dates, actual_vals, out_path, project_name):
    """Plotly 不可用時的純 SVG S 曲線"""
    rows_html = "".join(
        f"<tr><td>{d}</td><td>{p:.1f}%</td><td></td></tr>"
        for d, p in zip(dates, planned)
    )
    html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<title>{project_name} S 曲線</title>
<style>body{{font-family:Arial;padding:20px}}table{{border-collapse:collapse}}
th,td{{border:1px solid #ddd;padding:6px 12px}}th{{background:#2C3E50;color:white}}</style>
</head><body>
<h2>[SITE] {project_name}　工程進度 S 曲線（數據表）</h2>
<p>安裝 plotly 可獲得互動式圖表：<code>pip install plotly</code></p>
<table><tr><th>日期</th><th>計畫進度</th><th>實際進度</th></tr>{rows_html}</table>
<p style='color:#888'>由「築未科技 Construction Brain」產生</p></body></html>"""
    out_path.write_text(html, encoding="utf-8")
    print(f"[scurve] [OK] SCurve.html（簡易版）→ {out_path}")


def run(project_id: str, freq: str = "week"):
    print(f"\n{'='*55}")
    print(f"  築未科技 S 曲線產生器")
    print(f"  專案：{project_id}　頻率：{freq}")
    print(f"{'='*55}\n")

    schedule, cpm = _load_schedule(project_id)
    work_items = schedule.get("work_items", [])
    project_name = schedule.get("project_name") or project_id

    records = _calc_planned_scurve(work_items, cpm, freq)
    if not records:
        print("[scurve] [ERR] 無法計算 S 曲線，請確認 schedule.json 與 cpm_result.json 正確")
        return

    actual_daily = _load_actual_progress(project_id)
    if actual_daily:
        print(f"[scurve] 找到實際進度資料（{len(actual_daily)} 天），加入對比")
        records = _merge_actual(records, actual_daily)
    else:
        print("[scurve] 無實際進度資料，只顯示計畫線")

    out_dir = BASE_DIR / "projects" / project_id / "02_Output" / "Schedule"
    out_dir.mkdir(parents=True, exist_ok=True)

    generate_scurve_csv(records, out_dir / "SCurve.csv")
    generate_scurve_html(records, out_dir / "SCurve.html", project_name)

    print(f"\n完成！請開啟：{out_dir / 'SCurve.html'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="築未科技 — 進度 S 曲線產生器")
    parser.add_argument("--project_id", required=True)
    parser.add_argument("--freq", default="week", choices=["week", "month"],
                        help="時間軸頻率：week（週）或 month（月）")
    args = parser.parse_args()
    run(args.project_id, args.freq)

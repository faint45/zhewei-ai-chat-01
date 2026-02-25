# -*- coding: utf-8 -*-
"""
築未科技 Construction Brain
schedule_engine.py

功能：
  讀取 schedule.json（工項清單）
  → CPM 計算（ES/EF/LS/LF/TF/FF/要徑）
  → 輸出：
      Gantt.html（甘特圖，Plotly 互動式）
      Network.html（AON 網圖，要徑紅色標示）
      gantt.csv（甘特資料，可匯入 Excel）

用法：
    python schedule_engine.py --project_id PRJ-001 --start 2026-03-01
"""

import argparse
import json
import os
from collections import defaultdict, deque
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(os.environ.get("ZHEWEI_BASE", r"C:\ZheweiConstruction"))


# ─── CPM 計算核心 ───────────────────────────────────────────────────────────

def _topological_sort(items: list[dict]) -> list[str]:
    """Kahn 演算法拓撲排序"""
    in_degree = {item["id"]: 0 for item in items}
    graph = defaultdict(list)
    for item in items:
        for pred in item.get("predecessors", []):
            if pred in in_degree:
                graph[pred].append(item["id"])
                in_degree[item["id"]] += 1

    queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
    order = []
    while queue:
        nid = queue.popleft()
        order.append(nid)
        for succ in graph[nid]:
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    if len(order) != len(items):
        raise ValueError("工項邏輯關係有循環（Cycle Detected），請檢查前置工項設定")
    return order


def calculate_cpm(work_items: list[dict], project_start: date) -> dict[str, dict]:
    """
    計算 CPM（Critical Path Method）

    Returns:
        dict: {item_id: {ES, EF, LS, LF, TF, FF, is_critical, start_date, end_date}}
    """
    item_map = {item["id"]: item for item in work_items}
    topo = _topological_sort(work_items)
    graph_succ = defaultdict(list)
    for item in work_items:
        for pred in item.get("predecessors", []):
            if pred in item_map:
                graph_succ[pred].append(item["id"])

    cpm = {}

    # 前推（Early Start / Early Finish）
    for nid in topo:
        item = item_map[nid]
        dur = max(int(item.get("duration_days") or 1), 1)
        preds = [p for p in item.get("predecessors", []) if p in cpm]
        es = max((cpm[p]["EF"] for p in preds), default=0)
        cpm[nid] = {"ES": es, "EF": es + dur, "dur": dur}

    project_duration = max(v["EF"] for v in cpm.values())

    # 後推（Late Start / Late Finish）
    for nid in reversed(topo):
        succs = [s for s in graph_succ[nid] if s in cpm]
        lf = min((cpm[s]["LS"] for s in succs), default=project_duration)
        dur = cpm[nid]["dur"]
        cpm[nid]["LF"] = lf
        cpm[nid]["LS"] = lf - dur
        cpm[nid]["TF"] = lf - cpm[nid]["EF"]  # Total Float
        cpm[nid]["is_critical"] = cpm[nid]["TF"] == 0

    # Free Float
    for nid in topo:
        succs = [s for s in graph_succ[nid] if s in cpm]
        if succs:
            cpm[nid]["FF"] = min(cpm[s]["ES"] for s in succs) - cpm[nid]["EF"]
        else:
            cpm[nid]["FF"] = cpm[nid]["TF"]

    # 轉換為日曆日期（跳過週末）
    def _add_workdays(start: date, days: int) -> date:
        current = start
        added = 0
        while added < days:
            current += timedelta(days=1)
            if current.weekday() < 5:
                added += 1
        return current

    def _start_plus_workdays(base: date, offset: int) -> date:
        current = base
        added = 0
        while added < offset:
            current += timedelta(days=1)
            if current.weekday() < 5:
                added += 1
        return current

    for nid, vals in cpm.items():
        vals["start_date"] = _start_plus_workdays(project_start, vals["ES"])
        vals["end_date"] = _start_plus_workdays(project_start, vals["EF"])

    return cpm


# ─── 甘特圖 HTML（Plotly） ──────────────────────────────────────────────────

TRADE_COLORS = {
    "土木": "#4A90D9",
    "鋼筋": "#E24C4C",
    "模板": "#F5A623",
    "混凝土": "#7ED321",
    "機電": "#9B59B6",
    "道路": "#1ABC9C",
    "橋梁": "#E67E22",
    "管線": "#3498DB",
    "其他": "#95A5A6",
}


def generate_gantt_html(work_items: list[dict], cpm: dict, out_path: Path, project_name: str = ""):
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("[schedule_engine] [WARN] plotly 未安裝：pip install plotly")
        _write_gantt_fallback_html(work_items, cpm, out_path, project_name)
        return

    item_map = {item["id"]: item for item in work_items}
    fig = go.Figure()

    for item in work_items:
        nid = item["id"]
        if nid not in cpm:
            continue
        vals = cpm[nid]
        trade = item.get("trade", "其他")
        color = TRADE_COLORS.get(trade, "#95A5A6")
        if vals["is_critical"]:
            color = "#C0392B"
            border_color = "#922B21"
        else:
            border_color = color

        label = f"{nid} {item['name']}"
        hover = (
            f"<b>{item['name']}</b><br>"
            f"工項ID：{nid}<br>"
            f"工期：{vals['dur']} 天<br>"
            f"開始：{vals['start_date']}<br>"
            f"完成：{vals['end_date']}<br>"
            f"工種：{trade}<br>"
            f"浮時：{vals['TF']} 天<br>"
            f"{'[CRIT] 要徑工項' if vals['is_critical'] else ''}"
        )
        fig.add_trace(go.Bar(
            x=[vals["dur"]],
            y=[label],
            base=[vals["start_date"].isoformat()],
            orientation="h",
            marker=dict(color=color, line=dict(color=border_color, width=1.5)),
            hovertemplate=hover + "<extra></extra>",
            name=trade,
            showlegend=False,
        ))

    fig.update_layout(
        title=dict(text=f"{'　' if not project_name else project_name}　甘特圖（Gantt Chart）", font=dict(size=18)),
        xaxis=dict(type="date", title="日期", gridcolor="#ECF0F1"),
        yaxis=dict(autorange="reversed", title=""),
        plot_bgcolor="#FAFAFA",
        paper_bgcolor="white",
        height=max(400, len(work_items) * 30 + 150),
        margin=dict(l=250, r=40, t=80, b=60),
        font=dict(family="Microsoft JhengHei, Arial", size=12),
    )

    # 圖例（手動加）
    for trade, color in TRADE_COLORS.items():
        fig.add_trace(go.Bar(x=[None], y=[None], orientation="h",
                             marker_color=color, name=trade, showlegend=True))
    fig.add_trace(go.Bar(x=[None], y=[None], orientation="h",
                         marker_color="#C0392B", name="[CRIT] 要徑", showlegend=True))

    fig.write_html(str(out_path), include_plotlyjs="cdn")
    print(f"[schedule_engine] [OK] Gantt.html → {out_path}")


def _write_gantt_fallback_html(work_items, cpm, out_path, project_name):
    """Plotly 不可用時的 HTML 文字甘特表"""
    rows = []
    for item in work_items:
        nid = item["id"]
        if nid not in cpm:
            continue
        vals = cpm[nid]
        critical = "[CRIT]" if vals["is_critical"] else ""
        rows.append(
            f"<tr style='background:{'#fde8e8' if vals['is_critical'] else 'white'}'>"
            f"<td>{critical}{nid}</td><td>{item['name']}</td>"
            f"<td>{item.get('trade','')}</td><td>{vals['dur']}</td>"
            f"<td>{vals['start_date']}</td><td>{vals['end_date']}</td>"
            f"<td>{vals['TF']}</td></tr>"
        )
    html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<title>{project_name} 甘特圖</title>
<style>body{{font-family:Arial;padding:20px}}table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ddd;padding:8px;text-align:left}}th{{background:#2C3E50;color:white}}</style>
</head><body><h2>{project_name} 工程進度甘特表</h2>
<table><tr><th>ID</th><th>工項</th><th>工種</th><th>工期(天)</th>
<th>開始日</th><th>完成日</th><th>浮時</th></tr>{''.join(rows)}</table>
<p style='color:#888'>[CRIT] 要徑工項（浮時=0）｜由「築未科技 Construction Brain」產生</p>
</body></html>"""
    out_path.write_text(html, encoding="utf-8")
    print(f"[schedule_engine] [OK] Gantt.html（簡易版）→ {out_path}")


# ─── AON 網圖 HTML ──────────────────────────────────────────────────────────

def generate_network_html(work_items: list[dict], cpm: dict, out_path: Path, project_name: str = ""):
    item_map = {item["id"]: item for item in work_items}

    nodes_js = []
    edges_js = []

    for item in work_items:
        nid = item["id"]
        if nid not in cpm:
            continue
        vals = cpm[nid]
        is_critical = vals["is_critical"]
        color = "#C0392B" if is_critical else "#2980B9"
        border = "#922B21" if is_critical else "#1A5276"
        label = f"{nid}\\n{item['name'][:12]}\\nES:{vals['ES']} EF:{vals['EF']}\\nTF:{vals['TF']}"
        nodes_js.append(
            f"{{id:'{nid}',label:`{label}`,color:{{background:'{color}',border:'{border}'}},"
            f"font:{{color:'white',size:11}},shape:'box',margin:8}}"
        )

    for item in work_items:
        for pred in item.get("predecessors", []):
            if pred in item_map:
                is_crit = cpm[item["id"]]["is_critical"] and cpm[pred]["is_critical"]
                color = "#C0392B" if is_crit else "#7F8C8D"
                width = 3 if is_crit else 1
                edges_js.append(
                    f"{{from:'{pred}',to:'{item['id']}',color:'{color}',"
                    f"width:{width},arrows:'to'}}"
                )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{project_name} 進度網圖</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  body{{font-family:'Microsoft JhengHei',Arial;margin:0;background:#F0F4F8}}
  #title{{padding:16px 24px;background:#2C3E50;color:white;font-size:20px}}
  #legend{{padding:8px 24px;background:#ECF0F1;font-size:13px}}
  #network{{width:100%;height:calc(100vh - 100px);background:white}}
</style>
</head><body>
<div id="title">[SITE] {project_name}　進度網圖（AON Network Diagram）</div>
<div id="legend">
  <span style="color:#C0392B;font-weight:bold">■ 要徑工項（Critical Path）</span>　　
  <span style="color:#2980B9">■ 非要徑工項</span>　　
  <span style="color:#888">節點顯示：ES=最早開始 EF=最早完成 TF=總浮時（工作天）</span>　　
  <span style="color:#888">由「築未科技 Construction Brain」產生</span>
</div>
<div id="network"></div>
<script>
var nodes = new vis.DataSet([{','.join(nodes_js)}]);
var edges = new vis.DataSet([{','.join(edges_js)}]);
var container = document.getElementById('network');
var data = {{nodes:nodes,edges:edges}};
var options = {{
  layout:{{hierarchical:{{direction:'LR',sortMethod:'directed',levelSeparation:180,nodeSpacing:80}}}},
  physics:{{enabled:false}},
  interaction:{{dragNodes:true,zoomView:true,dragView:true}},
  nodes:{{borderWidth:2,shadow:true}},
  edges:{{smooth:{{type:'cubicBezier',forceDirection:'horizontal'}},shadow:true}}
}};
new vis.Network(container,data,options);
</script></body></html>"""

    out_path.write_text(html, encoding="utf-8")
    print(f"[schedule_engine] [OK] Network.html → {out_path}")


# ─── 甘特 CSV ───────────────────────────────────────────────────────────────

def generate_gantt_csv(work_items: list[dict], cpm: dict, out_path: Path):
    import csv
    fieldnames = ["id", "name", "trade", "duration_days", "predecessors",
                  "ES", "EF", "LS", "LF", "TF", "FF", "is_critical",
                  "start_date", "end_date", "quantity", "unit", "weight_pct"]
    item_map = {item["id"]: item for item in work_items}
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for item in work_items:
            nid = item["id"]
            if nid not in cpm:
                continue
            vals = cpm[nid]
            row = {
                "id": nid,
                "name": item.get("name", ""),
                "trade": item.get("trade", ""),
                "duration_days": vals["dur"],
                "predecessors": ",".join(item.get("predecessors", [])),
                "ES": vals["ES"], "EF": vals["EF"],
                "LS": vals["LS"], "LF": vals["LF"],
                "TF": vals["TF"], "FF": vals["FF"],
                "is_critical": "是" if vals["is_critical"] else "",
                "start_date": str(vals["start_date"]),
                "end_date": str(vals["end_date"]),
                "quantity": item.get("quantity", ""),
                "unit": item.get("unit", ""),
                "weight_pct": item.get("weight_pct", ""),
            }
            writer.writerow(row)
    print(f"[schedule_engine] [OK] gantt.csv → {out_path}")


# ─── 主流程 ─────────────────────────────────────────────────────────────────

def run(project_id: str, start_date_str: str):
    print(f"\n{'='*55}")
    print(f"  築未科技 CPM 進度網圖引擎")
    print(f"  專案：{project_id}　開工日：{start_date_str}")
    print(f"{'='*55}\n")

    schedule_path = BASE_DIR / "projects" / project_id / "02_Output" / "Schedule" / "schedule.json"
    if not schedule_path.exists():
        print(f"[schedule_engine] [ERR] 找不到 schedule.json，請先執行 schedule_extractor.py")
        return

    schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
    work_items = schedule.get("work_items", [])
    project_name = schedule.get("project_name") or project_id

    if not work_items:
        print("[schedule_engine] [ERR] 工項清單為空")
        return

    print(f"[schedule_engine] 載入工項：{len(work_items)} 項")

    try:
        start_date = date.fromisoformat(start_date_str)
    except ValueError:
        print(f"[schedule_engine] [WARN] 日期格式錯誤，使用今天")
        start_date = date.today()

    cpm = calculate_cpm(work_items, start_date)

    critical_items = [nid for nid, v in cpm.items() if v["is_critical"]]
    total_days = max(v["EF"] for v in cpm.values())
    end_date = max(v["end_date"] for v in cpm.values())

    print(f"[schedule_engine] 要徑工項（{len(critical_items)} 項）：{', '.join(critical_items)}")
    print(f"[schedule_engine] 計畫總工期：{total_days} 工作天｜完工日：{end_date}")

    out_dir = BASE_DIR / "projects" / project_id / "02_Output" / "Schedule"
    out_dir.mkdir(parents=True, exist_ok=True)

    generate_gantt_html(work_items, cpm, out_dir / "Gantt.html", project_name)
    generate_network_html(work_items, cpm, out_dir / "Network.html", project_name)
    generate_gantt_csv(work_items, cpm, out_dir / "gantt.csv")

    cpm_serializable = {
        nid: {k: str(v) if isinstance(v, date) else v for k, v in vals.items()}
        for nid, vals in cpm.items()
    }
    (out_dir / "cpm_result.json").write_text(
        json.dumps(cpm_serializable, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n完成！請開啟：")
    print(f"  甘特圖：{out_dir / 'Gantt.html'}")
    print(f"  網圖：  {out_dir / 'Network.html'}")
    print(f"  CSV：   {out_dir / 'gantt.csv'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="築未科技 — CPM 進度網圖引擎")
    parser.add_argument("--project_id", required=True)
    parser.add_argument("--start", default="", help="開工日期 YYYY-MM-DD（空=今天）")
    args = parser.parse_args()
    run(args.project_id, args.start or date.today().isoformat())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reports" / "business"
REPORT_JSON = REPORT_DIR / "cost_savings_report.json"
REPORT_MD = REPORT_DIR / "cost_savings_report.md"

# 可手動填寫：雲端實際帳單（NTD）
BILLING_FILE = REPORT_DIR / "cloud_billing_actual.json"
# 可手動填寫：你這套本地系統每月成本（NTD）
SYSTEM_COST_FILE = REPORT_DIR / "system_costs.json"

LOG_FILES = [
    ROOT / "Jarvis_Training" / "discord_bot_runtime.log",
    ROOT / "Jarvis_Training" / "discord_bot_autostart.log",
    ROOT / "D" / "brain_workspace" / "brain_system.log",
]

PAT_LOCAL = re.compile(r"POST http://(?:localhost|host\.docker\.internal):11460/api/chat", re.I)
PAT_GEMINI = re.compile(r"POST https://generativelanguage\.googleapis\.com|gemini", re.I)
PAT_CLAUDE = re.compile(r"POST https://api\.anthropic\.com|Claude API", re.I)


def _safe_read(p: Path) -> str:
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _safe_json(p: Path) -> dict:
    if not p.exists():
        return {}
    try:
        obj = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _count(pattern: re.Pattern[str], text: str) -> int:
    return len(pattern.findall(text or ""))


def _to_f(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _ensure_templates() -> None:
    if not BILLING_FILE.exists():
        BILLING_FILE.write_text(
            json.dumps(
                {
                    "period_days": 30,
                    "gemini_cost_ntd": 0,
                    "claude_cost_ntd": 0,
                    "other_cloud_ai_cost_ntd": 0,
                    "note": "填入實際雲端帳單金額，才能得到精確成本比較",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if not SYSTEM_COST_FILE.exists():
        SYSTEM_COST_FILE.write_text(
            json.dumps(
                {
                    "system_fixed_cost_ntd_per_month": 0,
                    "electricity_ntd_per_month": 0,
                    "internet_share_ntd_per_month": 0,
                    "maintenance_labor_ntd_per_month": 0,
                    "note": "填入你本地系統每月實際成本",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_templates()

    details = []
    local_total = 0
    gemini_total = 0
    claude_total = 0

    for p in LOG_FILES:
        txt = _safe_read(p)
        lc = _count(PAT_LOCAL, txt)
        gc = _count(PAT_GEMINI, txt)
        cc = _count(PAT_CLAUDE, txt)
        local_total += lc
        gemini_total += gc
        claude_total += cc
        details.append(
            {
                "file": str(p),
                "local_ollama_calls": lc,
                "gemini_related_hits": gc,
                "claude_related_hits": cc,
            }
        )

    cloud_total = gemini_total + claude_total

    # 估算區間（若未提供真實帳單）
    min_per_call = 0.05
    max_per_call = 0.40
    est_saved_min = round(local_total * min_per_call, 2)
    est_saved_max = round(local_total * max_per_call, 2)

    billing = _safe_json(BILLING_FILE)
    period_days = max(1, int(_to_f(billing.get("period_days", 30), 30)))
    cloud_actual_period = (
        _to_f(billing.get("gemini_cost_ntd", 0))
        + _to_f(billing.get("claude_cost_ntd", 0))
        + _to_f(billing.get("other_cloud_ai_cost_ntd", 0))
    )
    cloud_actual_month = round(cloud_actual_period * (30.0 / period_days), 2)

    system_cost = _safe_json(SYSTEM_COST_FILE)
    system_month = round(
        _to_f(system_cost.get("system_fixed_cost_ntd_per_month", 0))
        + _to_f(system_cost.get("electricity_ntd_per_month", 0))
        + _to_f(system_cost.get("internet_share_ntd_per_month", 0))
        + _to_f(system_cost.get("maintenance_labor_ntd_per_month", 0)),
        2,
    )

    # 一般訂閱費用方案（可對照）
    subscription_plans = [
        {"name": "一般單一訂閱", "monthly_ntd": 650.0},
        {"name": "一般雙訂閱", "monthly_ntd": 1300.0},
        {"name": "一般三訂閱", "monthly_ntd": 2000.0},
    ]
    for p in subscription_plans:
        p["delta_vs_system_ntd"] = round(p["monthly_ntd"] - system_month, 2)

    # 精確比較：雲端實際 vs 本地系統
    exact_delta = round(cloud_actual_month - system_month, 2)
    exact_better = "system" if exact_delta > 0 else ("cloud" if exact_delta < 0 else "equal")

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "evidence_scope": "repo logs + optional billing/system cost files",
        "totals": {
            "local_ollama_calls": local_total,
            "cloud_related_hits": cloud_total,
            "gemini_related_hits": gemini_total,
            "claude_related_hits": claude_total,
        },
        "estimated_savings_ntd": {
            "min": est_saved_min,
            "max": est_saved_max,
            "formula": "local_ollama_calls * cloud_cost_per_call_ntd",
        },
        "exact_comparison_ntd_per_month": {
            "cloud_actual_monthly_ntd": cloud_actual_month,
            "system_monthly_ntd": system_month,
            "delta_cloud_minus_system": exact_delta,
            "winner": exact_better,
            "formula": "cloud_actual_monthly_ntd - system_monthly_ntd",
        },
        "general_subscription_plans": subscription_plans,
        "inputs": {
            "billing_file": str(BILLING_FILE),
            "system_cost_file": str(SYSTEM_COST_FILE),
        },
        "details": details,
    }

    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = []
    md.append("# 精確成本報告（本地系統 vs 一般訂閱）")
    md.append("")
    md.append(f"- 產生時間：`{payload['generated_at']}`")
    md.append(f"- 本地 Ollama 呼叫：`{local_total}`")
    md.append(f"- 雲端相關命中：`{cloud_total}`（Gemini=`{gemini_total}` / Claude=`{claude_total}`）")
    md.append("")
    md.append("## 1) 日誌證據下的節省估算（區間）")
    md.append(f"- 下限：`NT${est_saved_min}`")
    md.append(f"- 上限：`NT${est_saved_max}`")
    md.append("")
    md.append("## 2) 精確月成本比較（你填實際帳單後）")
    md.append(f"- 雲端實際月成本：`NT${cloud_actual_month}`")
    md.append(f"- 你系統月成本：`NT${system_month}`")
    md.append(f"- 差額（雲端-系統）：`NT${exact_delta}`")
    md.append(f"- 較省方案：`{exact_better}`")
    md.append("")
    md.append("## 3) 一般訂閱費用比較")
    for p in subscription_plans:
        md.append(
            f"- {p['name']}：`NT${p['monthly_ntd']}` / 月，與你系統差額：`NT${p['delta_vs_system_ntd']}`"
        )
    md.append("")
    md.append("## 4) 依據檔案")
    for d in details:
        md.append(
            f"- `{d['file']}` | local={d['local_ollama_calls']} gemini={d['gemini_related_hits']} claude={d['claude_related_hits']}"
        )
    md.append("")
    md.append("## 5) 要達到財務級精確")
    md.append(f"- 請填：`{BILLING_FILE}`（雲端實際帳單）")
    md.append(f"- 請填：`{SYSTEM_COST_FILE}`（你系統每月成本）")
    md.append("- 重新執行報表後，`exact_comparison_ntd_per_month` 即為可審計數字。")
    REPORT_MD.write_text("\n".join(md), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


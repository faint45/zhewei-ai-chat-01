# -*- coding: utf-8 -*-
"""
築未科技 Construction Brain
project_briefing.py

功能：
  上傳新案子的設計圖說/契約/監造計畫
  → AI 自動產生「工程簡介」（ProjectBriefing.md）
  → 讓新進人員快速了解：
      這個工程在做什麼？
      有哪些主要工項？
      施工重點/限制/風險？
      工期/里程碑？
      主要規範要求？

用法：
    python project_briefing.py --project_id PRJ-001 --file contract.pdf
    python project_briefing.py --project_id PRJ-001  # 從已有的 schedule.json 產生
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

import httpx

BASE_DIR = Path(os.environ.get("ZHEWEI_BASE", r"C:\ZheweiConstruction"))
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "zhewei-brain")
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "180"))

BRIEFING_SYSTEM_PROMPT = """你是「築未科技」的工程簡介撰寫引擎。

【任務】
根據提供的工程文件（契約/監造計畫/設計圖說/工項清單），
撰寫一份讓「新進工程師或工地人員」能在 10 分鐘內理解本工程的簡介。

【你必須輸出純 JSON，不得附加任何說明文字】格式如下：

{
  "project_name": "工程名稱",
  "project_type": "工程類型（橋梁/道路/管線/建築/水利/其他）",
  "one_line_summary": "一句話說明這個工程在做什麼（30字以內）",
  "overview": "工程概述（3-5句，說明工程目的、範圍、重要性）",
  "key_work_items": [
    {
      "name": "主要工項名稱",
      "description": "說明這個工項在做什麼、為什麼重要",
      "duration_hint": "大約工期或占總工期比例"
    }
  ],
  "construction_highlights": [
    "施工重點1（如：主橋段需封路施工）",
    "施工重點2"
  ],
  "key_risks": [
    {
      "risk": "風險描述",
      "mitigation": "對應措施"
    }
  ],
  "critical_specs": [
    "重要規範要求（如：混凝土強度fc=280kgf/cm²）",
    "規範要求2"
  ],
  "milestones": [
    {
      "name": "里程碑名稱（如：基礎完成）",
      "trigger": "完成條件（如：完成橋台基礎澆置）"
    }
  ],
  "newcomer_tips": [
    "新進人員注意事項1（如：本工程有交通維持需求，每日進場前確認管制）",
    "注意事項2"
  ],
  "glossary": [
    {
      "term": "專業術語",
      "explanation": "白話說明（讓新人理解）"
    }
  ]
}

【撰寫原則】
1. 語言：口語化的專業中文，避免過度技術性詞彙（但可加括號解釋）
2. 重點突出：key_risks 必填，這是新人最需要知道的
3. newcomer_tips：從工地主任角度寫，實用、具體
4. 要讓看完這份簡介的人，能夠馬上知道「這工程的特殊性在哪裡」
5. 禁止輸出 JSON 以外的任何文字"""


def _load_schedule_summary(project_id: str) -> str:
    """從已有的 schedule.json 取工項摘要作為輸入"""
    sched_path = BASE_DIR / "projects" / project_id / "02_Output" / "Schedule" / "schedule.json"
    if not sched_path.exists():
        return ""
    schedule = json.loads(sched_path.read_text(encoding="utf-8"))
    items = schedule.get("work_items", [])
    lines = [f"工程名稱：{schedule.get('project_name', project_id)}",
             f"工期：{schedule.get('contract_period_days', '未知')} 天",
             f"開工日：{schedule.get('start_date_hint', '未知')}",
             "主要工項清單："]
    for item in items[:30]:
        lines.append(
            f"  - {item['id']} {item['name']}（{item.get('duration_days', '?')} 天）"
            f"：{item.get('notes', '')}"
        )
    if schedule.get("critical_constraints"):
        lines.append("施工限制條件：")
        for c in schedule["critical_constraints"]:
            lines.append(f"  - {c}")
    return "\n".join(lines)


def _extract_text_from_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        try:
            import pdfplumber
            parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages[:20]:
                    t = page.extract_text()
                    if t:
                        parts.append(t)
            return "\n".join(parts)
        except ImportError:
            return ""
    elif suffix in (".docx", ".doc"):
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            return ""
    elif suffix in (".txt", ".md"):
        return file_path.read_text(encoding="utf-8", errors="ignore")
    return ""


def _call_ollama_briefing(input_text: str) -> dict:
    max_chars = 10000
    if len(input_text) > max_chars:
        input_text = input_text[:max_chars]

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": BRIEFING_SYSTEM_PROMPT},
            {"role": "user", "content": f"請根據以下工程資料產生工程簡介：\n\n{input_text}"},
        ],
        "stream": False,
        "options": {"temperature": 0.3, "num_ctx": 12288},
    }
    with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
        r = client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        r.raise_for_status()
        raw = r.json()["message"]["content"].strip()

    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        return json.loads(m.group(0))
    raise ValueError(f"無法解析 AI 回應：{raw[:300]}")


def _render_briefing_md(data: dict, project_id: str) -> str:
    lines = []
    project_name = data.get("project_name") or project_id
    project_type = data.get("project_type", "")

    lines.append(f"# 工程簡介：{project_name}")
    lines.append(f"> **類型**：{project_type}　｜　**產生時間**：{datetime.now().strftime('%Y-%m-%d %H:%M')}　｜　由「築未科技 Construction Brain」產生")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 一句話說明")
    lines.append("")
    lines.append(f"> [NOTE] **{data.get('one_line_summary', '')}**")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 工程概述")
    lines.append("")
    lines.append(data.get("overview", ""))
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 主要工項")
    lines.append("")
    for item in data.get("key_work_items", []):
        lines.append(f"### {item.get('name', '')}")
        lines.append(f"{item.get('description', '')}")
        if item.get("duration_hint"):
            lines.append(f"> ⏱ 工期參考：{item['duration_hint']}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 施工重點")
    lines.append("")
    for i, h in enumerate(data.get("construction_highlights", []), 1):
        lines.append(f"{i}. {h}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## [WARN] 主要風險與對策")
    lines.append("")
    risks = data.get("key_risks", [])
    if risks:
        lines.append("| 風險 | 對應措施 |")
        lines.append("|------|---------|")
        for r in risks:
            lines.append(f"| {r.get('risk', '')} | {r.get('mitigation', '')} |")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 重要規範要求")
    lines.append("")
    for spec in data.get("critical_specs", []):
        lines.append(f"- {spec}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 工程里程碑")
    lines.append("")
    milestones = data.get("milestones", [])
    if milestones:
        lines.append("| 里程碑 | 完成條件 |")
        lines.append("|-------|---------|")
        for m in milestones:
            lines.append(f"| {m.get('name', '')} | {m.get('trigger', '')} |")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## [NEW] 新進人員注意事項")
    lines.append("")
    for i, tip in enumerate(data.get("newcomer_tips", []), 1):
        lines.append(f"{i}. {tip}")
    lines.append("")

    glossary = data.get("glossary", [])
    if glossary:
        lines.append("---")
        lines.append("")
        lines.append("## 專業術語說明")
        lines.append("")
        lines.append("| 術語 | 說明 |")
        lines.append("|------|------|")
        for g in glossary:
            lines.append(f"| **{g.get('term', '')}** | {g.get('explanation', '')} |")
        lines.append("")

    return "\n".join(lines)


def generate_briefing(project_id: str, file_path: Path = None) -> Path:
    """
    產生工程簡介 ProjectBriefing.md

    Args:
        project_id: 專案代碼
        file_path: 可選，上傳的文件（優先用文件；無則用 schedule.json）

    Returns:
        輸出的 .md 路徑
    """
    print(f"\n{'='*55}")
    print(f"  築未科技 工程簡介產生器")
    print(f"  專案：{project_id}")
    print(f"{'='*55}\n")

    if file_path and Path(file_path).exists():
        print(f"[briefing] 讀取文件：{Path(file_path).name}")
        input_text = _extract_text_from_file(Path(file_path))
        if not input_text:
            print("[briefing] [WARN] 文件讀取失敗，改用 schedule.json")
            input_text = _load_schedule_summary(project_id)
    else:
        print("[briefing] 從 schedule.json 讀取工項清單")
        input_text = _load_schedule_summary(project_id)

    if not input_text:
        print("[briefing] [ERR] 無輸入資料，請先執行 schedule_extractor.py 或提供文件")
        return None

    print("[briefing] 呼叫 AI 產生簡介（可能需要 30-60 秒）...")
    try:
        data = _call_ollama_briefing(input_text)
    except Exception as e:
        print(f"[briefing] [ERR] AI 產生失敗：{e}")
        return None

    md_content = _render_briefing_md(data, project_id)

    out_dir = BASE_DIR / "projects" / project_id / "02_Output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "ProjectBriefing.md"
    out_path.write_text(md_content, encoding="utf-8")

    json_path = out_dir / "ProjectBriefing.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[briefing] [OK] ProjectBriefing.md → {out_path}")
    print(f"\n工程類型：{data.get('project_type', '')}")
    print(f"一句話摘要：{data.get('one_line_summary', '')}")
    print(f"主要工項數：{len(data.get('key_work_items', []))} 項")
    print(f"風險項目：{len(data.get('key_risks', []))} 項")

    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="築未科技 — 工程簡介自動產生")
    parser.add_argument("--project_id", required=True)
    parser.add_argument("--file", default=None, help="文件路徑（選填，無則從 schedule.json 讀取）")
    args = parser.parse_args()
    generate_briefing(args.project_id, Path(args.file) if args.file else None)

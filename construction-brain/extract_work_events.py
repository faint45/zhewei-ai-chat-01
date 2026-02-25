# -*- coding: utf-8 -*-
"""
築未科技 Construction Brain
extract_work_events.py

功能：接收語音逐字稿或文字訊息，呼叫本地 Ollama（zhewei-brain）
     抽取結構化工項 JSON，並寫入 work_events.json 與 SQLite 索引庫

用法：
    python extract_work_events.py --text "今天K12+300路床整平150公尺..."
    python extract_work_events.py --transcript transcripts/2026-02-24/xxx.txt
    python extract_work_events.py --message_id "abc123" --project_id "PRJ-001"
"""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import date, datetime
from pathlib import Path

import httpx

BASE_DIR = Path(os.environ.get("ZHEWEI_BASE", r"C:\ZheweiConstruction"))
DB_PATH = BASE_DIR / "db" / "index.db"

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "zhewei-brain")
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120"))

EXTRACT_SYSTEM_PROMPT = """你是「築未科技」的施工日誌填寫引擎。

接收來自LINE群組的文字訊息或語音逐字稿，從中抽取「公共工程施工日誌」所需的結構化欄位。

【輸入格式不拘】
- 語音轉寫（口語、台灣中文、台語夾雜均可）
- 打字訊息（簡短、條列、口語均可）

【你必須輸出純 JSON，不得附加任何說明文字】格式如下：
{
  "weather_am": "晴|陰|雨|其他|null",
  "weather_pm": "晴|陰|雨|其他|null",
  "work_items": [
    {
      "item": "施工項目名稱",
      "location": "工區/里程/層別",
      "unit": "公尺|m³|噸|式|個",
      "qty_today": null,
      "progress_pct": null,
      "notes": "備註"
    }
  ],
  "materials": [
    {
      "name": "材料名稱",
      "unit": "單位",
      "qty_today": null,
      "supplier": null,
      "notes": ""
    }
  ],
  "labor": [
    {"trade": "工別", "count_today": null}
  ],
  "equipment": [
    {"name": "機具名稱", "count_today": null}
  ],
  "safety_issues": [
    {"description": "缺失描述", "location": "位置/里程", "severity": "low|medium|high"}
  ],
  "problems": [],
  "plan_tomorrow": [],
  "notices": [],
  "important_notes": []
}

【抽取規則】
1. 不確定的欄位填 null，不要猜測
2. 數量一定要帶單位（「八十方」→ qty_today:80, unit:"m³"）
3. 台語/口語數字換算（「廿噸」→20，「半噸」→0.5）
4. 同一則訊息可能含多個工項，全部列出
5. 工安相關描述（未戴、未設、開口、高處未繫、無護欄）→ 一律寫入 safety_issues
6. severity 判斷：高處/電氣/倒塌=high，保護具=medium，環境整潔=low
7. 「明天要...」「明日...」→ plan_tomorrow
8. 「通知OO廠商...」「叫XX補...」→ notices
9. 天候停工 → problems 且 important_notes
10. 禁止輸出 JSON 以外任何文字"""


def _ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS work_events (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            date TEXT,
            source TEXT,
            source_ref TEXT,
            json_data TEXT,
            parse_status TEXT,
            raw_input TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def _call_ollama(text: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": f"請抽取以下工地訊息的結構化欄位：\n\n{text}"},
        ],
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 8192},
    }
    with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
        r = client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        return json.loads(m.group(0))
    raise ValueError(f"找不到 JSON 區塊：{raw[:200]}")


def _safe_extract(text: str, retry: int = 1) -> tuple[dict, str]:
    for attempt in range(retry + 1):
        try:
            raw = _call_ollama(text)
            data = _extract_json(raw)
            return data, "ok"
        except (json.JSONDecodeError, ValueError) as e:
            if attempt == retry:
                print(f"[WARN] JSON 解析失敗（{e}），存為 partial")
                return {"raw_parse_error": str(e)}, "failed"
    return {}, "failed"


def extract(
    text: str,
    project_id: str = "default",
    source: str = "manual",
    source_ref: str = "",
    event_date: str = "",
    output_dir: Path | None = None,
) -> dict:
    """
    主要入口：傳入文字/逐字稿，回傳結構化 work_event dict 並寫入 SQLite

    Args:
        text: 語音逐字稿或文字訊息
        project_id: 專案代碼
        source: 來源（line_voice/line_text/manual）
        source_ref: 來源 ID（訊息 ID 或 transcript 檔名）
        event_date: YYYY-MM-DD，空字串則用今天
        output_dir: 指定輸出目錄；None 則用 BASE_DIR/projects/<project_id>/02_Output/events/

    Returns:
        work_event dict（含 event_id、parse_status 等）
    """
    _ensure_db()

    event_date = event_date or date.today().isoformat()
    event_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    print(f"[extract] project={project_id} date={event_date} source={source}")
    data, parse_status = _safe_extract(text)

    event = {
        "event_id": event_id,
        "project_id": project_id,
        "date": event_date,
        "source": source,
        "source_ref": source_ref,
        "created_at": created_at,
        "parse_status": parse_status,
        "raw_input": text,
        **data,
    }

    if output_dir is None:
        output_dir = BASE_DIR / "projects" / project_id / "02_Output" / "events"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    out_file = output_dir / f"{event_date}_{event_id[:8]}_work_event.json"
    out_file.write_text(json.dumps(event, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[extract] 輸出 → {out_file}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT OR REPLACE INTO work_events
           (id, project_id, date, source, source_ref, json_data, parse_status, raw_input, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (event_id, project_id, event_date, source, source_ref,
         json.dumps(data, ensure_ascii=False), parse_status, text, created_at),
    )
    conn.commit()
    conn.close()

    status_icon = "[OK]" if parse_status == "ok" else "[WARN]"
    print(f"[extract] {status_icon} parse_status={parse_status}  event_id={event_id[:8]}")
    return event


def load_events_for_date(project_id: str, event_date: str) -> list[dict]:
    """從 SQLite 讀取指定專案/日期的所有 work_events"""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT json_data FROM work_events WHERE project_id=? AND date=? AND parse_status='ok'",
        (project_id, event_date),
    ).fetchall()
    conn.close()
    return [json.loads(r[0]) for r in rows]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="築未科技 — 工地訊息結構化抽取")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="直接輸入文字訊息")
    group.add_argument("--transcript", help="語音逐字稿檔案路徑")
    parser.add_argument("--project_id", default="test_project_001", help="專案代碼")
    parser.add_argument("--date", default="", help="日期 YYYY-MM-DD（空=今天）")
    parser.add_argument("--source", default="manual", help="來源標籤")
    args = parser.parse_args()

    if args.text:
        input_text = args.text
        source_ref = "cli_text"
    else:
        transcript_path = Path(args.transcript)
        input_text = transcript_path.read_text(encoding="utf-8")
        source_ref = transcript_path.name

    result = extract(
        text=input_text,
        project_id=args.project_id,
        source=args.source,
        source_ref=source_ref,
        event_date=args.date,
    )

    print("\n--- 抽取結果摘要 ---")
    print(f"工項數量：{len(result.get('work_items', []))}")
    print(f"材料筆數：{len(result.get('materials', []))}")
    print(f"工安缺失：{len(result.get('safety_issues', []))}")
    print(f"明日計畫：{len(result.get('plan_tomorrow', []))}")
    print(f"解析狀態：{result.get('parse_status')}")

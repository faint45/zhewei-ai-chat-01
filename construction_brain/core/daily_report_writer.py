# -*- coding: utf-8 -*-
"""
營建自動化大腦 — 施工日誌引擎
將事件抽取結果組裝為完整施工日報

複用：
  - construction_mgmt/database.py: create_daily_log, get_daily_log
  - construction_brain/core/extract_work_events.py: extract_events
"""
import json
import logging
import os
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger("construction_brain.daily_report")

DATA_DIR = Path(os.environ.get("CB_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data")))
REPORTS_DIR = DATA_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11460").rstrip("/")
OLLAMA_MODEL = os.environ.get("CB_LLM_MODEL", "qwen3:32b")


def _call_llm(prompt: str, system: str = "") -> str:
    import urllib.request
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 4000},
    }
    try:
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8")).get("response", "")
    except Exception as e:
        log.error(f"LLM 呼叫失敗: {e}")
        return ""


class DailyReportWriter:
    """
    施工日報撰寫引擎

    流程：
    1. 收集當日所有 IngestResult（語音+照片+文字）
    2. 合併事件到統一日誌結構
    3. LLM 生成正式日報文字
    4. 輸出 JSON + 可列印文字報告
    """

    def __init__(self, project_id: str = "", project_name: str = ""):
        self.project_id = project_id
        self.project_name = project_name
        self._events: list = []

    def add_events(self, events: dict):
        """加入事件抽取結果"""
        self._events.append(events)

    def add_from_ingest(self, ingest_result):
        """從 IngestResult 加入事件"""
        if hasattr(ingest_result, "events") and ingest_result.events:
            self._events.append(ingest_result.events)

    def merge_daily_log(self) -> dict:
        """合併多個事件結果到單一日誌結構"""
        today = date.today().isoformat()
        merged = {
            "log_date": today,
            "weather_am": "", "weather_pm": "",
            "temperature_high": None, "temperature_low": None,
            "day_status": "working",
            "work_description": "",
            "safety_notes": "", "quality_notes": "", "notes": "",
            "workers": [], "equipment": [], "materials": [], "work_items": [],
        }
        all_safety = []
        all_quality = []
        all_events = []
        descriptions = []

        for evt in self._events:
            dl = evt.get("daily_log", {})
            # 取第一個非空的天氣/狀態
            for key in ("weather_am", "weather_pm", "day_status"):
                if dl.get(key) and not merged[key]:
                    merged[key] = dl[key]
            for key in ("temperature_high", "temperature_low"):
                if dl.get(key) is not None and merged[key] is None:
                    merged[key] = dl[key]
            # 合併陣列
            merged["workers"].extend(dl.get("workers", []))
            merged["equipment"].extend(dl.get("equipment", []))
            merged["materials"].extend(dl.get("materials", []))
            merged["work_items"].extend(dl.get("work_items", []))
            # 文字
            desc = dl.get("work_description", "")
            if desc:
                descriptions.append(desc)
            for key in ("safety_notes", "quality_notes", "notes"):
                val = dl.get(key, "")
                if val:
                    merged[key] = (merged[key] + "；" + val).lstrip("；")
            # 獨立區塊
            all_safety.extend(evt.get("safety_alerts", []))
            all_quality.extend(evt.get("quality_checks", []))
            all_events.extend(evt.get("events", []))

        merged["work_description"] = "\n".join(descriptions)
        # 去重人力（同工種合併人數）
        merged["workers"] = self._dedup_workers(merged["workers"])

        return {
            "daily_log": merged,
            "safety_alerts": all_safety,
            "quality_checks": all_quality,
            "events": all_events,
        }

    def generate_report(self) -> dict:
        """
        生成完整日報

        Returns:
            {
                "merged": {...},         # 結構化資料
                "report_text": "...",    # 正式日報文字
                "safety_summary": "...", # 工安摘要
                "elapsed_ms": 0.0,
            }
        """
        t0 = time.perf_counter()
        merged = self.merge_daily_log()
        dl = merged["daily_log"]
        safety = merged["safety_alerts"]

        # LLM 生成正式日報
        system = f"""你是營建工程日報撰寫助理。工程名稱：{self.project_name}。
請根據結構化資料撰寫正式施工日報，格式符合台灣公共工程品質管理規範。
語氣正式、簡潔、專業。包含：施工概要、人力機具、材料進場、施工進度、品質管理、安全衛生。"""

        prompt = f"""結構化資料：
```json
{json.dumps(dl, ensure_ascii=False, indent=2)}
```

工安警報：
{json.dumps(safety, ensure_ascii=False) if safety else "無"}

請撰寫正式施工日報（純文字，含各分段標題）。"""

        report_text = _call_llm(prompt, system)

        # 工安摘要
        safety_summary = ""
        if safety:
            high = [s for s in safety if s.get("severity") == "high"]
            medium = [s for s in safety if s.get("severity") == "medium"]
            if high:
                safety_summary += f"🔴 高風險 {len(high)} 項：" + "；".join(s.get("risk", "") for s in high) + "\n"
            if medium:
                safety_summary += f"🟡 中風險 {len(medium)} 項：" + "；".join(s.get("risk", "") for s in medium)

        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        result = {
            "merged": merged,
            "report_text": report_text,
            "safety_summary": safety_summary.strip(),
            "elapsed_ms": elapsed,
        }

        # 儲存
        report_path = REPORTS_DIR / f"daily_{dl.get('log_date', date.today().isoformat())}_{self.project_id}.json"
        try:
            report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            log.info(f"日報已儲存: {report_path}")
        except Exception as e:
            log.error(f"日報儲存失敗: {e}")

        return result

    @staticmethod
    def _dedup_workers(workers: list) -> list:
        """去重人力：同工種合併人數"""
        by_trade = {}
        for w in workers:
            trade = w.get("trade", "")
            if not trade:
                continue
            if trade in by_trade:
                by_trade[trade]["count"] += w.get("count", 0)
            else:
                by_trade[trade] = {**w}
        return list(by_trade.values())

    def save_to_db(self, merged: dict = None) -> Optional[int]:
        """將日誌寫入 construction_mgmt 資料庫"""
        if merged is None:
            merged = self.merge_daily_log()
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
            from construction_mgmt.database import create_daily_log
            project_id = int(self.project_id) if self.project_id.isdigit() else 1
            log_id = create_daily_log(project_id, merged["daily_log"])
            log.info(f"日誌已寫入 DB: project={project_id}, log_id={log_id}")
            return log_id
        except Exception as e:
            log.error(f"DB 寫入失敗: {e}")
            return None

# -*- coding: utf-8 -*-
"""
營建自動化大腦 — 進度管理引擎
追蹤工項進度、計算落後/超前、產出進度摘要

複用：
  - construction_mgmt/database.py: schedule_tasks, scurve_data
"""
import json
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger("construction_brain.schedule")

DATA_DIR = Path(os.environ.get("CB_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data")))
SCHEDULE_DIR = DATA_DIR / "schedule"
SCHEDULE_DIR.mkdir(parents=True, exist_ok=True)


class ScheduleEngine:
    """
    進度管理引擎

    功能：
    1. 匯入排程（CSV/JSON/DB）
    2. 從日報自動更新工項進度
    3. 計算進度差異（落後/超前天數）
    4. 產出進度摘要文字
    """

    def __init__(self, project_id: str = "", project_name: str = ""):
        self.project_id = project_id
        self.project_name = project_name
        self._tasks: list = []

    def load_tasks_from_db(self) -> int:
        """從 construction_mgmt DB 載入排程任務"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
            from construction_mgmt.database import list_schedule_tasks
            pid = int(self.project_id) if self.project_id.isdigit() else 1
            self._tasks = list_schedule_tasks(pid)
            log.info(f"載入 {len(self._tasks)} 個排程任務")
            return len(self._tasks)
        except Exception as e:
            log.error(f"載入排程失敗: {e}")
            return 0

    def load_tasks_from_json(self, json_path: str) -> int:
        """從 JSON 檔載入排程"""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                self._tasks = json.load(f)
            return len(self._tasks)
        except Exception as e:
            log.error(f"JSON 載入失敗: {e}")
            return 0

    def update_progress(self, item_name: str, progress_pct: float, actual_date: str = ""):
        """更新工項進度"""
        for task in self._tasks:
            if task.get("item_name", "") == item_name or task.get("task_name", "") == item_name:
                task["actual_progress"] = progress_pct
                task["actual_date"] = actual_date or date.today().isoformat()
                log.info(f"進度更新: {item_name} → {progress_pct}%")
                return True
        log.warning(f"工項未找到: {item_name}")
        return False

    def update_from_daily_log(self, daily_log: dict):
        """從日報的 work_items 自動更新進度"""
        work_items = daily_log.get("work_items", [])
        updated = 0
        for item in work_items:
            name = item.get("item_name", "")
            pct = item.get("progress_pct", 0)
            if name and pct > 0:
                if self.update_progress(name, pct):
                    updated += 1
        return updated

    def calculate_variance(self) -> list:
        """
        計算進度差異

        Returns: [{"task": str, "planned": float, "actual": float, "variance": float, "status": str}]
        """
        today = date.today()
        result = []
        for task in self._tasks:
            planned = task.get("planned_progress", 0)
            actual = task.get("actual_progress", 0)
            variance = actual - planned
            status = "on_track" if abs(variance) < 5 else ("ahead" if variance > 0 else "behind")
            result.append({
                "task": task.get("item_name") or task.get("task_name", ""),
                "planned": planned,
                "actual": actual,
                "variance": round(variance, 1),
                "status": status,
            })
        return result

    def generate_summary(self) -> str:
        """產出進度摘要"""
        variance = self.calculate_variance()
        if not variance:
            return "尚無排程資料。"

        behind = [v for v in variance if v["status"] == "behind"]
        ahead = [v for v in variance if v["status"] == "ahead"]
        on_track = [v for v in variance if v["status"] == "on_track"]

        lines = [f"進度摘要（{date.today().isoformat()}）"]
        lines.append(f"工程：{self.project_name}")
        lines.append(f"總工項：{len(variance)} | 正常：{len(on_track)} | 超前：{len(ahead)} | 落後：{len(behind)}")
        lines.append("")

        if behind:
            lines.append("⚠️ 落後工項：")
            for v in sorted(behind, key=lambda x: x["variance"]):
                lines.append(f"  - {v['task']}: 計畫 {v['planned']}% / 實際 {v['actual']}% (落後 {abs(v['variance'])}%)")

        if ahead:
            lines.append("✅ 超前工項：")
            for v in sorted(ahead, key=lambda x: -x["variance"])[:5]:
                lines.append(f"  - {v['task']}: 超前 {v['variance']}%")

        return "\n".join(lines)

    def get_tasks(self) -> list:
        return self._tasks

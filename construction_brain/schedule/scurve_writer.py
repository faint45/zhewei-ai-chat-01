# -*- coding: utf-8 -*-
"""
營建自動化大腦 — S-Curve 產出引擎
從排程資料計算計畫/實際累積進度，輸出 S-Curve 數據與圖表

複用：
  - construction_mgmt/database.py: get_scurve_data, update_scurve_actual
"""
import json
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger("construction_brain.scurve")

DATA_DIR = Path(os.environ.get("CB_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data")))


class SCurveWriter:
    """
    S-Curve 產出引擎

    功能：
    1. 從排程任務計算累積計畫進度
    2. 從日報實際進度更新累積實際進度
    3. 輸出 S-Curve JSON 數據（日期 vs 計畫% vs 實際%）
    4. 可選：matplotlib 圖表輸出
    """

    def __init__(self, project_id: str = "", project_name: str = ""):
        self.project_id = project_id
        self.project_name = project_name
        self._data: list = []  # [{"date": str, "planned": float, "actual": float}]

    def load_from_db(self) -> int:
        """從 construction_mgmt DB 載入 S-Curve 資料"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
            from construction_mgmt.database import get_scurve_data
            pid = int(self.project_id) if self.project_id.isdigit() else 1
            self._data = get_scurve_data(pid)
            return len(self._data)
        except Exception as e:
            log.error(f"S-Curve DB 載入失敗: {e}")
            return 0

    def load_from_json(self, json_path: str) -> int:
        """從 JSON 檔載入"""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            return len(self._data)
        except Exception as e:
            log.error(f"JSON 載入失敗: {e}")
            return 0

    def update_actual(self, log_date: str, actual_pct: float):
        """更新某日實際進度"""
        for d in self._data:
            if d.get("date") == log_date:
                d["actual"] = actual_pct
                return
        self._data.append({"date": log_date, "planned": 0, "actual": actual_pct})
        self._data.sort(key=lambda x: x.get("date", ""))

    def get_data(self) -> list:
        """取得 S-Curve 數據"""
        return self._data

    def get_latest_variance(self) -> dict:
        """取得最新進度差異"""
        if not self._data:
            return {"date": "", "planned": 0, "actual": 0, "variance": 0}
        latest = self._data[-1]
        planned = latest.get("planned", 0)
        actual = latest.get("actual", 0)
        return {
            "date": latest.get("date", ""),
            "planned": planned,
            "actual": actual,
            "variance": round(actual - planned, 1),
        }

    def export_json(self, output_path: str = "") -> str:
        """匯出 S-Curve JSON"""
        if not output_path:
            output_path = str(DATA_DIR / "schedule" / f"scurve_{self.project_id}.json")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "project_id": self.project_id,
                "project_name": self.project_name,
                "exported_at": datetime.now().isoformat(),
                "data": self._data,
            }, f, ensure_ascii=False, indent=2)
        return output_path

    def render_chart(self, output_path: str = "") -> Optional[str]:
        """
        matplotlib 圖表輸出（可選，若未安裝 matplotlib 則跳過）

        Returns: 圖片路徑或 None
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
        except ImportError:
            log.warning("matplotlib 未安裝，無法產出 S-Curve 圖表")
            return None

        if not self._data:
            return None

        dates = [d.get("date", "") for d in self._data]
        planned = [d.get("planned", 0) for d in self._data]
        actual = [d.get("actual", 0) for d in self._data]

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(dates, planned, "b-o", label="計畫進度", markersize=3)
        ax.plot(dates, actual, "r-s", label="實際進度", markersize=3)
        ax.fill_between(dates, planned, actual, alpha=0.15, color="red")
        ax.set_xlabel("日期")
        ax.set_ylabel("累積進度 (%)")
        ax.set_title(f"S-Curve — {self.project_name}")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 105)

        # 旋轉 x 軸日期
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        if not output_path:
            output_path = str(DATA_DIR / "schedule" / f"scurve_{self.project_id}.png")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150)
        plt.close(fig)
        log.info(f"S-Curve 圖表已輸出: {output_path}")
        return output_path

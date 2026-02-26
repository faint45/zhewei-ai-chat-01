# -*- coding: utf-8 -*-
"""
築未科技 AI 用量警報系統
當成本超過閾值時發送警報
"""
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

USAGE_DIR = Path("brain_workspace/usage")
ALERTS_DIR = USAGE_DIR / "alerts"
ALERTS_DIR.mkdir(parents=True, exist_ok=True)

# 警報閾值配置 (USD/天)
DEFAULT_THRESHOLDS = {
    "deepseek": 5.0,
    "minimax": 2.0,
    "gemini": 1.0,
    "claude": 10.0,
    "total": 15.0
}


class UsageAlerts:
    """用量警報管理器"""

    def __init__(self, thresholds: Dict = None):
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.alert_log = ALERTS_DIR / "alert_log.jsonl"
        self.config_file = ALERTS_DIR / "thresholds.json"

    def load_thresholds(self) -> Dict:
        """載入自定義閾值"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return self.thresholds

    def save_thresholds(self, thresholds: Dict):
        """儲存自定義閾值"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(thresholds, f, ensure_ascii=False, indent=2)

    def check_usage(self, stats: Dict) -> list:
        """檢查用量是否超過閾值"""
        alerts = []
        thresholds = self.load_thresholds()
        providers = stats.get("providers", {})

        # 檢查各提供者
        for provider, data in providers.items():
            provider_key = provider.lower()
            if provider_key in thresholds:
                cost = data.get("cost", 0)
                if cost >= thresholds[provider_key]:
                    alerts.append({
                        "type": "provider",
                        "provider": provider,
                        "cost": cost,
                        "threshold": thresholds[provider_key],
                        "message": f"{provider} 今日成本 ${cost:.2f} 已超過閾值 ${thresholds[provider_key]:.2f}"
                    })

        # 檢查總成本
        total_cost = stats.get("total_cost", 0)
        if "total" in thresholds and total_cost >= thresholds["total"]:
            alerts.append({
                "type": "total",
                "cost": total_cost,
                "threshold": thresholds["total"],
                "message": f"總成本 ${total_cost:.2f} 已超過閾值 ${thresholds['total']:.2f}"
            })

        # 記錄警報
        if alerts:
            self._log_alerts(alerts)

        return alerts

    def _log_alerts(self, alerts: list):
        """記錄警報"""
        with open(self.alert_log, 'a', encoding='utf-8') as f:
            for alert in alerts:
                record = {
                    "timestamp": datetime.now().isoformat(),
                    **alert
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def get_recent_alerts(self, hours: int = 24) -> list:
        """取得最近警報"""
        alerts = []
        cutoff = datetime.now() - timedelta(hours=hours)
        
        if self.alert_log.exists():
            with open(self.alert_log, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        alert_time = datetime.fromisoformat(record.get("timestamp", ""))
                        if alert_time >= cutoff:
                            alerts.append(record)
        
        return alerts[-20:]  # 最多返回 20 條

    def set_threshold(self, provider: str, value: float):
        """設定閾值"""
        thresholds = self.load_thresholds()
        thresholds[provider.lower()] = value
        self.save_thresholds(thresholds)

    def get_usage_report(self) -> str:
        """產生用量報告"""
        try:
            from ai_usage_tracker import usage_tracker
            stats = usage_tracker.get_today_stats()
            alerts = self.check_usage(stats)
            
            report = f"""
=== AI 用量報告 - {stats.get('date', 'N/A')} ===

總成本: ${stats.get('total_cost', 0):.4f}
總請求數: {stats.get('total_requests', 0)}

各提供者詳情:
"""
            for provider, data in stats.get("providers", {}).items():
                report += f"  {provider}: ${data.get('cost', 0):.4f} ({data.get('requests', 0)} 請求)\n"

            report += "\n警報狀態: "
            if alerts:
                report += f"⚠️ {len(alerts)} 項警報"
                for a in alerts:
                    report += f"\n  - {a['message']}"
            else:
                report += "✅ 正常"

            return report
        except ImportError:
            return "用量追蹤模組未安裝"


# 全域警報實例
alerts_manager = UsageAlerts()


def check_and_alert():
    """檢查並發送警報"""
    try:
        from ai_usage_tracker import usage_tracker
        stats = usage_tracker.get_today_stats()
        alerts = alerts_manager.check_usage(stats)
        return alerts
    except ImportError:
        return []


if __name__ == "__main__":
    # 測試
    print("=== 用量警報系統測試 ===")
    print()
    
    # 設定閾值
    alerts_manager.set_threshold("deepseek", 0.01)  # 設低一點方便測試
    print("閾值設定完成")
    
    # 檢查
    alerts = check_and_alert()
    if alerts:
        print("警報數量:", len(alerts))
        for a in alerts:
            print(" -", a["message"])
    else:
        print("無警報")
    
    # 報告
    print()
    print(alerts_manager.get_usage_report())

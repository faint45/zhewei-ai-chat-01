"""
Asset Commander - GPU 挖礦與 HDD 儲存收益管理系統
自動管理多平台 GPU 挖礦與 HDD 儲存收益，支援收益比較與自動切換
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import aiohttp
import psutil

DATA_DIR = os.path.join(os.path.dirname(__file__), "brain_workspace", "asset_data")
os.makedirs(DATA_DIR, exist_ok=True)

STATE_FILE = os.path.join(DATA_DIR, "state.json")
EARNINGS_FILE = os.path.join(DATA_DIR, "earnings.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

DEFAULT_CONFIG = {
    "electricity_rate": 4.0,  # NT$/kWh
    "min_profit_threshold": 0.5,  # 最低淨利門檻 (NT$/day)
    "check_interval": 300,  # 5 分鐘檢查一次
    "switch_interval": 900,  # 15 分鐘比較平台
    "discord_webhook": "",
    "platforms": {
        "io_net": {
            "enabled": True,
            "api_key": "",
            "worker_id": "",
            "earnings_per_gpu_hour": 0.0
        },
        "render": {
            "enabled": True,
            "api_key": "",
            "node_id": "",
            "earnings_per_gpu_hour": 0.0
        },
        "salad": {
            "enabled": True,
            "api_token": "",
            "earnings_per_gpu_hour": 0.0
        },
        "storj": {
            "enabled": True,
            "api_key": "",
            "bucket": "",
            "storage_gb": 0,
            "earnings_per_gb_month": 0.0
        }
    },
    "gpu": {
        "name": "RTX 4060 Ti",
        "watts": 160,
        "count": 1
    }
}


@dataclass
class PlatformStatus:
    name: str
    enabled: bool
    earnings: float = 0.0  # 每小時收入
    cost: float = 0.0  # 每小時成本
    profit: float = 0.0  # 每小時淨利
    status: str = "unknown"  # online, offline, error
    last_update: str = ""
    error: str = ""


@dataclass
class SystemState:
    running: bool = False
    current_platform: str = "none"
    total_earnings_day: float = 0.0
    total_cost_day: float = 0.0
    net_profit_day: float = 0.0
    gpu_utilization: float = 0.0
    gpu_power_watts: float = 0.0
    platforms: Dict[str, PlatformStatus] = field(default_factory=dict)
    last_switch: str = ""
    last_check: str = ""
    uptime_hours: float = 0.0
    start_time: str = ""


class AssetCommander:
    def __init__(self):
        self.config = self._load_config()
        self.state = self._load_state()
        self.earnings_history = self._load_earnings()
        self._init_platforms()
        
    def _load_config(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return DEFAULT_CONFIG.copy()
    
    def _save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def _load_state(self) -> SystemState:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    state = SystemState()
                    state.running = data.get("running", False)
                    state.current_platform = data.get("current_platform", "none")
                    state.total_earnings_day = data.get("total_earnings_day", 0.0)
                    state.total_cost_day = data.get("total_cost_day", 0.0)
                    state.net_profit_day = data.get("net_profit_day", 0.0)
                    state.gpu_utilization = data.get("gpu_utilization", 0.0)
                    state.gpu_power_watts = data.get("gpu_power_watts", 0.0)
                    state.last_switch = data.get("last_switch", "")
                    state.last_check = data.get("last_check", "")
                    state.uptime_hours = data.get("uptime_hours", 0.0)
                    state.start_time = data.get("start_time", "")
                    
                    platforms = data.get("platforms", {})
                    for name, pdata in platforms.items():
                        state.platforms[name] = PlatformStatus(
                            name=name,
                            enabled=pdata.get("enabled", True),
                            earnings=pdata.get("earnings", 0.0),
                            cost=pdata.get("cost", 0.0),
                            profit=pdata.get("profit", 0.0),
                            status=pdata.get("status", "unknown"),
                            last_update=pdata.get("last_update", ""),
                            error=pdata.get("error", "")
                        )
                    return state
            except:
                pass
        return SystemState()
    
    def _save_state(self):
        data = {
            "running": self.state.running,
            "current_platform": self.state.current_platform,
            "total_earnings_day": self.state.total_earnings_day,
            "total_cost_day": self.state.total_cost_day,
            "net_profit_day": self.state.net_profit_day,
            "gpu_utilization": self.state.gpu_utilization,
            "gpu_power_watts": self.state.gpu_power_watts,
            "platforms": {
                name: {
                    "enabled": p.enabled,
                    "earnings": p.earnings,
                    "cost": p.cost,
                    "profit": p.profit,
                    "status": p.status,
                    "last_update": p.last_update,
                    "error": p.error
                }
                for name, p in self.state.platforms.items()
            },
            "last_switch": self.state.last_switch,
            "last_check": self.state.last_check,
            "uptime_hours": self.state.uptime_hours,
            "start_time": self.state.start_time
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _load_earnings(self) -> List[dict]:
        if os.path.exists(EARNINGS_FILE):
            try:
                with open(EARNINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _save_earnings(self):
        with open(EARNINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.earnings_history, f, indent=2, ensure_ascii=False)
    
    def _init_platforms(self):
        for name in ["io_net", "render", "salad", "storj"]:
            if name not in self.state.platforms:
                self.state.platforms[name] = PlatformStatus(
                    name=name,
                    enabled=self.config["platforms"].get(name, {}).get("enabled", True)
                )
    
    def get_gpu_power_cost(self) -> float:
        """計算 GPU 每小時用電成本 (NT$)"""
        watts = self.config["gpu"]["watts"]
        rate = self.config["electricity_rate"]
        return (watts / 1000) * rate
    
    def get_gpu_info(self) -> dict:
        """取得 GPU 資訊"""
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,power.draw,memory.used,memory.total,utilization.gpu", 
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                gpus = []
                for line in lines:
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 5:
                        gpus.append({
                            "name": parts[0],
                            "power_watts": float(parts[1]) if parts[1] else 0,
                            "memory_used_mb": float(parts[2]) if parts[2] else 0,
                            "memory_total_mb": float(parts[3]) if parts[3] else 0,
                            "utilization": float(parts[4]) if parts[4] else 0
                        })
                return {"gpus": gpus, "available": True}
        except:
            pass
        return {"gpus": [], "available": False}
    
    async def fetch_io_net_earnings(self) -> PlatformStatus:
        """取得 IO.net 收益"""
        platform = self.state.platforms["io_net"]
        cfg = self.config["platforms"]["io_net"]
        
        if not cfg.get("enabled") or not cfg.get("api_key"):
            platform.status = "disabled"
            return platform
        
        try:
            # 模擬 API 調用 (實際需要根據 IO.net API 文件調整)
            # 這裡使用配置中的預設收益
            hourly_earnings = cfg.get("earnings_per_gpu_hour", 0.0)
            cost = self.get_gpu_power_cost()
            
            platform.earnings = hourly_earnings
            platform.cost = cost
            platform.profit = hourly_earnings - cost
            platform.status = "online"
            platform.last_update = datetime.now().isoformat()
            platform.error = ""
        except Exception as e:
            platform.status = "error"
            platform.error = str(e)
        
        return platform
    
    async def fetch_render_earnings(self) -> PlatformStatus:
        """取得 Render 收益"""
        platform = self.state.platforms["render"]
        cfg = self.config["platforms"]["render"]
        
        if not cfg.get("enabled") or not cfg.get("api_key"):
            platform.status = "disabled"
            return platform
        
        try:
            hourly_earnings = cfg.get("earnings_per_gpu_hour", 0.0)
            cost = self.get_gpu_power_cost()
            
            platform.earnings = hourly_earnings
            platform.cost = cost
            platform.profit = hourly_earnings - cost
            platform.status = "online"
            platform.last_update = datetime.now().isoformat()
            platform.error = ""
        except Exception as e:
            platform.status = "error"
            platform.error = str(e)
        
        return platform
    
    async def fetch_salad_earnings(self) -> PlatformStatus:
        """取得 Salad.com 收益"""
        platform = self.state.platforms["salad"]
        cfg = self.config["platforms"]["salad"]
        
        if not cfg.get("enabled") or not cfg.get("api_token"):
            platform.status = "disabled"
            return platform
        
        try:
            hourly_earnings = cfg.get("earnings_per_gpu_hour", 0.0)
            cost = self.get_gpu_power_cost()
            
            platform.earnings = hourly_earnings
            platform.cost = cost
            platform.profit = hourly_earnings - cost
            platform.status = "online"
            platform.last_update = datetime.now().isoformat()
            platform.error = ""
        except Exception as e:
            platform.status = "error"
            platform.error = str(e)
        
        return platform
    
    async def fetch_storj_earnings(self) -> PlatformStatus:
        """取得 Storj HDD 儲存收益"""
        platform = self.state.platforms["storj"]
        cfg = self.config["platforms"]["storj"]
        
        if not cfg.get("enabled"):
            platform.status = "disabled"
            return platform
        
        try:
            storage_gb = cfg.get("storage_gb", 0)
            rate_per_gb = cfg.get("earnings_per_gb_month", 0.0)
            
            # 月收益轉換為小時收益
            hourly_earnings = (storage_gb * rate_per_gb) / 720
            # HDD 功耗約 10W
            cost = (10 / 1000) * self.config["electricity_rate"]
            
            platform.earnings = hourly_earnings
            platform.cost = cost
            platform.profit = hourly_earnings - cost
            platform.status = "online"
            platform.last_update = datetime.now().isoformat()
            platform.error = ""
        except Exception as e:
            platform.status = "error"
            platform.error = str(e)
        
        return platform
    
    async def update_all_platforms(self):
        """更新所有平台收益"""
        await asyncio.gather(
            self.fetch_io_net_earnings(),
            self.fetch_render_earnings(),
            self.fetch_salad_earnings(),
            self.fetch_storj_earnings()
        )
        
        # 更新 GPU 資訊
        gpu_info = self.get_gpu_info()
        if gpu_info["available"]:
            self.state.gpu_utilization = gpu_info["gpus"][0]["utilization"] if gpu_info["gpus"] else 0
            self.state.gpu_power_watts = gpu_info["gpus"][0]["power_watts"] if gpu_info["gpus"] else 0
        else:
            self.state.gpu_power_watts = self.config["gpu"]["watts"]
        
        # 計算每日總收益
        total_hourly = sum(p.profit for p in self.state.platforms.values() if p.status == "online")
        self.state.total_earnings_day = total_hourly * 24
        self.state.total_cost_day = self.get_gpu_power_cost() * 24
        self.state.net_profit_day = self.state.total_earnings_day - self.state.total_cost_day
        
        self.state.last_check = datetime.now().isoformat()
        self._save_state()
    
    def get_best_platform(self) -> Optional[str]:
        """取得最佳收益平台"""
        best = None
        best_profit = float("-inf")
        
        for name, platform in self.state.platforms.items():
            if platform.status == "online" and platform.profit > best_profit:
                best_profit = platform.profit
                best = name
        
        return best
    
    def should_pause(self) -> bool:
        """檢查是否應該暫停 (淨利低於門檻)"""
        return self.state.net_profit_day < self.config["min_profit_threshold"]
    
    async def switch_to_platform(self, platform_name: str):
        """切換到指定平台"""
        if platform_name not in self.state.platforms:
            return False
        
        self.state.current_platform = platform_name
        self.state.last_switch = datetime.now().isoformat()
        self._save_state()
        return True
    
    def record_earnings(self):
        """記錄當前收益到歷史"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "platform": self.state.current_platform,
            "earnings": self.state.total_earnings_day,
            "cost": self.state.total_cost_day,
            "net_profit": self.state.net_profit_day,
            "gpu_power": self.state.gpu_power_watts
        }
        self.earnings_history.append(record)
        
        # 只保留 30 天資料
        cutoff = datetime.now() - timedelta(days=30)
        self.earnings_history = [
            r for r in self.earnings_history 
            if datetime.fromisoformat(r["timestamp"]) > cutoff
        ]
        self._save_earnings()
    
    def get_daily_report(self) -> dict:
        """取得每日報告"""
        if not self.earnings_history:
            return {"error": "無歷史資料"}
        
        today = datetime.now().date()
        today_records = [
            r for r in self.earnings_history 
            if datetime.fromisoformat(r["timestamp"]).date() == today
        ]
        
        if today_records:
            total_earnings = sum(r["earnings"] for r in today_records)
            total_cost = sum(r["cost"] for r in today_records)
            avg_profit = sum(r["net_profit"] for r in today_records) / len(today_records)
        else:
            total_earnings = self.state.total_earnings_day
            total_cost = self.state.total_cost_day
            avg_profit = self.state.net_profit_day
        
        return {
            "date": today.isoformat(),
            "total_earnings": round(total_earnings, 2),
            "total_cost": round(total_cost, 2),
            "net_profit": round(avg_profit, 2),
            "current_platform": self.state.current_platform,
            "gpu_power_watts": self.state.gpu_power_watts,
            "should_pause": self.should_pause(),
            "best_platform": self.get_best_platform()
        }
    
    def get_state(self) -> dict:
        """取得系統狀態"""
        return {
            "running": self.state.running,
            "current_platform": self.state.current_platform,
            "total_earnings_day": round(self.state.total_earnings_day, 2),
            "total_cost_day": round(self.state.total_cost_day, 2),
            "net_profit_day": round(self.state.net_profit_day, 2),
            "gpu_utilization": round(self.state.gpu_utilization, 1),
            "gpu_power_watts": round(self.state.gpu_power_watts, 1),
            "platforms": {
                name: {
                    "enabled": p.enabled,
                    "earnings": round(p.earnings, 4),
                    "cost": round(p.cost, 4),
                    "profit": round(p.profit, 4),
                    "status": p.status,
                    "last_update": p.last_update
                }
                for name, p in self.state.platforms.items()
            },
            "last_switch": self.state.last_switch,
            "last_check": self.state.last_check,
            "uptime_hours": round(self.state.uptime_hours, 1),
            "should_pause": self.should_pause(),
            "best_platform": self.get_best_platform()
        }
    
    def get_config(self) -> dict:
        """取得配置 (隱藏敏感資訊)"""
        config = self.config.copy()
        for platform in config["platforms"].values():
            if "api_key" in platform:
                platform["api_key"] = "***" if platform.get("api_key") else ""
            if "api_token" in platform:
                platform["api_token"] = "***" if platform.get("api_token") else ""
        return config
    
    def update_config(self, new_config: dict):
        """更新配置"""
        if "electricity_rate" in new_config:
            self.config["electricity_rate"] = float(new_config["electricity_rate"])
        if "min_profit_threshold" in new_config:
            self.config["min_profit_threshold"] = float(new_config["min_profit_threshold"])
        if "platforms" in new_config:
            for name, pconfig in new_config["platforms"].items():
                if name in self.config["platforms"]:
                    self.config["platforms"][name].update(pconfig)
        self._save_config()
    
    def start(self):
        """啟動系統"""
        self.state.running = True
        self.state.start_time = datetime.now().isoformat()
        self._save_state()
    
    def stop(self):
        """停止系統"""
        self.state.running = False
        self._save_state()


# 全域實例
_commander: Optional[AssetCommander] = None

def get_commander() -> AssetCommander:
    global _commander
    if _commander is None:
        _commander = AssetCommander()
    return _commander

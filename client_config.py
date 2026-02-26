# -*- coding: utf-8 -*-
"""
築未科技 — 客戶端配置模組
──────────────────────────
商用客戶端核心配置：
- 本地/遠端自動切換
- 離線偵測 + 自動降級
- 用量追蹤（遠端呼叫次數）
- 知識庫同步狀態管理
- 整合 license_manager 功能權限
"""

import json
import os
import time
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── 設定 ──
ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "brain_workspace" / "client"
CONFIG_FILE = CONFIG_DIR / "config.json"
USAGE_FILE = CONFIG_DIR / "usage.json"
SYNC_STATE_FILE = CONFIG_DIR / "sync_state.json"

# 遠端伺服器
DEFAULT_REMOTE_URL = os.environ.get("JARVIS_REMOTE_URL", "https://brain.zhe-wei.net")
REMOTE_TIMEOUT = int(os.environ.get("JARVIS_REMOTE_TIMEOUT", "10"))

# ── 預設配置 ──
DEFAULT_CONFIG = {
    "version": 1,
    "mode": "auto",  # auto / local_only / remote_only
    "remote_url": DEFAULT_REMOTE_URL,
    "remote_timeout": REMOTE_TIMEOUT,
    "local_ollama_url": "http://localhost:11434",
    "local_ollama_model": "qwen3:32b",
    "local_coder_model": "qwen3:32b",
    "local_embed_model": "nomic-embed-text:latest",
    "local_vision_model": "moondream",
    "chromadb_path": str(ROOT / "Jarvis_Training" / "chroma_db"),
    "auto_sync_kb": True,
    "sync_interval_hours": 24,
    "telemetry_enabled": True,  # 匿名用量統計
    "ui_language": "zh-TW",
}


# =====================================================================
# 配置管理
# =====================================================================

class ClientConfig:
    """客戶端配置管理器"""

    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._config = self._load_config()
        self._online_status: Optional[bool] = None
        self._online_checked_at: float = 0
        self._ollama_status: Optional[bool] = None
        self._ollama_checked_at: float = 0

    def _load_config(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                # 合併預設值（新版本可能有新欄位）
                merged = {**DEFAULT_CONFIG, **saved}
                return merged
            except Exception:
                pass
        return dict(DEFAULT_CONFIG)

    def save(self):
        CONFIG_FILE.write_text(
            json.dumps(self._config, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def get(self, key: str, default=None):
        return self._config.get(key, default)

    def set(self, key: str, value):
        self._config[key] = value
        self.save()

    def to_dict(self) -> dict:
        return dict(self._config)

    # ── 連線狀態偵測 ──

    def is_online(self, force_check: bool = False) -> bool:
        """檢查是否可連線到遠端伺服器（30 秒快取）"""
        if not force_check and self._online_status is not None:
            if time.time() - self._online_checked_at < 30:
                return self._online_status

        remote_url = self._config.get("remote_url", DEFAULT_REMOTE_URL)
        timeout = self._config.get("remote_timeout", REMOTE_TIMEOUT)

        try:
            import httpx
            r = httpx.get(f"{remote_url}/health", timeout=timeout)
            self._online_status = r.status_code == 200
        except Exception:
            self._online_status = False

        self._online_checked_at = time.time()
        return self._online_status

    def is_ollama_available(self, force_check: bool = False) -> bool:
        """檢查本地 Ollama 是否可用（30 秒快取）"""
        if not force_check and self._ollama_status is not None:
            if time.time() - self._ollama_checked_at < 30:
                return self._ollama_status

        ollama_url = self._config.get("local_ollama_url", "http://localhost:11434")
        urls_to_try = [ollama_url]
        if "11434" in ollama_url:
            urls_to_try.append(ollama_url.replace("11434", "11460"))
        elif "11460" in ollama_url:
            urls_to_try.append(ollama_url.replace("11460", "11434"))

        for url in urls_to_try:
            try:
                import httpx
                r = httpx.get(f"{url.rstrip('/')}/api/tags", timeout=3)
                if r.status_code == 200:
                    self._ollama_status = True
                    # 更新配置中的 URL
                    if url != self._config.get("local_ollama_url"):
                        self._config["local_ollama_url"] = url.rstrip("/")
                        self.save()
                    self._ollama_checked_at = time.time()
                    return True
            except Exception:
                continue

        self._ollama_status = False
        self._ollama_checked_at = time.time()
        return False

    # ── 智慧路由決策 ──

    def resolve_provider(self, task_type: str = "general") -> dict:
        """
        根據當前狀態決定使用哪個 AI 提供者

        task_type: general / code / vision / think / execute
        
        Returns:
            {
                "provider": "ollama" | "remote" | "fallback",
                "url": "...",
                "model": "...",
                "reason": "...",
                "is_local": True/False,
            }
        """
        mode = self._config.get("mode", "auto")
        ollama_available = self.is_ollama_available()
        online = self.is_online() if mode != "local_only" else False

        # 強制本地模式
        if mode == "local_only":
            if ollama_available:
                model = self._pick_local_model(task_type)
                return {
                    "provider": "ollama",
                    "url": self._config.get("local_ollama_url"),
                    "model": model,
                    "reason": "本地模式（離線可用）",
                    "is_local": True,
                }
            return {
                "provider": "none",
                "url": "",
                "model": "",
                "reason": "本地模式但 Ollama 不可用",
                "is_local": True,
            }

        # 強制遠端模式
        if mode == "remote_only":
            if online:
                return {
                    "provider": "remote",
                    "url": self._config.get("remote_url"),
                    "model": "",
                    "reason": "遠端模式",
                    "is_local": False,
                }
            return {
                "provider": "none",
                "url": "",
                "model": "",
                "reason": "遠端模式但無法連線",
                "is_local": False,
            }

        # 自動模式：本地優先，不夠再遠端加強
        if task_type in ("code", "execute"):
            # 執行型任務：本地優先（零成本）
            if ollama_available:
                model = self._pick_local_model(task_type)
                return {
                    "provider": "ollama",
                    "url": self._config.get("local_ollama_url"),
                    "model": model,
                    "reason": "執行型任務 → 本地優先（零成本）",
                    "is_local": True,
                }
            if online:
                return {
                    "provider": "remote",
                    "url": self._config.get("remote_url"),
                    "model": "",
                    "reason": "本地不可用 → 遠端降級",
                    "is_local": False,
                }

        elif task_type in ("think", "vision"):
            # 思考型/視覺任務：優先遠端（品質高）
            if online:
                # 檢查遠端配額
                usage = self._get_usage()
                if usage.get("remaining", 0) > 0 or usage.get("unlimited"):
                    return {
                        "provider": "remote",
                        "url": self._config.get("remote_url"),
                        "model": "",
                        "reason": "思考型任務 → 遠端加強（品質優先）",
                        "is_local": False,
                    }
            # 遠端不可用或配額用完 → 本地
            if ollama_available:
                model = self._pick_local_model(task_type)
                return {
                    "provider": "ollama",
                    "url": self._config.get("local_ollama_url"),
                    "model": model,
                    "reason": "遠端不可用/配額已盡 → 本地降級",
                    "is_local": True,
                }

        else:
            # 一般任務：本地優先
            if ollama_available:
                model = self._pick_local_model(task_type)
                return {
                    "provider": "ollama",
                    "url": self._config.get("local_ollama_url"),
                    "model": model,
                    "reason": "一般任務 → 本地優先",
                    "is_local": True,
                }
            if online:
                return {
                    "provider": "remote",
                    "url": self._config.get("remote_url"),
                    "model": "",
                    "reason": "本地不可用 → 遠端降級",
                    "is_local": False,
                }

        return {
            "provider": "none",
            "url": "",
            "model": "",
            "reason": "本地和遠端均不可用（完全離線）",
            "is_local": True,
        }

    def _pick_local_model(self, task_type: str) -> str:
        if task_type == "code":
            return self._config.get("local_coder_model", "qwen3:8b")
        elif task_type == "vision":
            return self._config.get("local_vision_model", "moondream")
        else:
            return self._config.get("local_ollama_model", "qwen3:32b")

    # ── 用量追蹤 ──

    def _get_usage(self) -> dict:
        """取得當月用量"""
        if not USAGE_FILE.exists():
            return {"month": "", "remote_calls": 0, "remaining": 0, "unlimited": False}
        try:
            data = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
            current_month = datetime.now().strftime("%Y-%m")
            if data.get("month") != current_month:
                # 新月份，重置
                data = {"month": current_month, "remote_calls": 0}
                USAGE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

            # 取得 License 配額
            try:
                from license_manager import validate_license
                lic = validate_license()
                limit = lic.get("remote_calls_per_month", 0)
                if limit == -1:
                    data["unlimited"] = True
                    data["remaining"] = 999999
                else:
                    data["remaining"] = max(0, limit - data.get("remote_calls", 0))
                    data["unlimited"] = False
            except Exception:
                data["remaining"] = 0
                data["unlimited"] = False

            return data
        except Exception:
            return {"month": "", "remote_calls": 0, "remaining": 0, "unlimited": False}

    def record_remote_call(self):
        """記錄一次遠端呼叫"""
        current_month = datetime.now().strftime("%Y-%m")
        try:
            if USAGE_FILE.exists():
                data = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
            else:
                data = {}
            if data.get("month") != current_month:
                data = {"month": current_month, "remote_calls": 0}
            data["remote_calls"] = data.get("remote_calls", 0) + 1
            data["last_call"] = datetime.now().isoformat(timespec="seconds")
            USAGE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def get_usage_stats(self) -> dict:
        """取得用量統計"""
        usage = self._get_usage()
        return {
            "month": usage.get("month", ""),
            "remote_calls": usage.get("remote_calls", 0),
            "remaining": usage.get("remaining", 0),
            "unlimited": usage.get("unlimited", False),
        }

    # ── 知識庫同步狀態 ──

    def get_sync_state(self) -> dict:
        if not SYNC_STATE_FILE.exists():
            return {"last_sync": None, "version": 0, "items_synced": 0}
        try:
            return json.loads(SYNC_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"last_sync": None, "version": 0, "items_synced": 0}

    def update_sync_state(self, version: int, items_synced: int):
        state = {
            "last_sync": datetime.now().isoformat(timespec="seconds"),
            "version": version,
            "items_synced": items_synced,
        }
        SYNC_STATE_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # ── 系統狀態總覽 ──

    def get_system_status(self) -> dict:
        """取得完整系統狀態（給 UI 用）"""
        ollama_ok = self.is_ollama_available(force_check=True)
        online = self.is_online(force_check=True)

        # License 狀態
        license_info = {"valid": False, "tier": "free"}
        try:
            from license_manager import validate_license, check_offline_grace
            license_info = validate_license()
            offline_info = check_offline_grace()
        except Exception:
            offline_info = {"ok": False}

        return {
            "ollama_available": ollama_ok,
            "ollama_url": self._config.get("local_ollama_url"),
            "online": online,
            "remote_url": self._config.get("remote_url"),
            "mode": self._config.get("mode"),
            "license": {
                "valid": license_info.get("valid", False),
                "tier": license_info.get("tier", "free"),
                "tier_name": license_info.get("tier_name", "免費體驗版"),
                "customer_name": license_info.get("customer_name", ""),
                "days_remaining": license_info.get("days_remaining", 0),
                "expires_at": license_info.get("expires_at", ""),
            },
            "offline_grace": {
                "ok": offline_info.get("ok", False),
                "days_offline": offline_info.get("days_offline", 0),
                "days_remaining": offline_info.get("days_remaining_offline", 0),
            },
            "usage": self.get_usage_stats(),
            "sync": self.get_sync_state(),
            "device": {
                "hostname": platform.node(),
                "os": f"{platform.system()} {platform.release()}",
                "arch": platform.machine(),
            },
        }


# ── 全域實例 ──
_client_config: Optional[ClientConfig] = None

def get_config() -> ClientConfig:
    global _client_config
    if _client_config is None:
        _client_config = ClientConfig()
    return _client_config

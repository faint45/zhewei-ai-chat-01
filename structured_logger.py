# -*- coding: utf-8 -*-
"""
築未科技 — 結構化日誌模組

商用核心：統一所有日誌輸出為 JSON 格式，支援：
  - 分級日誌（DEBUG/INFO/WARN/ERROR/CRITICAL）
  - 結構化欄位（timestamp, level, module, message, extra）
  - 多輸出（console + NDJSON 檔案 + 未來可接 ELK/Loki）
  - 請求追蹤（request_id）
  - 效能指標（duration_ms）

使用方式：
  from structured_logger import get_logger
  log = get_logger("ai_service")
  log.info("路由完成", provider="gemini", duration_ms=120)
"""
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "brain_workspace" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "brain_structured.ndjson"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
LOG_MAX_SIZE_MB = int(os.environ.get("LOG_MAX_SIZE_MB", "50"))


class StructuredFormatter(logging.Formatter):
    """將 log record 格式化為 JSON。"""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        # 附加結構化欄位
        if hasattr(record, "extra_fields"):
            entry.update(record.extra_fields)
        # 異常資訊
        if record.exc_info and record.exc_info[1]:
            entry["error"] = str(record.exc_info[1])
            entry["error_type"] = type(record.exc_info[1]).__name__
        return json.dumps(entry, ensure_ascii=False)


class StructuredLogger:
    """帶結構化欄位的 Logger 包裝。"""

    def __init__(self, name: str):
        self._logger = logging.getLogger(f"zhewei.{name}")
        self._logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
        self._name = name
        # 避免重複添加 handler
        if not self._logger.handlers:
            # Console handler（簡潔格式）
            ch = logging.StreamHandler(sys.stdout)
            ch.setFormatter(_ConsoleFormatter())
            self._logger.addHandler(ch)
            # File handler（NDJSON）
            try:
                fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
                fh.setFormatter(StructuredFormatter())
                self._logger.addHandler(fh)
            except Exception:
                pass

    def _log(self, level: int, msg: str, **kwargs):
        record = self._logger.makeRecord(
            self._name, level, "(structured)", 0, msg, (), None
        )
        record.extra_fields = kwargs
        self._logger.handle(record)

    def debug(self, msg: str, **kwargs):
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs):
        self._log(logging.INFO, msg, **kwargs)

    def warn(self, msg: str, **kwargs):
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs):
        self._log(logging.ERROR, msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        self._log(logging.CRITICAL, msg, **kwargs)


class _ConsoleFormatter(logging.Formatter):
    """Console 用的簡潔彩色格式。"""

    COLORS = {
        "DEBUG": "\033[36m",    # cyan
        "INFO": "\033[32m",     # green
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",    # red
        "CRITICAL": "\033[35m", # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        ts = datetime.now().strftime("%H:%M:%S")
        extra = ""
        if hasattr(record, "extra_fields") and record.extra_fields:
            parts = [f"{k}={v}" for k, v in record.extra_fields.items() if k not in ("ts", "level", "module")]
            if parts:
                extra = f" [{', '.join(parts[:5])}]"
        return f"{color}{ts} [{record.levelname[0]}] {record.name}: {record.getMessage()}{extra}{self.RESET}"


# ── 工廠函數 ──

_loggers: dict[str, StructuredLogger] = {}


def get_logger(name: str) -> StructuredLogger:
    """取得或建立結構化 Logger。"""
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    return _loggers[name]


# ── 監控儀表板資料 ──

def get_dashboard_data() -> dict:
    """
    彙整系統監控資料（供前端儀表板使用）。
    整合：用量、健康、日誌摘要。
    """
    data = {
        "timestamp": datetime.now().isoformat(),
        "usage": {},
        "health": {},
        "recent_errors": [],
        "log_stats": {},
    }

    # 用量摘要
    try:
        import usage_metering
        data["usage"]["today"] = usage_metering.get_today_summary()
        data["usage"]["system_30d"] = usage_metering.get_system_usage(30)
    except Exception:
        data["usage"]["error"] = "用量模組不可用"

    # 最近錯誤（從 NDJSON 日誌讀取最後 20 筆 ERROR）
    try:
        if LOG_FILE.exists():
            errors = []
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("level") in ("ERROR", "CRITICAL"):
                            errors.append(entry)
                    except Exception:
                        pass
            data["recent_errors"] = errors[-20:]
    except Exception:
        pass

    # 日誌統計
    try:
        if LOG_FILE.exists():
            counts = {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0}
            size_bytes = LOG_FILE.stat().st_size
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        lvl = entry.get("level", "INFO")
                        if lvl in counts:
                            counts[lvl] += 1
                    except Exception:
                        pass
            data["log_stats"] = {
                "counts": counts,
                "total": sum(counts.values()),
                "file_size_mb": round(size_bytes / 1024 / 1024, 2),
            }
    except Exception:
        pass

    return data

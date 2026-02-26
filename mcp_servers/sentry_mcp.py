#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 Sentry MCP Server
提供錯誤監控、日誌查詢、異常追蹤功能
"""
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

SERVER_NAME = "sentry_mcp"
mcp = FastMCP(SERVER_NAME)

LOG_DIR = Path(os.environ.get("LOG_DIR", "D:/zhe-wei-tech/reports"))
ERROR_KEYWORDS = ["error", "exception", "traceback", "failed", "fatal", "critical"]


def _parse_log_line(line: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line:
        return None
    
    ts_match = re.match(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", line)
    timestamp = ts_match.group(1) if ts_match else ""
    
    severity = "info"
    lower = line.lower()
    if any(k in lower for k in ["error", "exception", "traceback"]):
        severity = "error"
    elif any(k in lower for k in ["warn", "warning"]):
        severity = "warning"
    elif any(k in lower for k in ["fatal", "critical"]):
        severity = "critical"
    
    return {
        "timestamp": timestamp,
        "severity": severity,
        "message": line,
    }


@mcp.tool(
    name="sentry_recent_errors",
    annotations={
        "title": "Get recent errors from logs",
        "description": "查詢近期錯誤（從日誌檔案）",
    },
)
def sentry_recent_errors(hours: int = 24, severity: str = "error") -> str:
    try:
        if not LOG_DIR.exists():
            return json.dumps({"ok": False, "error": f"日誌目錄不存在: {LOG_DIR}"}, ensure_ascii=False)
        
        cutoff = datetime.now() - timedelta(hours=hours)
        errors = []
        
        for log_file in LOG_DIR.glob("*.log"):
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        parsed = _parse_log_line(line)
                        if not parsed:
                            continue
                        
                        if severity == "all" or parsed["severity"] == severity:
                            errors.append({
                                "file": log_file.name,
                                "timestamp": parsed["timestamp"],
                                "severity": parsed["severity"],
                                "message": parsed["message"][:200],
                            })
            except Exception:
                continue
        
        errors.sort(key=lambda x: x["timestamp"], reverse=True)
        return json.dumps({
            "ok": True,
            "count": len(errors),
            "errors": errors[:50],
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="sentry_log_search",
    annotations={
        "title": "Search logs by keyword",
        "description": "關鍵字搜尋日誌",
    },
)
def sentry_log_search(keyword: str, limit: int = 20) -> str:
    try:
        if not LOG_DIR.exists():
            return json.dumps({"ok": False, "error": f"日誌目錄不存在: {LOG_DIR}"}, ensure_ascii=False)
        
        keyword_lower = keyword.lower()
        matches = []
        
        for log_file in LOG_DIR.glob("*.log"):
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if keyword_lower in line.lower():
                            matches.append({
                                "file": log_file.name,
                                "line": line_num,
                                "content": line.strip()[:200],
                            })
                            if len(matches) >= limit:
                                break
            except Exception:
                continue
            
            if len(matches) >= limit:
                break
        
        return json.dumps({
            "ok": True,
            "keyword": keyword,
            "count": len(matches),
            "matches": matches,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="sentry_stats",
    annotations={
        "title": "Get error statistics",
        "description": "錯誤統計（按嚴重程度）",
    },
)
def sentry_stats() -> str:
    try:
        if not LOG_DIR.exists():
            return json.dumps({"ok": False, "error": f"日誌目錄不存在: {LOG_DIR}"}, ensure_ascii=False)
        
        stats = {
            "critical": 0,
            "error": 0,
            "warning": 0,
            "info": 0,
        }
        
        for log_file in LOG_DIR.glob("*.log"):
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        parsed = _parse_log_line(line)
                        if parsed:
                            stats[parsed["severity"]] = stats.get(parsed["severity"], 0) + 1
            except Exception:
                continue
        
        return json.dumps({
            "ok": True,
            "stats": stats,
            "total": sum(stats.values()),
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="sentry_list_logs",
    annotations={
        "title": "List all log files",
        "description": "列出所有日誌檔案",
    },
)
def sentry_list_logs() -> str:
    try:
        if not LOG_DIR.exists():
            return json.dumps({"ok": False, "error": f"日誌目錄不存在: {LOG_DIR}"}, ensure_ascii=False)
        
        logs = []
        for log_file in LOG_DIR.glob("*.log"):
            stat = log_file.stat()
            logs.append({
                "name": log_file.name,
                "size_kb": round(stat.st_size / 1024, 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        
        logs.sort(key=lambda x: x["modified"], reverse=True)
        return json.dumps({
            "ok": True,
            "count": len(logs),
            "logs": logs,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()

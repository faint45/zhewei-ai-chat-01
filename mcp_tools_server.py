#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 — MCP 工具伺服器
將 local_agent 工具集包裝成 MCP (Model Context Protocol) server
讓 Open WebUI / Claude Desktop / 任何 MCP 客戶端可以呼叫

啟動方式:
  python mcp_tools_server.py          # 預設 port 18020
  python mcp_tools_server.py --port 18020

Open WebUI 設定:
  Settings → Tools → Add Tool Server
  URL: http://localhost:18020
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MCP] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="築未科技 MCP Tools Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WORKDIR = Path("D:/zhe-wei-tech")


# ── 工具實作 ──────────────────────────────────────────

def _run_command(command: str, cwd: str = None, timeout: int = 60) -> str:
    try:
        workdir = Path(cwd) if cwd else WORKDIR
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            cwd=str(workdir), timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        if err:
            out += f"\n[STDERR] {err}" if out else err
        if result.returncode != 0:
            out = f"[EXIT {result.returncode}]\n{out}" if out else f"[EXIT {result.returncode}]"
        return out or "(無輸出)"
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT] 超過 {timeout}s"
    except Exception as e:
        return f"[ERROR] {e}"


def _read_file(path: str) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return f"[ERROR] 檔案不存在: {path}"
        size = p.stat().st_size
        if size > 80_000:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            head = "\n".join(lines[:80])
            tail = "\n".join(lines[-30:])
            return f"[大檔案，顯示頭80行+尾30行]\n{head}\n...\n{tail}"
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[ERROR] {e}"


def _write_file(path: str, content: str) -> str:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"✅ 已寫入: {path} ({len(content)} chars)"
    except Exception as e:
        return f"[ERROR] {e}"


def _list_dir(path: str = ".", max_items: int = 60) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return f"[ERROR] 目錄不存在: {path}"
        items = []
        for item in sorted(p.iterdir()):
            icon = "📁" if item.is_dir() else "📄"
            size = f" ({item.stat().st_size//1024}K)" if item.is_file() else ""
            items.append(f"{icon} {item.name}{size}")
            if len(items) >= max_items:
                items.append(f"... (超過 {max_items} 項)")
                break
        return "\n".join(items) or "(空目錄)"
    except Exception as e:
        return f"[ERROR] {e}"


def _search_in_file(path: str, pattern: str) -> str:
    try:
        import re
        p = Path(path)
        if not p.exists():
            return f"[ERROR] 檔案不存在: {path}"
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        matches = [f"Line {i+1}: {l.rstrip()}" for i, l in enumerate(lines)
                   if re.search(pattern, l, re.IGNORECASE)]
        return "\n".join(matches) if matches else f"(未找到 '{pattern}')"
    except Exception as e:
        return f"[ERROR] {e}"


def _ollama_chat(message: str, model: str = "zhewei-qwen3-32b-deep") -> str:
    import urllib.request
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11460")
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 4096}
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{ollama_url}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data.get("message", {}).get("content", "(無回應)")
    except Exception as e:
        return f"[ERROR] {e}"


# ── MCP 標準端點 ──────────────────────────────────────

@app.get("/")
async def root():
    return {"name": "築未科技 MCP Tools Server", "version": "1.0.0", "status": "ok"}


@app.get("/.well-known/mcp")
async def mcp_manifest():
    """MCP 服務清單"""
    return {
        "name": "築未科技工具集",
        "description": "築未科技本地工具：命令執行、檔案操作、AI 對話",
        "version": "1.0.0",
        "tools": [
            {
                "name": "run_command",
                "description": "執行 shell 命令或 Python 腳本，回傳執行結果",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "要執行的命令"},
                        "cwd": {"type": "string", "description": "工作目錄（可選）"},
                        "timeout": {"type": "integer", "description": "超時秒數（預設60）"}
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "read_file",
                "description": "讀取檔案內容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "檔案完整路徑"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "write_file",
                "description": "寫入或建立檔案",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "檔案完整路徑"},
                        "content": {"type": "string", "description": "檔案內容"}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "list_dir",
                "description": "列出目錄內容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "目錄路徑"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "search_in_file",
                "description": "在檔案中搜尋文字模式",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "檔案路徑"},
                        "pattern": {"type": "string", "description": "搜尋關鍵字（支援正則）"}
                    },
                    "required": ["path", "pattern"]
                }
            },
            {
                "name": "ollama_chat",
                "description": "呼叫本地 Ollama 模型進行深度討論",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "訊息內容"},
                        "model": {"type": "string", "description": "模型名稱（預設 zhewei-qwen3-32b-deep）"}
                    },
                    "required": ["message"]
                }
            }
        ]
    }


@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, request: Request):
    """執行工具"""
    try:
        body = await request.json()
    except Exception:
        body = {}

    logger.info(f"Tool: {tool_name}, Args: {list(body.keys())}")

    tool_map = {
        "run_command": _run_command,
        "read_file": _read_file,
        "write_file": _write_file,
        "list_dir": _list_dir,
        "search_in_file": _search_in_file,
        "ollama_chat": _ollama_chat,
    }

    if tool_name not in tool_map:
        raise HTTPException(status_code=404, detail=f"工具不存在: {tool_name}")

    try:
        result = tool_map[tool_name](**body)
        return {"result": result, "tool": tool_name, "success": True}
    except TypeError as e:
        raise HTTPException(status_code=400, detail=f"參數錯誤: {e}")
    except Exception as e:
        logger.error(f"Tool {tool_name} error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "tools": 6}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="築未科技 MCP Tools Server")
    parser.add_argument("--port", type=int, default=18020, help="Port (預設 18020)")
    parser.add_argument("--host", default="0.0.0.0", help="Host")
    args = parser.parse_args()
    logger.info(f"MCP Tools Server 啟動於 http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)

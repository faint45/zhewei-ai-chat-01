# -*- coding: utf-8 -*-
"""
築未科技 — FFmpeg 影音處理 MCP Server（免費，本地執行）
─────────────────────────────────────────────────────────
提供影片剪輯、格式轉換、音訊處理、截圖等功能。
適用角色：影音創作工程師
需求：系統已安裝 ffmpeg（ffmpeg -version 可執行）
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("ffmpeg-video-mcp")

WORK_DIR = Path(os.environ.get("FFMPEG_WORK_DIR", "D:/zhe-wei-tech/brain_workspace/media"))
WORK_DIR.mkdir(parents=True, exist_ok=True)


def _run_ffmpeg(args: list[str], timeout: int = 120) -> dict:
    cmd = ["ffmpeg", "-y"] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"ok": r.returncode == 0, "stdout": r.stdout[-500:] if r.stdout else "", "stderr": r.stderr[-500:] if r.stderr else ""}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "FFmpeg 執行超時"}
    except FileNotFoundError:
        return {"ok": False, "error": "ffmpeg 未安裝或不在 PATH 中"}


def _run_ffprobe(filepath: str) -> dict:
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", filepath]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return json.loads(r.stdout)
        return {"error": r.stderr[-300:]}
    except Exception as e:
        return {"error": str(e)}


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="video_info",
            description="取得影片/音訊檔案的詳細資訊（時長、解析度、編碼、位元率等）",
            inputSchema={
                "type": "object",
                "properties": {"filepath": {"type": "string", "description": "檔案路徑"}},
                "required": ["filepath"],
            },
        ),
        Tool(
            name="video_trim",
            description="剪輯影片片段（指定開始時間和持續時間）",
            inputSchema={
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "輸入檔案路徑"},
                    "start": {"type": "string", "description": "開始時間，如 00:01:30 或 90（秒）"},
                    "duration": {"type": "string", "description": "持續時間，如 00:00:30 或 30（秒）"},
                    "output": {"type": "string", "description": "輸出檔案路徑（可選）"},
                },
                "required": ["input", "start", "duration"],
            },
        ),
        Tool(
            name="video_convert",
            description="轉換影片格式（mp4/webm/avi/mov/gif）",
            inputSchema={
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "輸入檔案路徑"},
                    "format": {"type": "string", "description": "目標格式：mp4/webm/avi/mov/gif"},
                    "output": {"type": "string", "description": "輸出檔案路徑（可選）"},
                },
                "required": ["input", "format"],
            },
        ),
        Tool(
            name="video_screenshot",
            description="從影片截取一張圖片",
            inputSchema={
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "輸入影片路徑"},
                    "time": {"type": "string", "description": "截取時間點，如 00:00:05 或 5"},
                    "output": {"type": "string", "description": "輸出圖片路徑（可選，預設 .png）"},
                },
                "required": ["input", "time"],
            },
        ),
        Tool(
            name="extract_audio",
            description="從影片中提取音訊（mp3/wav/aac）",
            inputSchema={
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "輸入影片路徑"},
                    "format": {"type": "string", "description": "音訊格式：mp3/wav/aac", "default": "mp3"},
                    "output": {"type": "string", "description": "輸出音訊路徑（可選）"},
                },
                "required": ["input"],
            },
        ),
        Tool(
            name="video_resize",
            description="調整影片解析度",
            inputSchema={
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "輸入影片路徑"},
                    "width": {"type": "integer", "description": "目標寬度（-1 自動等比例）"},
                    "height": {"type": "integer", "description": "目標高度（-1 自動等比例）"},
                    "output": {"type": "string", "description": "輸出檔案路徑（可選）"},
                },
                "required": ["input", "width", "height"],
            },
        ),
        Tool(
            name="merge_videos",
            description="合併多個影片（相同編碼格式）",
            inputSchema={
                "type": "object",
                "properties": {
                    "inputs": {"type": "string", "description": "逗號分隔的輸入檔案路徑"},
                    "output": {"type": "string", "description": "輸出檔案路徑"},
                },
                "required": ["inputs", "output"],
            },
        ),
        Tool(
            name="add_subtitle",
            description="為影片添加字幕檔（SRT/ASS）",
            inputSchema={
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "輸入影片路徑"},
                    "subtitle": {"type": "string", "description": "字幕檔路徑（.srt 或 .ass）"},
                    "output": {"type": "string", "description": "輸出檔案路徑（可選）"},
                },
                "required": ["input", "subtitle"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "video_info":
            info = _run_ffprobe(arguments["filepath"])
            return [TextContent(type="text", text=json.dumps(info, ensure_ascii=False, indent=2))]

        elif name == "video_trim":
            inp = arguments["input"]
            out = arguments.get("output") or str(WORK_DIR / f"trim_{Path(inp).stem}.mp4")
            r = _run_ffmpeg(["-i", inp, "-ss", arguments["start"], "-t", arguments["duration"], "-c", "copy", out])
            r["output"] = out
            return [TextContent(type="text", text=json.dumps(r, ensure_ascii=False))]

        elif name == "video_convert":
            inp = arguments["input"]
            fmt = arguments["format"]
            out = arguments.get("output") or str(WORK_DIR / f"convert_{Path(inp).stem}.{fmt}")
            r = _run_ffmpeg(["-i", inp, out])
            r["output"] = out
            return [TextContent(type="text", text=json.dumps(r, ensure_ascii=False))]

        elif name == "video_screenshot":
            inp = arguments["input"]
            out = arguments.get("output") or str(WORK_DIR / f"screenshot_{Path(inp).stem}.png")
            r = _run_ffmpeg(["-i", inp, "-ss", arguments["time"], "-vframes", "1", out])
            r["output"] = out
            return [TextContent(type="text", text=json.dumps(r, ensure_ascii=False))]

        elif name == "extract_audio":
            inp = arguments["input"]
            fmt = arguments.get("format", "mp3")
            out = arguments.get("output") or str(WORK_DIR / f"audio_{Path(inp).stem}.{fmt}")
            r = _run_ffmpeg(["-i", inp, "-vn", "-acodec", {"mp3": "libmp3lame", "wav": "pcm_s16le", "aac": "aac"}.get(fmt, "copy"), out])
            r["output"] = out
            return [TextContent(type="text", text=json.dumps(r, ensure_ascii=False))]

        elif name == "video_resize":
            inp = arguments["input"]
            w, h = arguments["width"], arguments["height"]
            out = arguments.get("output") or str(WORK_DIR / f"resize_{Path(inp).stem}.mp4")
            r = _run_ffmpeg(["-i", inp, "-vf", f"scale={w}:{h}", out])
            r["output"] = out
            return [TextContent(type="text", text=json.dumps(r, ensure_ascii=False))]

        elif name == "merge_videos":
            inputs = [s.strip() for s in arguments["inputs"].split(",") if s.strip()]
            list_file = str(WORK_DIR / "merge_list.txt")
            with open(list_file, "w") as f:
                for inp in inputs:
                    f.write(f"file '{inp}'\n")
            out = arguments["output"]
            r = _run_ffmpeg(["-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", out])
            r["output"] = out
            return [TextContent(type="text", text=json.dumps(r, ensure_ascii=False))]

        elif name == "add_subtitle":
            inp = arguments["input"]
            sub = arguments["subtitle"]
            out = arguments.get("output") or str(WORK_DIR / f"subtitled_{Path(inp).stem}.mp4")
            r = _run_ffmpeg(["-i", inp, "-vf", f"subtitles={sub}", out])
            r["output"] = out
            return [TextContent(type="text", text=json.dumps(r, ensure_ascii=False))]

        else:
            return [TextContent(type="text", text=f"未知工具: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"錯誤: {e}")]


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

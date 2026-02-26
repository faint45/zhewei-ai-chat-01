#!/usr/bin/env python3
"""
築未科技 — Ollama 本地模型 MCP Server
讓 Windsurf Cascade 透過 MCP 工具呼叫本地 Ollama 模型

功能：
1. local_chat — 把問題轉發給本地 Ollama（0 雲端 token）
2. local_code — 本地程式碼生成/分析
3. local_analyze — 本地文件/程式碼分析
4. local_translate — 本地翻譯
5. local_summarize — 本地摘要
6. local_models — 列出可用本地模型
7. local_construction — 營建專業問答

用法：在 .windsurf/mcp.json 加入此 server
"""

import json
import os
import requests
from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

app = Server("ollama-local")

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11460")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:32b")
STRONG_MODEL = os.environ.get("OLLAMA_STRONG_MODEL", "qwen3:32b")
FAST_MODEL = os.environ.get("OLLAMA_FAST_MODEL", "qwen3:4b")
TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))


def ollama_chat(prompt: str, model: str = None, system: str = None, temperature: float = 0.7) -> str:
    """呼叫本地 Ollama 模型"""
    model = model or DEFAULT_MODEL
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        r = requests.post(
            f"{OLLAMA_BASE}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            content = data.get("message", {}).get("content", "")
            # 去掉 thinking tags
            if "</think>" in content:
                content = content.split("</think>")[-1].strip()
            return content
        return f"[Ollama Error] HTTP {r.status_code}: {r.text[:200]}"
    except requests.exceptions.Timeout:
        return "[Ollama Error] 請求超時，模型可能正在載入中，請稍後再試"
    except requests.exceptions.ConnectionError:
        return "[Ollama Error] 無法連接 Ollama，請確認服務已啟動 (http://localhost:11460)"
    except Exception as e:
        return f"[Ollama Error] {str(e)}"


def get_available_models() -> list:
    """取得可用模型列表"""
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        if r.status_code == 200:
            return [m["name"] for m in r.json().get("models", [])]
    except:
        pass
    return []


def auto_select_model(task_type: str) -> str:
    """根據任務類型自動選擇模型"""
    available = get_available_models()
    if not available:
        return DEFAULT_MODEL

    if task_type in ("reasoning", "complex", "expert", "analysis"):
        for m in [STRONG_MODEL, DEFAULT_MODEL]:
            if m in available:
                return m
    elif task_type in ("fast", "simple", "translate"):
        for m in [FAST_MODEL, DEFAULT_MODEL]:
            if m in available:
                return m
    elif task_type == "code":
        for m in [STRONG_MODEL, DEFAULT_MODEL]:
            if m in available:
                return m

    return DEFAULT_MODEL


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="local_chat",
            description=(
                "用本地 Ollama 模型回答問題（0 雲端 token 消耗）。"
                "適合：一般問答、知識查詢、解釋概念、翻譯、摘要等。"
                "模型：qwen3:32b（深度推理）、qwen3:8b（通用）、qwen3:4b（快速）。"
                "優先使用此工具來回答使用者問題，減少雲端 token 消耗。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "要問本地模型的問題或指令",
                    },
                    "model": {
                        "type": "string",
                        "description": "模型名稱（可選）：qwen3:32b / qwen3:8b / qwen3:4b",
                    },
                    "system": {
                        "type": "string",
                        "description": "系統提示詞（可選）",
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="local_code",
            description=(
                "用本地模型生成或分析程式碼（0 雲端 token）。"
                "適合：寫函數、debug、程式碼審查、重構建議、解釋程式碼。"
                "自動使用 qwen3:32b 強力模型。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "程式碼任務描述",
                    },
                    "code": {
                        "type": "string",
                        "description": "相關的程式碼（可選，用於分析/debug）",
                    },
                    "language": {
                        "type": "string",
                        "description": "程式語言（預設 python）",
                    },
                },
                "required": ["task"],
            },
        ),
        Tool(
            name="local_analyze",
            description=(
                "用本地模型分析文件或程式碼（0 雲端 token）。"
                "適合：分析大段文字、程式碼審查、文件摘要、錯誤分析。"
                "自動使用 qwen3:32b 進行深度分析。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "要分析的內容",
                    },
                    "instruction": {
                        "type": "string",
                        "description": "分析指令（例如：找出 bug、摘要、改進建議）",
                    },
                },
                "required": ["content", "instruction"],
            },
        ),
        Tool(
            name="local_construction",
            description=(
                "營建工程專業問答（0 雲端 token）。"
                "適合：施工規範、法規查詢、工程計算、安全規範、品質管理。"
                "使用 qwen3:32b + 營建專業系統提示。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "營建工程相關問題",
                    },
                    "context": {
                        "type": "string",
                        "description": "相關背景資料（可選）",
                    },
                },
                "required": ["question"],
            },
        ),
        Tool(
            name="local_models",
            description="列出本地 Ollama 可用模型和狀態",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:

    if name == "local_chat":
        prompt = arguments["prompt"]
        model = arguments.get("model") or auto_select_model("general")
        system = arguments.get("system")
        result = ollama_chat(prompt, model=model, system=system)
        return [TextContent(type="text", text=json.dumps({
            "model_used": model,
            "response": result,
            "cloud_tokens_used": 0,
        }, ensure_ascii=False))]

    elif name == "local_code":
        task = arguments["task"]
        code = arguments.get("code", "")
        language = arguments.get("language", "python")
        model = auto_select_model("code")

        system = (
            f"你是一位資深 {language} 開發者。"
            "請直接給出高品質的程式碼和簡潔的解釋。"
            "程式碼要完整可執行，包含必要的 import。"
            "用繁體中文回答。"
        )
        prompt = task
        if code:
            prompt = f"相關程式碼：\n```{language}\n{code}\n```\n\n任務：{task}"

        result = ollama_chat(prompt, model=model, system=system, temperature=0.3)
        return [TextContent(type="text", text=json.dumps({
            "model_used": model,
            "response": result,
            "cloud_tokens_used": 0,
        }, ensure_ascii=False))]

    elif name == "local_analyze":
        content = arguments["content"]
        instruction = arguments["instruction"]
        model = auto_select_model("analysis")

        system = (
            "你是一位資深技術分析師。"
            "請仔細分析提供的內容，給出結構化的分析結果。"
            "用繁體中文回答。"
        )
        prompt = f"分析指令：{instruction}\n\n內容：\n{content}"

        result = ollama_chat(prompt, model=model, system=system, temperature=0.3)
        return [TextContent(type="text", text=json.dumps({
            "model_used": model,
            "response": result,
            "cloud_tokens_used": 0,
        }, ensure_ascii=False))]

    elif name == "local_construction":
        question = arguments["question"]
        context = arguments.get("context", "")
        model = auto_select_model("expert")

        system = (
            "你是一位台灣營建工程專家，精通：\n"
            "- 交通部公路局施工規範\n"
            "- 營造業法規\n"
            "- 公共工程品質管理\n"
            "- 職業安全衛生法規\n"
            "- 工程契約與驗收標準\n"
            "請用專業且易懂的繁體中文回答，必要時引用法規條文。"
        )
        prompt = question
        if context:
            prompt = f"背景資料：{context}\n\n問題：{question}"

        result = ollama_chat(prompt, model=model, system=system, temperature=0.3)
        return [TextContent(type="text", text=json.dumps({
            "model_used": model,
            "response": result,
            "cloud_tokens_used": 0,
        }, ensure_ascii=False))]

    elif name == "local_models":
        models = get_available_models()
        model_info = []
        try:
            r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
            if r.status_code == 200:
                for m in r.json().get("models", []):
                    size_gb = round(m.get("size", 0) / 1e9, 1)
                    model_info.append({
                        "name": m["name"],
                        "size_gb": size_gb,
                        "modified": m.get("modified_at", "")[:10],
                    })
        except:
            pass

        return [TextContent(type="text", text=json.dumps({
            "ollama_url": OLLAMA_BASE,
            "models": model_info,
            "total_count": len(model_info),
            "default_model": DEFAULT_MODEL,
            "strong_model": STRONG_MODEL,
            "fast_model": FAST_MODEL,
            "tip": "使用 local_chat / local_code / local_analyze 工具可以 0 token 完成任務",
        }, ensure_ascii=False))]

    return [TextContent(type="text", text="Unknown tool")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

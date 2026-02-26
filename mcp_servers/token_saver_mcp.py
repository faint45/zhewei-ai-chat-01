import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Any, Optional
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

app = Server("token-saver")

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_FILE = os.path.join(CACHE_DIR, "response_cache.json")
MAX_CACHE_AGE_DAYS = 7

def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def get_cache_key(prompt: str, model: str) -> str:
    data = f"{model}:{prompt}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]

def compress_history(messages: list, max_tokens: int = 2000) -> list:
    if len(messages) <= 4:
        return messages
    
    compressed = [messages[0]]
    
    for msg in messages[1:-1]:
        content = msg.get("content", "")
        if isinstance(content, str) and len(content) > 500:
            compressed.append({
                "role": msg.get("role", "user"),
                "content": f"[摘要] {content[:200]}... (原始長度: {len(content)} 字)"
            })
        else:
            compressed.append(msg)
    
    compressed.append(messages[-1])
    return compressed

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_cached_response",
            description="取得快取的回覆（省 token）",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "使用者問題"},
                    "model": {"type": "string", "description": "模型名稱"}
                },
                "required": ["prompt"]
            }
        ),
        Tool(
            name="cache_response",
            description="快取回覆（省 token）",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "使用者問題"},
                    "response": {"type": "string", "description": "AI 回覆"},
                    "model": {"type": "string", "description": "模型名稱"}
                },
                "required": ["prompt", "response"]
            }
        ),
        Tool(
            name="compress_conversation",
            description="壓縮對話歷史（省 token）",
            inputSchema={
                "type": "object",
                "properties": {
                    "messages": {"type": "array", "description": "對話歷史"},
                    "max_tokens": {"type": "integer", "description": "最大 token 估計"}
                },
                "required": ["messages"]
            }
        ),
        Tool(
            name="get_cache_stats",
            description="取得快取統計",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="clear_cache",
            description="清除過期快取",
            inputSchema={
                "type": "object",
                "properties": {
                    "days_old": {"type": "integer", "description": "超過天數的快取"}
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    cache = load_cache()
    
    if name == "get_cached_response":
        prompt = arguments["prompt"]
        model = arguments.get("model", "default")
        key = get_cache_key(prompt, model)
        
        if key in cache:
            entry = cache[key]
            cached_at = datetime.fromisoformat(entry["cached_at"])
            if datetime.now() - cached_at < timedelta(days=MAX_CACHE_AGE_DAYS):
                return [TextContent(type="text", text=json.dumps({
                    "cached": True,
                    "response": entry["response"],
                    "cached_at": entry["cached_at"]
                }, ensure_ascii=False))]
        
        return [TextContent(type="text", text=json.dumps({"cached": False}))]
    
    elif name == "cache_response":
        prompt = arguments["prompt"]
        response = arguments["response"]
        model = arguments.get("model", "default")
        key = get_cache_key(prompt, model)
        
        cache[key] = {
            "prompt": prompt,
            "response": response,
            "model": model,
            "cached_at": datetime.now().isoformat()
        }
        save_cache(cache)
        
        return [TextContent(type="text", text=json.dumps({"cached": True, "key": key}))]
    
    elif name == "compress_conversation":
        messages = arguments["messages"]
        max_tokens = arguments.get("max_tokens", 2000)
        compressed = compress_history(messages, max_tokens)
        
        original_chars = sum(len(str(m.get("content", ""))) for m in messages)
        compressed_chars = sum(len(str(m.get("content", ""))) for m in compressed)
        saved = original_chars - compressed_chars
        
        return [TextContent(type="text", text=json.dumps({
            "compressed_messages": compressed,
            "original_chars": original_chars,
            "compressed_chars": compressed_chars,
            "saved_chars": saved,
            "savings_percent": round(saved / original_chars * 100, 1) if original_chars > 0 else 0
        }, ensure_ascii=False))]
    
    elif name == "get_cache_stats":
        total = len(cache)
        total_chars = sum(len(str(v.get("response", ""))) for v in cache.values())
        
        return [TextContent(type="text", text=json.dumps({
            "total_cached": total,
            "total_chars": total_chars,
            "estimated_saved_tokens": total_chars // 4,
            "cache_file": CACHE_FILE
        }))]
    
    elif name == "clear_cache":
        days_old = arguments.get("days_old", 7)
        cutoff = datetime.now() - timedelta(days=days_old)
        
        removed = 0
        for key, entry in list(cache.items()):
            cached_at = datetime.fromisoformat(entry["cached_at"])
            if cached_at < cutoff:
                del cache[key]
                removed += 1
        
        save_cache(cache)
        return [TextContent(type="text", text=json.dumps({"removed": removed, "remaining": len(cache)}))]
    
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

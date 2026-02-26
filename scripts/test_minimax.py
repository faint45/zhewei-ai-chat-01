# -*- coding: utf-8 -*-
"""Quick test for MiniMax M2.5 API connectivity."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 手動讀取 .env（處理非 UTF-8 編碼）
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
for enc in ("utf-8", "utf-8-sig", "cp950", "latin-1"):
    try:
        with open(env_path, encoding=enc) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
        break
    except (UnicodeDecodeError, FileNotFoundError):
        continue

import httpx

async def test():
    api_key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if not api_key:
        print("❌ MINIMAX_API_KEY 未設定")
        return

    print(f"🔑 API Key: {api_key[:10]}...{api_key[-6:]}")
    url = "https://api.minimax.io/v1/text/chatcompletion_v2"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "MiniMax-M2.5",
        "messages": [{"role": "user", "content": "你好，請用一句話介紹自己"}],
        "stream": False,
        "max_completion_tokens": 1024,
    }

    print("📡 正在連線 MiniMax API...")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, json=payload, headers=headers)
            data = r.json()
            base = data.get("base_resp", {})
            if base.get("status_code", 0) != 0:
                print(f"❌ API 錯誤: {base}")
            else:
                choices = data.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    content = msg.get("content", "")
                    reasoning = msg.get("reasoning_content", "")
                    usage = data.get("usage", {})
                    details = usage.get("completion_tokens_details", {})
                    print(f"✅ MiniMax M2.5 回應成功！")
                    if reasoning:
                        print(f"🧠 推理: {reasoning[:200]}...")
                    print(f"📝 回應: {content[:300] if content else '(空，可能需增加 max_completion_tokens)'}")
                    print(f"📊 Token: input={usage.get('prompt_tokens', '?')}, output={usage.get('completion_tokens', '?')}, reasoning={details.get('reasoning_tokens', '?')}")
                else:
                    print(f"❌ 無 choices: {data}")
    except Exception as e:
        print(f"❌ 連線失敗: {e}")

if __name__ == "__main__":
    asyncio.run(test())

"""
Ollama 本地 Gemma 客戶端 - 非同步、無雲端依賴
"""
import asyncio
import json
from typing import AsyncIterator, Optional

import httpx

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma3:4b"
VISION_MODEL = "llava"
DEFAULT_TIMEOUT = 120.0


async def get_local_intelligence(
    prompt: str,
    model: str = DEFAULT_MODEL,
    timeout: float = DEFAULT_TIMEOUT,
    images: Optional[list[str]] = None,
) -> Optional[str]:
    """
    透過 Ollama 呼叫本地模型，支援圖片 (需 llava 等視覺模型)
    """
    url = f"{OLLAMA_URL}/api/generate"
    model = VISION_MODEL if images else model
    payload = {"model": model, "prompt": prompt, "stream": False}
    if images:
        payload["images"] = images
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
        except (httpx.HTTPError, KeyError) as e:
            print(f"[Ollama] 錯誤: {e}")
            return None


async def stream_local_intelligence(
    prompt: str,
    model: str = DEFAULT_MODEL,
    timeout: float = DEFAULT_TIMEOUT,
) -> AsyncIterator[str]:
    """
    串流模式：邊產生邊回傳，降低延遲感
    """
    url = f"{OLLAMA_URL}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": True}
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        if chunk:
                            yield chunk
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            print(f"[Ollama] 串流錯誤: {e}")


async def analyze_dashboard(throughput_mbps: float, ops: int, node: str) -> Optional[str]:
    """讓 Gemma 根據看板數據給建議"""
    prompt = f"""根據以下戰情數據給予簡短建議（1-2 句）：
- 吞吐量: {throughput_mbps:.1f} MB/s
- 累計操作: {ops} ops
- 當前節點: {node}

是否需要切換節點？網路狀態如何？"""
    return await get_local_intelligence(prompt)


if __name__ == "__main__":
    result = asyncio.run(get_local_intelligence("用一句話介紹你自己"))
    print(result or "(無回應)")

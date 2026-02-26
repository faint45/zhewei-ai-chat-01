"""
連線探測器 - 週期性探測目標網站，將數據寫入看板
"""
import asyncio
import time

import httpx


class MessengerProbe:
    def __init__(self, db):
        self.db = db
        self.targets = [
            "https://www.google.com",
            "https://www.youtube.com",
            "https://github.com",
        ]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def probe_site(self, url: str) -> str:
        async with httpx.AsyncClient(headers=self.headers, timeout=5.0) as client:
            try:
                start = time.perf_counter()
                resp = await client.get(url)
                latency = time.perf_counter() - start
                self.db.record(bytes_count=len(resp.content), ops=1)
                return f"[OK] {url} - {latency:.2f}s"
            except Exception as e:
                return f"[ERR] {url} - {type(e).__name__}"

    async def run_forever(self, interval: int = 10):
        while True:
            tasks = [self.probe_site(url) for url in self.targets]
            await asyncio.gather(*tasks)
            await asyncio.sleep(interval)

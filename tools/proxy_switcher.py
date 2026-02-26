"""
代理切換器 - 測試代理節點，失敗時自動切換至下一個
"""
import asyncio
import time

import httpx


class ProxySwitcher:
    def __init__(self, db=None):
        self.db = db
        self.proxy_list = [
            "http://proxy1.example.com:8080",
            "http://proxy2.example.com:8080",
            None,
        ]
        self.current_proxy = None

    async def test_and_switch(self, target_url: str = "https://www.google.com") -> bool:
        for proxy in self.proxy_list:
            transport = httpx.AsyncHTTPTransport(proxy=proxy)
            async with httpx.AsyncClient(transport=transport, timeout=3.0) as client:
                try:
                    start = time.perf_counter()
                    resp = await client.get(target_url)
                    latency = time.perf_counter() - start
                    if resp.status_code == 200:
                        self.current_proxy = proxy
                        label = proxy if proxy else "本地直連 (Minxiong)"
                        if self.db:
                            self.db.record(bytes_count=len(resp.content), ops=1)
                            self.db.current_node = label
                            self.db.switch_count += 1
                        print(f"[OK] 已切換至: {label} - {latency:.2f}s")
                        return True
                except Exception:
                    label = proxy if proxy else "本地直連"
                    print(f"[ERR] 節點失效: {label}")
        return False

    async def maintenance_loop(self, interval: int = 60):
        while True:
            success = await self.test_and_switch()
            if not success:
                print("[警告] 所有節點均已阻塞，請更新代理列表。")
            await asyncio.sleep(interval)

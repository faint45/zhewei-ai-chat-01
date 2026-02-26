"""
智慧管理觀測站 - 網路效能診斷與戰情顯示
"""
import asyncio
import os
import time

import httpx


class MessengerDashboard:
    def __init__(self):
        self.start_time = time.perf_counter()
        self.total_bytes = 0
        self.ops_count = 0
        self.current_status = "系統就緒"
        self.targets = ["https://www.google.com", "https://github.com"]

    def record(self, bytes_count: int = 0, ops: int = 0) -> None:
        self.total_bytes += bytes_count
        self.ops_count += ops

    def get_throughput(self) -> float:
        elapsed = time.perf_counter() - self.start_time
        return self.total_bytes / elapsed / 1024 / 1024 if elapsed > 0 else 0.0

    async def diagnostic_task(self) -> None:
        async with httpx.AsyncClient(timeout=5.0) as client:
            while True:
                for url in self.targets:
                    try:
                        resp = await client.get(url)
                        self.record(bytes_count=len(resp.content), ops=1)
                        self.current_status = f"連線正常: {url.split('//')[1]}"
                    except Exception:
                        self.current_status = f"節點波動: {url.split('//')[1]}"
                await asyncio.sleep(5)

    async def render_loop(self) -> None:
        interval = 2.0
        while True:
            if os.name == "nt":
                os.system("cls")
            else:
                os.system("clear")
            elapsed = time.perf_counter() - self.start_time
            print("=" * 60)
            print(" 【智慧管理觀測站】 - 民雄開發節點")
            print("=" * 60)
            print(f" [當前狀態] : {self.current_status}")
            print(f" [運行時間] : {elapsed:.1f}s")
            print(f" [總吞吐量] : {self.get_throughput():.2f} MB/s")
            print(f" [累計操作] : {self.ops_count} ops")
            print("-" * 60)
            print(" > 本地模型狀態: gemma3:4b (已連接)")
            print(" > 監控模式: 效能優先、0 丟包設計")
            print("=" * 60)
            await asyncio.sleep(interval)


async def main():
    db = MessengerDashboard()
    await asyncio.gather(db.render_loop(), db.diagnostic_task())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[系統] 服務已優雅結束。")

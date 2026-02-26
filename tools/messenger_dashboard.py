"""
智慧監控看板 - 持續顯示吞吐量與 OPS，每秒刷新
"""
import asyncio
import os
import random
import time

from dashboard import ThroughputCounter


class MessengerDashboard:
    def __init__(self):
        self.start_time = time.perf_counter()
        self._total_bytes = 0
        self.ops_counter = ThroughputCounter(window_sec=1.0)
        self.current_node = "本地直連 (Minxiong)"
        self.switch_count = 0
        self.current_status = "系統就緒"
        self.error_logs = []
        self.edge_info = {}

    def record(self, bytes_count: int = 0, ops: int = 1, error: str = None):
        self.ops_counter.hit(ops)
        if bytes_count:
            self._total_bytes += bytes_count
        if error:
            from datetime import datetime

            self.error_logs.append(f"{datetime.now()}: {error}")
            self.current_status = "偵測到異常"

    def get_throughput_mbps(self) -> float:
        elapsed = max(time.perf_counter() - self.start_time, 0.001)
        return self._total_bytes / elapsed / 1024 / 1024

    def get_ops_rate(self) -> float:
        return self.ops_counter.rate()

    async def _self_healing_monitor(self):
        while True:
            if self.error_logs:
                last = self.error_logs.pop(0)
                print(f"[自癒] 處理: {last[:80]}...")
            await asyncio.sleep(5)

    async def _demo_traffic(self):
        """模擬背景流量 (demo 用)；降低頻率以減輕 CPU"""
        while True:
            self.ops_counter.hit(1)
            self._total_bytes += random.randint(100, 5000)
            await asyncio.sleep(0.5)

    async def render_loop(self):
        RENDER_INTERVAL = 2.0
        while True:
            if os.name == "nt":
                os.system("cls")
            else:
                os.system("clear")
            elapsed = time.perf_counter() - self.start_time
            print("=" * 50)
            print(" 【智慧戰情看板】 - 民雄監控節點")
            print("=" * 50)
            print(f" [當前節點] : {self.current_node}")
            print(f" [系統狀態] : {self.current_status}")
            print(f" [切換次數] : {self.switch_count}")
            print(f" [運行時間] : {elapsed:.1f}s")
            print(f" [吞吐量]   : {self.get_throughput_mbps():.2f} MB/s")
            print(f" [OPS 頻率] : {self.get_ops_rate():.1f} ops/s")
            ei = self.edge_info
            if ei:
                ollama = "已連線" if ei.get("ollama_ready") else "離線"
                print(f" [邊緣計算] : Ollama {ollama}" + (f" ({ei.get('ollama_latency_ms', 0):.0f}ms)" if ei.get("ollama_ready") else ""))
            if self.error_logs:
                print(f" [最近錯誤] : {self.error_logs[-1][:60]}...")
            print("=" * 50)
            print(" > 正在觀測異步流量數據...")
            print(" > 本地 AI 狀態: gemma3:4b (邊緣節點)")
            print("=" * 50)
            await asyncio.sleep(RENDER_INTERVAL)


db = None


async def main():
    global db
    db = MessengerDashboard()
    asyncio.create_task(db._demo_traffic())
    asyncio.create_task(db._self_healing_monitor())
    try:
        from messenger_probe import MessengerProbe
        probe = MessengerProbe(db)
        asyncio.create_task(probe.run_forever(interval=10))
    except ImportError:
        pass
    try:
        from proxy_switcher import ProxySwitcher
        switcher = ProxySwitcher(db=db)
        asyncio.create_task(switcher.maintenance_loop(interval=60))
    except ImportError:
        pass
    try:
        from edge_compute import get_edge
        edge = get_edge()
        def on_edge_status(info):
            db.edge_info = info
        asyncio.create_task(edge.run_edge_daemon(on_status=on_edge_status))
    except ImportError:
        pass
    await db.render_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[系統] 監控已終止。")

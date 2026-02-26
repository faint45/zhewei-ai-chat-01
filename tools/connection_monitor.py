import asyncio


class ConnectionMonitor:
    def __init__(self, check_interval: int = 60, max_retries: int = 3):
        self.state = "CONNECTED"
        self.retry_count = 0
        self.check_interval = check_interval
        self.max_retries = max_retries

    async def monitor_logic(self):
        while True:
            if self.state == "EXPIRED":
                success = await self.reconnect()
                if success:
                    self.retry_count = 0
                else:
                    self.retry_count += 1
                    if self.retry_count >= self.max_retries:
                        self.state = "FAILED"
                        break
            await asyncio.sleep(self.check_interval)

    async def reconnect(self) -> bool:
        print("連線已過期，執行重新連接...")
        try:
            await self._do_reconnect()
            self.state = "CONNECTED"
            return True
        except Exception as e:
            print(f"重連失敗: {e}")
            return False

    async def _do_reconnect(self):
        await asyncio.sleep(1)


if __name__ == "__main__":
    monitor = ConnectionMonitor(check_interval=2)
    monitor.state = "EXPIRED"
    try:
        asyncio.run(asyncio.wait_for(monitor.monitor_logic(), timeout=8))
    except asyncio.TimeoutError:
        print(f"監控結束，最終狀態: {monitor.state}")

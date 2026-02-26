"""
代理切換引擎 - 獨立行程，每分鐘校準連線節點
"""
import asyncio
from proxy_switcher import ProxySwitcher


async def main():
    switcher = ProxySwitcher()
    await switcher.maintenance_loop(interval=60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[系統] 代理切換引擎已終止。")

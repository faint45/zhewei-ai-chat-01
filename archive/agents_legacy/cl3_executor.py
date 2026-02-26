"""
CL3 執行器 - 授權確認後執行操作
"""
import asyncio
from typing import Any, Callable


class CL3Executor:
    def __init__(self, dashboard=None):
        self.db = dashboard

    async def request_permission(
        self,
        action_desc: str,
        task_fn: Callable[..., Any],
        *args,
        **kwargs,
    ) -> Any | None:
        print(f"\n[AI 請求操作許可]")
        print(f"  預計執行: {action_desc}")
        user_choice = input("  授權執行? (y/n): ").strip().lower()

        if user_choice != "y":
            print("  [已取消]")
            return None

        print("  [授權通過] 執行中...")
        try:
            if asyncio.iscoroutinefunction(task_fn):
                result = await task_fn(*args, **kwargs)
            else:
                result = task_fn(*args, **kwargs)
            if self.db:
                self.db.record(ops=1)
            print(f"  [成功] {result}")
            return result
        except Exception as e:
            if self.db:
                self.db.record(error=str(e))
            print(f"  [失敗] {e}")
            return None


async def example_task(name: str) -> str:
    return f"節點 {name} 配置完成"

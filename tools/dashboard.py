"""
戰情看板 - ASCII 表格 + 非同步吞吐量計數器
純 ASCII 字元 (-, |, +)，效能損耗最低
"""
import asyncio
import time
from collections import deque
from typing import List, Tuple


def draw_table(rows: List[List[str]], headers: List[str] = None) -> str:
    """
    使用 -, |, + 繪製 ASCII 表格
    """
    if headers:
        rows = [headers] + rows
    if not rows:
        return ""

    col_widths = [max(len(str(r[i]) if i < len(r) else "") for r in rows) for i in range(max(len(r) for r in rows))]
    lines = []

    def sep(char: str) -> str:
        return "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    def row(cells: List[str]) -> str:
        padded = [str(c).ljust(col_widths[i])[: col_widths[i]] for i, c in enumerate(cells + [""] * (len(col_widths) - len(cells)))]
        return "| " + " | ".join(padded[: len(col_widths)]) + " |"

    lines.append(sep("-"))
    for r in rows:
        lines.append(row(r))
        lines.append(sep("-"))
    return "\n".join(lines)


class ThroughputCounter:
    """
    無鎖吞吐量計數器 - 滑動視窗，rate 計算時清理，最小開銷
    """

    __slots__ = ("_times", "_window")

    def __init__(self, window_sec: float = 1.0):
        self._times: deque = deque(maxlen=10000)
        self._window = window_sec

    def hit(self, count: int = 1) -> None:
        t = time.perf_counter()
        for _ in range(count):
            self._times.append(t)

    def rate(self) -> float:
        now = time.perf_counter()
        cutoff = now - self._window
        while self._times and self._times[0] < cutoff:
            self._times.popleft()
        return len(self._times) / self._window if self._window > 0 else 0.0

    def total(self) -> int:
        return len(self._times)


class Dashboard:
    def __init__(self, counters: dict = None):
        self.counters = counters or {}

    def render(self) -> str:
        rows = []
        for name, counter in self.counters.items():
            rate = counter.rate() if hasattr(counter, "rate") else 0
            total = counter.total() if hasattr(counter, "total") else 0
            rows.append([name, f"{rate:.1f}/s", str(total)])
        return draw_table(rows, ["Metric", "Throughput", "Total"])


async def demo():
    tc = ThroughputCounter(window_sec=1.0)
    for _ in range(50):
        tc.hit()
        await asyncio.sleep(0.02)
    print(Dashboard({"Stream A": tc}).render())


if __name__ == "__main__":
    table = draw_table(
        [["Alpha", "100", "OK"], ["Beta", "200", "OK"], ["Gamma", "50", "WARN"]],
        ["Service", "Count", "Status"],
    )
    print(table)
    print()
    asyncio.run(demo())

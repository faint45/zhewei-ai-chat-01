#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json

import httpx
from mcp.server.fastmcp import FastMCP


SERVER_NAME = "osrm_route_mcp"
mcp = FastMCP(SERVER_NAME)

OSRM_BASE = "https://router.project-osrm.org"
USER_AGENT = "ZheweiTech-Jarvis-MCP/1.0 (contact: local)"


def _fmt_km(meters: float) -> float:
    return round(float(meters) / 1000.0, 3)


def _fmt_min(seconds: float) -> float:
    return round(float(seconds) / 60.0, 2)


@mcp.tool(
    name="osrm_route_eta",
    annotations={
        "title": "Get route distance and ETA via OSRM",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def osrm_route_eta(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    profile: str = "driving",
) -> str:
    """
    透過 OSRM 估算路線距離與時間（免費）。

    Args:
        start_lat: 起點緯度
        start_lon: 起點經度
        end_lat: 終點緯度
        end_lon: 終點經度
        profile: routing profile，預設 driving（可選 driving/walking/cycling）

    Returns:
        JSON 字串，含距離(公里)、時間(分鐘)與簡易摘要。
    """
    p = (profile or "driving").strip().lower()
    if p not in {"driving", "walking", "cycling"}:
        p = "driving"

    coords = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    url = f"{OSRM_BASE}/route/v1/{p}/{coords}"
    params = {
        "overview": "false",
        "alternatives": "false",
        "steps": "false",
    }
    headers = {"User-Agent": USER_AGENT}
    try:
        async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        routes = data.get("routes") or []
        if not routes:
            return json.dumps({"error": "查無可用路線"}, ensure_ascii=False)

        r0 = routes[0]
        dist_m = float(r0.get("distance", 0.0))
        dur_s = float(r0.get("duration", 0.0))
        out = {
            "profile": p,
            "distance_km": _fmt_km(dist_m),
            "duration_min": _fmt_min(dur_s),
            "summary": f"預估 {_fmt_km(dist_m)} 公里，約 {_fmt_min(dur_s)} 分鐘",
        }
        return json.dumps(out, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"OSRM 查詢失敗: {e}"}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()


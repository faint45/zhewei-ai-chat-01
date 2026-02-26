#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP


SERVER_NAME = "osm_geocode_mcp"
mcp = FastMCP(SERVER_NAME)

NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
USER_AGENT = "ZheweiTech-Jarvis-MCP/1.0 (contact: local)"


async def _get_json(url: str, params: dict) -> list | dict:
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


@mcp.tool(
    name="osm_geocode_search",
    annotations={
        "title": "Geocode address to coordinates via OSM Nominatim",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def osm_geocode_search(query: str, limit: int = 5) -> str:
    """
    使用 OSM Nominatim 進行地理編碼（地址 -> 座標）。

    Args:
        query: 地點文字，例如「嘉義縣民雄鄉」。
        limit: 回傳筆數，預設 5，最大 10。

    Returns:
        JSON 字串，含 display_name、lat、lon。
    """
    q = (query or "").strip()
    if not q:
        return json.dumps({"error": "query 不可為空"}, ensure_ascii=False)

    n = max(1, min(int(limit), 10))
    try:
        data = await _get_json(
            f"{NOMINATIM_BASE}/search",
            {
                "q": q,
                "format": "jsonv2",
                "limit": n,
                "addressdetails": 1,
            },
        )
        results = []
        for row in data if isinstance(data, list) else []:
            results.append(
                {
                    "display_name": row.get("display_name", ""),
                    "lat": row.get("lat", ""),
                    "lon": row.get("lon", ""),
                    "type": row.get("type", ""),
                    "class": row.get("class", ""),
                }
            )
        return json.dumps({"query": q, "count": len(results), "results": results}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Nominatim 查詢失敗: {e}"}, ensure_ascii=False)


@mcp.tool(
    name="osm_reverse_geocode",
    annotations={
        "title": "Reverse geocode coordinates via OSM Nominatim",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def osm_reverse_geocode(lat: float, lon: float) -> str:
    """
    使用 OSM Nominatim 反向地理編碼（座標 -> 地址）。

    Args:
        lat: 緯度
        lon: 經度

    Returns:
        JSON 字串，含 display_name 與 address 結構。
    """
    try:
        data = await _get_json(
            f"{NOMINATIM_BASE}/reverse",
            {
                "lat": lat,
                "lon": lon,
                "format": "jsonv2",
                "addressdetails": 1,
            },
        )
        out = {
            "lat": lat,
            "lon": lon,
            "display_name": data.get("display_name", "") if isinstance(data, dict) else "",
            "address": data.get("address", {}) if isinstance(data, dict) else {},
        }
        return json.dumps(out, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"反向地理編碼失敗: {e}"}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 Qdrant MCP Server
提供向量資料庫操作、語意搜尋功能
"""
import json
import os
from typing import Any

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except ImportError:
    QdrantClient = None

from mcp.server.fastmcp import FastMCP

SERVER_NAME = "qdrant_mcp"
mcp = FastMCP(SERVER_NAME)

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")


def _get_client() -> Any:
    if not QdrantClient:
        raise RuntimeError("qdrant-client 未安裝，請執行: pip install qdrant-client")
    return QdrantClient(url=QDRANT_URL)


@mcp.tool(
    name="qdrant_list_collections",
    annotations={
        "title": "List all Qdrant collections",
        "description": "列出所有向量集合",
    },
)
def qdrant_list_collections() -> str:
    try:
        client = _get_client()
        collections = client.get_collections()
        result = []
        for col in collections.collections:
            result.append({
                "name": col.name,
                "vectors_count": col.vectors_count if hasattr(col, 'vectors_count') else "N/A",
            })
        return json.dumps({"ok": True, "collections": result}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="qdrant_collection_info",
    annotations={
        "title": "Get Qdrant collection info",
        "description": "取得集合詳細資訊",
    },
)
def qdrant_collection_info(collection_name: str) -> str:
    try:
        client = _get_client()
        info = client.get_collection(collection_name)
        return json.dumps({
            "ok": True,
            "name": info.config.params.vectors.size if hasattr(info.config.params, 'vectors') else "N/A",
            "vectors_count": info.vectors_count if hasattr(info, 'vectors_count') else 0,
            "points_count": info.points_count if hasattr(info, 'points_count') else 0,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="qdrant_search",
    annotations={
        "title": "Search vectors in Qdrant",
        "description": "向量搜尋（需提供 query_vector）",
    },
)
def qdrant_search(collection_name: str, query_vector: list[float], top_k: int = 5) -> str:
    try:
        client = _get_client()
        results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
        )
        hits = []
        for r in results:
            hits.append({
                "id": r.id,
                "score": r.score,
                "payload": r.payload,
            })
        return json.dumps({"ok": True, "hits": hits}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool(
    name="qdrant_scroll",
    annotations={
        "title": "Scroll through Qdrant points",
        "description": "瀏覽集合中的點（分頁）",
    },
)
def qdrant_scroll(collection_name: str, limit: int = 10, offset: int = 0) -> str:
    try:
        client = _get_client()
        points, next_offset = client.scroll(
            collection_name=collection_name,
            limit=limit,
            offset=offset,
        )
        result = []
        for p in points:
            result.append({
                "id": p.id,
                "payload": p.payload,
            })
        return json.dumps({
            "ok": True,
            "points": result,
            "next_offset": next_offset,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()

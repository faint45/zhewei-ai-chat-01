#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import chromadb
from mcp.server.fastmcp import FastMCP


SERVER_NAME = "construction_law_mcp"
mcp = FastMCP(SERVER_NAME)


def _stable_embedding(text: str, dim: int = 64) -> list[float]:
    digest = hashlib.sha256((text or "").encode("utf-8", errors="ignore")).digest()
    return [((digest[i % len(digest)] / 255.0) * 2.0 - 1.0) for i in range(dim)]


def _resolve_db_path() -> str:
    configured = (os.environ.get("JARVIS_DB_PATH") or "").strip()
    if configured:
        return configured
    return str(Path(__file__).resolve().parents[1] / "Jarvis_Training" / "chroma_db")


DB_PATH = _resolve_db_path()
COLLECTION_NAME = (os.environ.get("JARVIS_COLLECTION") or "jarvis_training").strip()
client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(name=COLLECTION_NAME)


def _format_hits(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return "找不到相關法規內容。"
    lines = ["# Construction Law Search Result", ""]
    for idx, h in enumerate(hits, start=1):
        question = (h.get("question") or "").strip()
        source = (h.get("source") or "").strip() or "Unknown"
        content = (h.get("document") or "").strip()
        lines.append(f"## {idx}. 來源: {source}")
        if question:
            lines.append(f"- 問題: {question}")
        lines.append(f"- 內容: {content[:500]}")
        lines.append("")
    return "\n".join(lines).strip()


def _recall(query: str, top_k: int) -> list[dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    rs = collection.query(query_embeddings=[_stable_embedding(q)], n_results=max(1, min(top_k, 10)))
    ids = (rs.get("ids") or [[]])[0]
    docs = (rs.get("documents") or [[]])[0]
    metas = (rs.get("metadatas") or [[]])[0]
    out: list[dict[str, Any]] = []
    for i, rid in enumerate(ids):
        meta = metas[i] if i < len(metas) and isinstance(metas[i], dict) else {}
        out.append(
            {
                "id": rid,
                "document": docs[i] if i < len(docs) else "",
                "question": meta.get("question", ""),
                "source": meta.get("source", ""),
                "time": meta.get("time", ""),
            }
        )
    return out


@mcp.tool(
    name="construction_law_search",
    annotations={
        "title": "Search construction law knowledge base",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def construction_law_search(query: str, top_k: int = 5) -> str:
    """
    查詢台灣營建法規知識庫（ChromaDB）。

    Args:
        query: 自然語言問題，例如「限制性招標第22條風險」。
        top_k: 回傳筆數（1-10）。

    Returns:
        Markdown 格式的查詢結果。
    """
    try:
        hits = _recall(query=query, top_k=top_k)
        return _format_hits(hits)
    except Exception as e:
        return f"Error: 查詢失敗 - {e}"


@mcp.tool(
    name="construction_law_stats",
    annotations={
        "title": "Get construction law KB stats",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def construction_law_stats() -> str:
    """
    取得法規知識庫狀態。

    Returns:
        JSON 字串：db_path、collection、count。
    """
    try:
        payload = {
            "db_path": DB_PATH,
            "collection": COLLECTION_NAME,
            "count": collection.count(),
        }
        return json.dumps(payload, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()


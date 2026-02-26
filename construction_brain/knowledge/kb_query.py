# -*- coding: utf-8 -*-
"""
營建自動化大腦 — 知識庫查詢引擎
語意搜尋營建法規、合約條款、施工規範

複用：
  - Jarvis_Training/chroma_db: 現有 14,600+ 筆知識庫
  - ai_modules/reranker.py: 搜尋重排序
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger("construction_brain.kb_query")

CHROMADB_PATH = os.environ.get("CHROMADB_PATH", "")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11460").rstrip("/")
EMBED_MODEL = os.environ.get("CB_EMBED_MODEL", "nomic-embed-text")
COLLECTION_NAME = os.environ.get("CB_KB_COLLECTION", "construction_knowledge")
# 也搜尋主知識庫
MAIN_COLLECTION = os.environ.get("LEARNING_COLLECTION", "jarvis_training")


def _get_chroma_client():
    import chromadb
    if CHROMADB_PATH:
        return chromadb.PersistentClient(path=CHROMADB_PATH)
    default = str(Path(__file__).resolve().parent.parent.parent / "Jarvis_Training" / "chroma_db")
    return chromadb.PersistentClient(path=default)


def _embed_text(text: str) -> list:
    import urllib.request
    payload = {"model": EMBED_MODEL, "prompt": text}
    try:
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("embedding", [])
    except Exception as e:
        log.error(f"Embedding 失敗: {e}")
        return []


def query(question: str, n_results: int = 5, collection_name: str = "",
          category_filter: str = "") -> list:
    """
    語意搜尋知識庫

    Args:
        question: 查詢問題
        n_results: 回傳筆數
        collection_name: 指定 collection（空則搜尋全部）
        category_filter: 篩選分類（regulation/contract/spec）

    Returns:
        [{"id": str, "document": str, "metadata": dict, "distance": float}]
    """
    embedding = _embed_text(question)
    if not embedding:
        return []

    client = _get_chroma_client()
    collections_to_search = []

    if collection_name:
        collections_to_search.append(collection_name)
    else:
        # 搜尋營建知識庫 + 主知識庫
        collections_to_search = [COLLECTION_NAME, MAIN_COLLECTION]

    results = []
    for coll_name in collections_to_search:
        try:
            collection = client.get_collection(name=coll_name)
        except Exception:
            continue

        where_filter = None
        if category_filter:
            where_filter = {"category": category_filter}

        try:
            res = collection.query(
                query_embeddings=[embedding],
                n_results=min(n_results, 10),
                where=where_filter,
            )
        except Exception:
            # where filter 可能不支援，重試不帶 filter
            res = collection.query(
                query_embeddings=[embedding],
                n_results=min(n_results, 10),
            )

        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        for i in range(len(ids)):
            results.append({
                "id": ids[i],
                "document": docs[i] if i < len(docs) else "",
                "metadata": metas[i] if i < len(metas) else {},
                "distance": dists[i] if i < len(dists) else 999,
                "collection": coll_name,
            })

    # 按距離排序，取前 n
    results.sort(key=lambda x: x["distance"])
    return results[:n_results]


def query_with_context(question: str, n_results: int = 3) -> str:
    """
    查詢並組裝為 LLM 可用的上下文字串

    Returns: 格式化的參考資料文字
    """
    hits = query(question, n_results=n_results)
    if not hits:
        return ""

    lines = ["【參考資料】"]
    for i, hit in enumerate(hits, 1):
        source = hit["metadata"].get("source", "知識庫")
        category = hit["metadata"].get("category", "")
        doc = hit["document"][:500]  # 截斷過長
        label = f"{source}"
        if category:
            label += f" ({category})"
        lines.append(f"\n[{i}] {label}")
        lines.append(doc)
    return "\n".join(lines)


def search_regulations(keyword: str, n_results: int = 5) -> list:
    """搜尋營建法規"""
    return query(keyword, n_results=n_results, category_filter="regulation")


def search_contracts(keyword: str, n_results: int = 5) -> list:
    """搜尋合約條款"""
    return query(keyword, n_results=n_results, category_filter="contract")


def search_specs(keyword: str, n_results: int = 5) -> list:
    """搜尋施工規範"""
    return query(keyword, n_results=n_results, category_filter="spec")

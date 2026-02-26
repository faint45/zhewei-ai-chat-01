"""
築未科技大腦 - RAG 強化（Chroma + Ollama nomic-embed-text 語意向量）
統一使用 Jarvis Training 的 chroma_db / jarvis_training collection
"""
import hashlib
import os
import uuid
from pathlib import Path
from typing import Optional

import requests

# 統一指向 Jarvis Training 的 ChromaDB（14,600+ 筆知識）
_JARVIS_CHROMA_PATH = Path(__file__).resolve().parent.parent / "Jarvis_Training" / "chroma_db"
_COLLECTION_NAME = os.environ.get("LEARNING_COLLECTION", "jarvis_training").strip()
_EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text:latest").strip()
_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "").strip().rstrip("/")

_chroma_client = None


def _resolve_ollama_url() -> str:
    candidates = []
    if _OLLAMA_BASE_URL:
        candidates.append(_OLLAMA_BASE_URL)
    candidates.extend(["http://localhost:11460", "http://localhost:11434"])
    for base in candidates:
        try:
            r = requests.get(f"{base}/api/tags", timeout=2)
            if r.status_code == 200:
                return base
        except Exception:
            continue
    return candidates[0] if candidates else "http://localhost:11434"


def _ollama_embed(text: str) -> list[float]:
    """使用 Ollama nomic-embed-text 產生 768 維語意向量"""
    text = (text or "").strip()[:8000]
    if not text:
        return _fallback_embed(text)
    base = _resolve_ollama_url()
    try:
        r = requests.post(
            f"{base}/api/embed",
            json={"model": _EMBED_MODEL, "input": text},
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            embeddings = data.get("embeddings") or []
            if embeddings and len(embeddings[0]) > 0:
                return embeddings[0]
    except Exception:
        pass
    return _fallback_embed(text)


def _fallback_embed(text: str, dim: int = 768) -> list[float]:
    digest = hashlib.sha256((text or "").encode("utf-8", errors="ignore")).digest()
    return [((digest[i % len(digest)] / 255.0) * 2.0 - 1.0) for i in range(dim)]


def _ensure_chroma():
    global _chroma_client
    if _chroma_client is not None:
        return True
    try:
        import chromadb
        _JARVIS_CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(_JARVIS_CHROMA_PATH))
        return True
    except ImportError:
        return False


def _get_collection():
    if not _ensure_chroma():
        return None
    return _chroma_client.get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def add_to_chroma(text: str, source: str = "對話", doc_id: Optional[str] = None) -> bool:
    """將文字加入統一知識庫。"""
    coll = _get_collection()
    if coll is None:
        return False
    try:
        emb = _ollama_embed(text[:4000])
        coll.upsert(
            ids=[doc_id or str(uuid.uuid4())],
            embeddings=[emb],
            documents=[text[:4000]],
            metadatas=[{"source": source, "question": ""}],
        )
        return True
    except Exception:
        return False


def search_chroma(query: str, limit: int = 8) -> str:
    """以語義搜尋統一知識庫。"""
    coll = _get_collection()
    if coll is None:
        return ""
    try:
        q_emb = _ollama_embed(query)
        results = coll.query(query_embeddings=[q_emb], n_results=limit)
        if not results or not results.get("documents") or not results["documents"][0]:
            return ""
        docs = results["documents"][0]
        metas = (results.get("metadatas") or [[]])[0]
        dists = (results.get("distances") or [[]])[0]
        parts = []
        for i, doc in enumerate(docs[:limit]):
            meta = metas[i] if i < len(metas) else {}
            dist = dists[i] if i < len(dists) else 1.0
            q = meta.get("question", "")
            src = meta.get("source", "")
            sim = f"{1-dist:.2f}" if dist is not None else "?"
            header = f"[{src}] {q}" if q else f"[{src}]"
            parts.append(f"({sim}) {header}\n{doc[:500]}")
        return "【向量知識】\n" + "\n\n---\n\n".join(parts)
    except Exception:
        return ""


def sync_from_brain_knowledge() -> int:
    """將 brain_knowledge.ndjson 現有內容同步至統一知識庫。"""
    coll = _get_collection()
    if coll is None:
        return 0
    try:
        from brain_knowledge import _load
        entries = _load()
        count = 0
        for i, e in enumerate(entries):
            txt = e.get("text", "")
            if txt:
                add_to_chroma(txt, source=e.get("source", "同步"), doc_id=f"bk_{i}")
                count += 1
        return count
    except Exception:
        return 0


def is_available() -> bool:
    """是否已安裝並可用。"""
    return _ensure_chroma()

# -*- coding: utf-8 -*-
"""
營建自動化大腦 — 知識庫匯入引擎
將營建法規、合約、規範文件匯入 ChromaDB 向量資料庫

複用：
  - kb_snapshot.py: ChromaDB 匯出/匯入
  - ai_modules/smart_chunker.py: 智慧分段
  - Jarvis_Training/chroma_db: 現有 14,600+ 筆知識庫
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger("construction_brain.kb_ingest")

CHROMADB_PATH = os.environ.get("CHROMADB_PATH", "")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11460").rstrip("/")
EMBED_MODEL = os.environ.get("CB_EMBED_MODEL", "nomic-embed-text")
COLLECTION_NAME = os.environ.get("CB_KB_COLLECTION", "construction_knowledge")


def _get_chroma_client():
    """取得 ChromaDB 客戶端"""
    import chromadb
    if CHROMADB_PATH:
        return chromadb.PersistentClient(path=CHROMADB_PATH)
    # 預設路徑
    default = str(Path(__file__).resolve().parent.parent.parent / "Jarvis_Training" / "chroma_db")
    return chromadb.PersistentClient(path=default)


def _embed_text(text: str) -> list:
    """透過 Ollama nomic-embed-text 取得 embedding"""
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


def ingest_text(text: str, metadata: dict = None, doc_id: str = "") -> bool:
    """
    單筆文字匯入知識庫

    Args:
        text: 文件內容
        metadata: 附加 metadata（source, category, date 等）
        doc_id: 文件 ID（若空則自動生成）
    """
    if not text.strip():
        return False

    client = _get_chroma_client()
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    embedding = _embed_text(text)
    if not embedding:
        log.error("無法取得 embedding，跳過匯入")
        return False

    if not doc_id:
        import hashlib
        doc_id = hashlib.md5(text.encode()).hexdigest()[:16]

    meta = metadata or {}
    meta.setdefault("source", "construction_brain")
    meta.setdefault("ingested_at", datetime.now().isoformat())

    collection.upsert(
        ids=[doc_id],
        documents=[text],
        embeddings=[embedding],
        metadatas=[meta],
    )
    log.info(f"已匯入: {doc_id} ({len(text)} chars)")
    return True


def ingest_file(file_path: str, category: str = "regulation", chunk_size: int = 1000) -> int:
    """
    檔案匯入知識庫（自動分段）

    Args:
        file_path: 檔案路徑（.txt, .md, .json）
        category: 分類（regulation/contract/spec/manual）
        chunk_size: 分段字數

    Returns: 匯入筆數
    """
    path = Path(file_path)
    if not path.exists():
        log.error(f"檔案不存在: {file_path}")
        return 0

    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return 0

    # 簡易分段
    chunks = _split_text(text, chunk_size)
    count = 0
    for i, chunk in enumerate(chunks):
        doc_id = f"{path.stem}_{i:04d}"
        meta = {
            "source": path.name,
            "category": category,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        if ingest_text(chunk, metadata=meta, doc_id=doc_id):
            count += 1

    log.info(f"檔案匯入完成: {path.name} → {count}/{len(chunks)} 段")
    return count


def ingest_directory(dir_path: str, category: str = "regulation", extensions: list = None) -> int:
    """
    批次匯入目錄下所有檔案

    Args:
        dir_path: 目錄路徑
        category: 分類
        extensions: 副檔名過濾（預設 .txt, .md）
    """
    exts = extensions or [".txt", ".md", ".json"]
    total = 0
    for f in Path(dir_path).rglob("*"):
        if f.suffix.lower() in exts and f.is_file():
            total += ingest_file(str(f), category=category)
    return total


def get_collection_stats() -> dict:
    """取得知識庫統計"""
    try:
        client = _get_chroma_client()
        collection = client.get_or_create_collection(name=COLLECTION_NAME)
        return {
            "collection": COLLECTION_NAME,
            "count": collection.count(),
            "chromadb_path": CHROMADB_PATH or "default",
        }
    except Exception as e:
        return {"error": str(e)}


def _split_text(text: str, chunk_size: int = 1000) -> list:
    """簡易分段：按段落優先，超長則硬切"""
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > chunk_size and current:
            chunks.append(current.strip())
            current = para
        else:
            current = current + "\n\n" + para if current else para
    if current.strip():
        chunks.append(current.strip())
    # 硬切過長段
    final = []
    for chunk in chunks:
        while len(chunk) > chunk_size * 1.5:
            final.append(chunk[:chunk_size])
            chunk = chunk[chunk_size:]
        final.append(chunk)
    return final

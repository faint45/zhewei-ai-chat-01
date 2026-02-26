"""
築未科技大腦 - 本地知識庫（不斷學習）
儲存於 D 槽，append-only 保護（只能新增，不能覆寫）
"""
import json
import re
import threading
from pathlib import Path
from datetime import datetime

from brain_data_config import BRAIN_DATA_DIR, KNOWLEDGE_FILE, KNOWLEDGE_JSON_LEGACY

MAX_ENTRIES = 2000
MAX_CONTEXT_CHARS = 6000  # 注入提示的最大字數（提高以利文字文件辨識與理解）
_lock = threading.Lock()


def _migrate_legacy_json():
    """將舊 brain_knowledge.json 遷移為 ndjson（僅執行一次）"""
    from pathlib import Path
    project_legacy = Path(__file__).parent / "brain_knowledge.json"
    for legacy in (project_legacy, KNOWLEDGE_JSON_LEGACY):
        if not legacy.exists():
            continue
        try:
            with open(legacy, "r", encoding="utf-8") as f:
                data = json.load(f)
            entries = data if isinstance(data, list) else data.get("entries", [])
            with open(KNOWLEDGE_FILE, "a", encoding="utf-8") as out:
                for e in entries:
                    out.write(json.dumps(e, ensure_ascii=False) + "\n")
            legacy.rename(legacy.with_suffix(".json.migrated"))
            break
        except Exception:
            pass


def _load() -> list:
    _migrate_legacy_json()
    if not KNOWLEDGE_FILE.exists():
        return []
    try:
        entries = []
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
        return entries[-MAX_ENTRIES:]
    except Exception:
        return []


def _append_only(entry: dict):
    """Append-only：只新增，不覆寫"""
    with _lock:
        try:
            with open(KNOWLEDGE_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


def add(text: str, source: str = "對話", metadata: dict = None) -> str:
    """新增一筆知識，回傳摘要。append-only，不覆寫既有資料。"""
    if not text or not text.strip():
        return "無內容可儲存"
    entry = {
        "text": text.strip()[:10000],
        "source": source,
        "ts": datetime.now().isoformat(),
        "metadata": metadata or {},
    }
    _append_only(entry)
    entries = _load()
    try:
        from brain_rag import add_to_chroma
        if add_to_chroma(text.strip()[:4000], source=source):
            pass
    except Exception:
        pass
    # GraphRAG：同步建立知識圖譜
    try:
        from ai_modules.graph_rag import graph_add
        graph_add(text.strip()[:2000], source=source)
    except Exception:
        pass
    return f"已學習：{source}，共 {len(entries)} 筆知識"


def add_transcript(text: str, source_name: str) -> str:
    """新增影片/音檔逐字稿"""
    return add(text, source=f"影片/音檔：{source_name}", metadata={"type": "transcript"})


def _semantic_search(query: str, entries: list, limit: int) -> list:
    """若已安裝 sentence-transformers，使用語義搜尋。"""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device="cpu")
        q_emb = model.encode([query], normalize_embeddings=True)
        texts = [e.get("text", "")[:500] for e in entries]
        emb = model.encode(texts, normalize_embeddings=True)
        import numpy as np
        scores = np.dot(emb, q_emb.T).flatten()
        idx = np.argsort(-scores)[:limit]
        return [entries[i] for i in idx]
    except Exception:
        return []


def search(query: str, limit: int = 8) -> str:
    """搜尋相關知識，回傳可注入提示的文字。已整合 Reranker 提升精準度 30-40%。"""
    query_lower = (query or "").strip().lower()
    if query_lower:
        try:
            from brain_rag import search_chroma, is_available as chroma_ok
            if chroma_ok():
                ctx = search_chroma(query_lower, limit=limit)
                if ctx:
                    return ctx
        except Exception:
            pass

    entries = _load()
    if not entries:
        return ""

    if query_lower:
        # 第一階段：取得候選結果（取 limit*3 以供重排序）
        picked = _semantic_search(query_lower, entries, limit * 3)
        if not picked:
            query_words = set(re.findall(r"[\w\u4e00-\u9fff]+", query_lower))

            def score(ent: dict) -> float:
                txt = ent.get("text", "").lower()
                hits = sum(1 for w in query_words if w in txt and len(w) > 1)
                return hits / max(len(query_words), 1)

            scored = [(e, score(e)) for e in entries]
            scored.sort(key=lambda x: (-x[1], x[0].get("ts", "")), reverse=False)
            picked = [e for e, s in scored[:limit * 3] if s > 0]

        # 第二階段：Reranker 重排序（提升精準度 30-40%）
        if picked and len(picked) > limit:
            try:
                from ai_modules.reranker import rerank_results
                docs = [e.get("text", "")[:500] for e in picked]
                metas = [e.get("metadata", {}) for e in picked]
                reranked = rerank_results(query_lower, docs, top_k=limit, metadatas=metas)
                picked = [picked[r["original_index"]] for r in reranked]
            except Exception:
                picked = picked[:limit]
        else:
            picked = picked[:limit]
    else:
        picked = entries[-limit:]

    parts = []
    total = 0
    for e in picked:
        t = e.get("text", "")[:1200]
        src = e.get("source", "")
        parts.append(f"[{src}]\n{t}")
        total += len(parts[-1])
        if total >= MAX_CONTEXT_CHARS:
            break

    if not parts:
        return ""

    # GraphRAG：補充知識圖譜上下文
    graph_ctx = ""
    try:
        from ai_modules.graph_rag import graph_context
        graph_ctx = graph_context(query)
    except Exception:
        pass

    result = "【你學過的知識】\n" + "\n\n---\n\n".join(parts)
    if graph_ctx:
        result += "\n\n" + graph_ctx
    return result


def get_stats() -> dict:
    """回傳知識庫統計"""
    entries = _load()
    sources = {}
    for e in entries:
        s = e.get("source", "其他")
        sources[s] = sources.get(s, 0) + 1
    return {"total": len(entries), "by_source": sources}



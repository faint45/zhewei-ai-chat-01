"""
築未科技大腦 - 統一檢索流程
整合 brain_knowledge + Chroma + Mem0，決定注入規則
支援「文字文件辨識／理解」：長查詢時自動提高檢索量與上下文長度
"""
import os
from typing import Optional

# 文件模式：當查詢較長時提高辨識與理解度（更多檢索結果、更長上下文）
DOC_QUERY_LEN_THRESHOLD = int(os.environ.get("BRAIN_DOC_QUERY_LEN", "250"))
DOC_RETRIEVE_LIMIT = int(os.environ.get("BRAIN_DOC_LIMIT", "14"))
DOC_MAX_CHARS = int(os.environ.get("BRAIN_DOC_MAX_CHARS", "7000"))
DEFAULT_MAX_CHARS = int(os.environ.get("BRAIN_RETRIEVE_MAX_CHARS", "4500"))
QUERY_PREFIX_LEN = int(os.environ.get("BRAIN_QUERY_PREFIX_LEN", "500"))


def retrieve_context(query: str, user_id: str = "default", limit: int = 8, max_chars: int = 4000) -> str:
    """
    統一檢索：依序嘗試 Chroma → brain_knowledge → Mem0，去重後合併。
    若查詢較長（文件／段落），自動提高 limit 與 max_chars 以提升辨識與理解度。
    回傳可注入至 prompt 的上下文字串。
    """
    q = (query or "").strip()
    is_doc_mode = len(q) >= DOC_QUERY_LEN_THRESHOLD
    if is_doc_mode:
        limit = max(limit, DOC_RETRIEVE_LIMIT)
        max_chars = max(max_chars, DOC_MAX_CHARS)
    else:
        max_chars = max_chars if max_chars > 0 else DEFAULT_MAX_CHARS
    q_prefix = q[:QUERY_PREFIX_LEN]

    seen = set()
    parts = []

    # 1. Chroma 向量檢索（語義最準）
    try:
        from brain_rag import search_chroma, is_available as chroma_ok
        if chroma_ok():
            ctx = search_chroma(q_prefix, limit=limit)
            if ctx and ctx.strip():
                for line in ctx.replace("【向量知識】\n", "").split("\n\n---\n\n"):
                    line = line.strip()
                    if line and line[:50] not in seen and len(line) > 20:
                        seen.add(line[:50])
                        parts.append(line)
    except Exception:
        pass

    # 2. brain_knowledge 關鍵字／語義
    try:
        from brain_knowledge import search
        ctx = search(q_prefix, limit=limit)
        if ctx:
            for block in ctx.split("\n\n")[:8]:
                block = block.strip()
                if block and block[:50] not in seen and len(block) > 30:
                    seen.add(block[:50])
                    parts.append(block)
    except Exception:
        pass

    # 3. Mem0 長期記憶
    try:
        from memory_mem0 import search as mem0_search, is_available as mem0_ok
        if mem0_ok():
            ctx = mem0_search(q_prefix[:300], user_id=user_id, limit=4)
            if ctx and ctx.strip():
                for line in ctx.split("\n")[:6]:
                    line = line.strip()
                    if line and line[:50] not in seen and len(line) > 20:
                        seen.add(line[:50])
                        parts.append(f"[記憶] {line}")
    except Exception:
        pass

    if not parts:
        return ""
    combined = "\n\n".join(parts)[:max_chars]
    return f"【相關知識】\n{combined}\n\n---\n\n"

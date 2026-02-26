"""
築未科技大腦 - 長期記憶（Mem0 整合）
當 pip install mem0ai 後啟用，記住使用者偏好與專案脈絡
Mem0 API: add(messages, user_id), search(query, filters={"user_id": ...})
"""
from typing import Optional

_MEM0_AVAILABLE = False
_memory = None


def _ensure_mem0():
    global _MEM0_AVAILABLE, _memory
    if _memory is not None:
        return _MEM0_AVAILABLE
    try:
        from mem0 import Memory
        _memory = Memory()
        _MEM0_AVAILABLE = True
    except ImportError:
        _MEM0_AVAILABLE = False
    return _MEM0_AVAILABLE


def add(user_id: str, text: str, metadata: Optional[dict] = None) -> bool:
    """新增一筆長期記憶。user_id 可為 'default' 表示全域。"""
    if not _ensure_mem0():
        return False
    try:
        messages = [{"role": "assistant", "content": text[:2000]}]
        _memory.add(messages, user_id=user_id)
        return True
    except Exception:
        return False


def search(query: str, user_id: str = "default", limit: int = 5) -> str:
    """搜尋長期記憶，回傳相關內容。"""
    if not _ensure_mem0():
        return ""
    try:
        results = _memory.search(query, filters={"user_id": user_id})
        if not results or not results.get("results"):
            return ""
        texts = [r.get("memory", r.get("text", "")) for r in results["results"][:limit]]
        return "\n".join(t for t in texts if t)
    except Exception:
        return ""


def get_all(user_id: str = "default", limit: int = 20) -> str:
    """取得使用者所有記憶（最近 N 筆）。"""
    if not _ensure_mem0():
        return ""
    try:
        results = _memory.get_all(filters={"user_id": user_id})
        if not results or not results.get("results"):
            return ""
        items = results["results"][:limit]
        texts = [r.get("memory", r.get("text", str(r))) for r in items]
        return "\n".join(t for t in texts if t)
    except Exception:
        return ""


def is_available() -> bool:
    """是否已安裝並可用。"""
    return _ensure_mem0()

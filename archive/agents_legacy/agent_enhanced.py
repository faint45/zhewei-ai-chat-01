"""
築未科技大腦 - 強化 Agent（整合 Mem0、Chroma、LangGraph 可選）
當 requirements-agent-enhancements.txt 安裝後啟用
"""
import asyncio
from typing import Callable, Optional


def _inject_enhanced_context(user_prompt: str, user_id: str = "default") -> str:
    """注入 Mem0 長期記憶與 Chroma RAG 內容。"""
    parts = []
    # Mem0 長期記憶
    try:
        from memory_mem0 import search as mem0_search, is_available as mem0_ok
        if mem0_ok():
            ctx = mem0_search(user_prompt[:200], user_id=user_id, limit=3)
            if ctx:
                parts.append("【長期記憶】\n" + ctx[:800])
    except Exception:
        pass
    # Chroma 向量知識
    try:
        from brain_rag import search_chroma, is_available as chroma_ok
        if chroma_ok():
            ctx = search_chroma(user_prompt[:200], limit=4)
            if ctx:
                parts.append(ctx[:1200])
    except Exception:
        pass
    if not parts:
        return user_prompt
    return "\n\n---\n\n".join(parts) + "\n\n---\n\n用戶：" + user_prompt


def _run_agent_base(user_prompt: str, on_step: Optional[Callable] = None, user_id: str = "default") -> tuple[str, str]:
    """注入強化 context 後呼叫原始 agent，避免遞迴。"""
    from agent import run_agent_sync
    enhanced_prompt = _inject_enhanced_context(user_prompt, user_id)
    return run_agent_sync(enhanced_prompt, on_step, user_id, _skip_enhanced=True)


async def run_agent(
    user_prompt: str,
    on_step: Optional[Callable[[str, str], None]] = None,
    user_id: str = "default",
) -> tuple[str, str]:
    """
    強化版 Agent：注入 Mem0 + Chroma 後執行。
    回傳 (最終回答, 使用的 AI 提供者)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: _run_agent_base(user_prompt, on_step, user_id),
    )


def run_agent_sync(
    user_prompt: str,
    on_step: Optional[Callable] = None,
    user_id: str = "default",
) -> tuple[str, str]:
    """強化版 Agent（同步）。"""
    return _run_agent_base(user_prompt, on_step, user_id)


def is_enhanced() -> bool:
    """是否啟用強化功能（Mem0 或 Chroma 至少其一）。"""
    try:
        from memory_mem0 import is_available as mem0_ok
        if mem0_ok():
            return True
    except Exception:
        pass
    try:
        from brain_rag import is_available as chroma_ok
        if chroma_ok():
            return True
    except Exception:
        pass
    return False

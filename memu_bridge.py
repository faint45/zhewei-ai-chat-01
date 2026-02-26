# -*- coding: utf-8 -*-
"""
築未科技 — memU Bridge：本地 AI 記憶引擎
────────────────────────────────────────
將 NevaMind-AI/memU 的 proactive memory 框架
整合到 Jarvis，使用 Ollama 本地模型作為 LLM + Embedding。

功能：
1. 24/7 持久記憶（分層：個人/偏好/知識/工作/目標）
2. 語意搜尋（向量 + bruteforce in-memory）
3. 自動分類 + 模式偵測
4. Proactive 上下文預測
5. 完全本地化，零雲端成本

用法：
    from memu_bridge import get_memu_service, memorize, retrieve
    svc = get_memu_service()
    await memorize(svc, "使用者偏好深色模式", user_id="allen")
    results = await retrieve(svc, "使用者的 UI 偏好", user_id="allen")
"""

import asyncio
import logging
import os
import sys
import types
from pathlib import Path

logger = logging.getLogger(__name__)

# ── memU source path injection ──────────────────────────────
MEMU_SRC = Path(__file__).resolve().parent / "memU" / "src"

def _bootstrap_memu():
    """
    把 memU/src 加入 sys.path，並 mock 掉 Rust _core 模組
    （lib.rs 只有一個 hello_from_bin 佔位函數，不影響核心功能）
    """
    src_str = str(MEMU_SRC)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

    # Mock the Rust _core module so import memu works without maturin build
    if "memu._core" not in sys.modules:
        fake_core = types.ModuleType("memu._core")
        fake_core.hello_from_bin = lambda: "Hello from memu (Python bridge)!"
        sys.modules["memu._core"] = fake_core

    # Also mock lazyllm to avoid import errors (we only use 'sdk' backend)
    if "lazyllm" not in sys.modules:
        fake_lazyllm = types.ModuleType("lazyllm")
        sys.modules["lazyllm"] = fake_lazyllm


_bootstrap_memu()

# Now we can safely import memU
from memu.app.service import MemoryService  # noqa: E402

# ── Ollama 配置 ─────────────────────────────────────────────
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11460").rstrip("/")
MEMU_CHAT_MODEL = os.environ.get("MEMU_CHAT_MODEL", "qwen3:8b")
MEMU_EMBED_MODEL = os.environ.get("MEMU_EMBED_MODEL", "nomic-embed-text:latest")

# 記憶分類（中文化，針對築未科技場景）
ZHEWEI_CATEGORIES = [
    {"name": "personal_info", "description": "使用者的個人基本資料（姓名、職稱、公司等）"},
    {"name": "preferences", "description": "使用者的偏好設定（UI、語言、回覆風格、常用工具）"},
    {"name": "relationships", "description": "人際關係與合作夥伴資訊"},
    {"name": "knowledge", "description": "技術知識、領域專長、學到的事實"},
    {"name": "work_projects", "description": "工作專案、營建案場、進度追蹤"},
    {"name": "goals", "description": "目標、計畫、待辦事項"},
    {"name": "experiences", "description": "過去的操作經驗、錯誤記錄、最佳做法"},
    {"name": "opinions", "description": "觀點、決策傾向、管理風格"},
    {"name": "habits", "description": "日常習慣、工作模式、排程偏好"},
    {"name": "system_context", "description": "系統狀態、設定變更、部署記錄"},
]


# ── Service singleton ───────────────────────────────────────
_service: MemoryService | None = None


def get_memu_service() -> MemoryService:
    """取得 memU MemoryService 單例（Ollama 本地模式）"""
    global _service
    if _service is not None:
        return _service

    ollama_v1 = f"{OLLAMA_BASE_URL}/v1"

    _service = MemoryService(
        llm_profiles={
            "default": {
                "base_url": ollama_v1,
                "api_key": "ollama",  # Ollama 不需要 key，但 SDK 要求非空
                "chat_model": MEMU_CHAT_MODEL,
                "embed_model": MEMU_EMBED_MODEL,
                "client_backend": "sdk",
            },
            "embedding": {
                "base_url": ollama_v1,
                "api_key": "ollama",
                "chat_model": MEMU_CHAT_MODEL,
                "embed_model": MEMU_EMBED_MODEL,
                "client_backend": "sdk",
            },
        },
        database_config={
            "metadata_store": {"provider": "inmemory"},
            # bruteforce = in-memory vector search，不需要 PostgreSQL
        },
        memorize_config={
            "memory_categories": ZHEWEI_CATEGORIES,
        },
        blob_config={
            "resources_dir": str(Path(__file__).resolve().parent / "brain_workspace" / "memu_data"),
        },
    )

    logger.info(
        "✅ memU MemoryService 初始化成功 (LLM=%s, Embed=%s, Ollama=%s)",
        MEMU_CHAT_MODEL, MEMU_EMBED_MODEL, OLLAMA_BASE_URL,
    )
    return _service


# ── 便捷函數 ────────────────────────────────────────────────

async def memorize(
    service: MemoryService | None = None,
    content: str = "",
    *,
    user_id: str = "default",
    source: str = "jarvis",
) -> dict:
    """將內容寫入 memU 記憶（自動分類 + 向量化）"""
    svc = service or get_memu_service()
    try:
        result = await svc.memorize(
            content=content,
            user_id=user_id,
            metadata={"source": source},
        )
        return {"ok": True, "result": result}
    except Exception as e:
        logger.error("memU memorize 失敗: %s", e)
        return {"ok": False, "error": str(e)}


async def retrieve(
    service: MemoryService | None = None,
    query: str = "",
    *,
    user_id: str = "default",
    top_k: int = 5,
) -> dict:
    """從 memU 記憶中檢索相關內容"""
    svc = service or get_memu_service()
    try:
        result = await svc.retrieve(
            query=query,
            user_id=user_id,
        )
        return {"ok": True, "result": result}
    except Exception as e:
        logger.error("memU retrieve 失敗: %s", e)
        return {"ok": False, "error": str(e)}


# ── 與既有 agent_memory.py 的相容層 ─────────────────────────

class MemUAgentMemory:
    """
    memU 驅動的 Agent 記憶，API 相容舊版 AgentMemory。
    同時保留 JSONL fallback（離線/錯誤時降級）。
    """

    def __init__(self, agent_id: str = "default"):
        self.agent_id = agent_id
        self._service = get_memu_service()
        # 保留舊版 fallback
        from agent_memory import AgentMemory as _LegacyMemory
        self._legacy = _LegacyMemory(agent_id)

    def store_interaction(self, user_input: str, ai_response: str,
                          session_id: str = None, metadata: dict = None):
        """儲存互動到 memU + legacy fallback"""
        # 同步版：在背景 memorize
        content = f"[User] {user_input}\n[AI] {ai_response}"
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(memorize(
                    self._service, content,
                    user_id=self.agent_id,
                    source=session_id or "chat",
                ))
            else:
                asyncio.run(memorize(
                    self._service, content,
                    user_id=self.agent_id,
                    source=session_id or "chat",
                ))
        except Exception as e:
            logger.warning("memU store fallback to legacy: %s", e)
        # 總是寫 legacy（備援）
        self._legacy.store_interaction(user_input, ai_response, session_id, metadata)

    def search_memory(self, query: str, limit: int = 5) -> list[dict]:
        """語意搜尋（memU 向量搜尋 + legacy fallback）"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 已在 async context 中，不能 asyncio.run
                # 返回 legacy 結果，memU 搜尋在 async API 中使用
                return self._legacy.search_memory(query, limit)
            else:
                result = asyncio.run(retrieve(self._service, query, user_id=self.agent_id))
                if result.get("ok") and result.get("result"):
                    return [{"memU": True, "data": result["result"]}]
        except Exception as e:
            logger.warning("memU search fallback to legacy: %s", e)
        return self._legacy.search_memory(query, limit)

    def get_recent_context(self, limit: int = 10) -> list[dict]:
        return self._legacy.get_recent_context(limit)

    def get_context_summary(self) -> str:
        return self._legacy.get_context_summary()

    def get_user_preferences(self) -> dict:
        return self._legacy.get_user_preferences()

    def update_user_preference(self, key: str, value):
        self._legacy.update_user_preference(key, value)

    def clear_session(self, session_id: str = None):
        self._legacy.clear_session(session_id)


def get_memu_agent_memory(agent_id: str = "default") -> MemUAgentMemory:
    """取得 memU 驅動的 Agent 記憶（相容舊版 API）"""
    return MemUAgentMemory(agent_id)


# ── CLI 測試 ────────────────────────────────────────────────
if __name__ == "__main__":
    async def _test():
        print("=== memU Bridge 測試 ===")
        svc = get_memu_service()
        print(f"✅ Service 初始化完成")

        print("\n--- memorize ---")
        r1 = await memorize(svc, "使用者 Allen 是築未科技的負責人，偏好深色主題，常用 Python 和 FastAPI", user_id="allen")
        print(f"memorize: {r1}")

        print("\n--- retrieve ---")
        r2 = await retrieve(svc, "使用者偏好什麼主題？", user_id="allen")
        print(f"retrieve: {r2}")

        print("\n--- MemUAgentMemory 相容層 ---")
        mem = get_memu_agent_memory("jarvis")
        mem.store_interaction("你好", "你好！我是 Jarvis。")
        results = mem.search_memory("Jarvis")
        print(f"search: {results}")

    asyncio.run(_test())

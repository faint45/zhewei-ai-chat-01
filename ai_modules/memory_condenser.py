# -*- coding: utf-8 -*-
"""
築未科技 — Memory Condenser 記憶壓縮
借鑑 OpenHands Memory Condenser，context window 快滿時自動壓縮歷史

策略：
1. 保留最近 N 輪完整對話
2. 舊的對話區塊用 LLM 摘要壓縮
3. 系統訊息永遠保留
4. 用戶明確的任務指令保留

用法：
    from ai_modules.memory_condenser import MemoryCondenser

    condenser = MemoryCondenser(max_tokens=28000)
    compressed = condenser.condense(messages)
"""
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

log = logging.getLogger("ai_modules.memory_condenser")


@dataclass
class CondenserConfig:
    """壓縮器配置"""
    max_context_tokens: int = 28000       # context window 上限
    keep_recent_turns: int = 6            # 保留最近 N 輪（user+assistant = 1 輪）
    keep_system: bool = True              # 永遠保留 system 訊息
    summary_max_tokens: int = 300         # 每個摘要的最大 token 數
    min_chunk_size: int = 3               # 最小壓縮區塊大小（訊息數）
    summary_model: str = ""               # 摘要用的模型（空 = 用預設）
    estimate_ratio: float = 3.5           # 中文字元 → token 估算比率


class MemoryCondenser:
    """
    對話記憶壓縮器

    當 messages 的 token 數接近上限時，自動壓縮舊的對話歷史：
    1. 系統訊息永遠保留
    2. 最近 N 輪對話完整保留
    3. 更舊的對話分塊，用 LLM 生成摘要替換
    4. 摘要訊息標記為 [condensed]
    """

    SUMMARY_PROMPT = """你是一個對話歷史壓縮助手。請將以下對話片段壓縮成一段簡潔的摘要。
保留：
- 用戶的核心需求和指令
- 重要的技術決策和結論
- 產生的程式碼檔案路徑
- 數字、設定值等關鍵數據

去除：
- 寒暄和確認語句
- 重複的解釋
- 中間過程的細節

回覆格式：直接輸出摘要文字，不要前綴或格式標記。限制在 200 字以內。

對話片段：
{chunk}"""

    def __init__(self, max_tokens: int = 0, config: CondenserConfig = None):
        self.config = config or CondenserConfig()
        if max_tokens > 0:
            self.config.max_context_tokens = max_tokens

    def condense(self, messages: List[Dict], force: bool = False) -> List[Dict]:
        """
        壓縮對話歷史

        Args:
            messages: OpenAI 格式的 messages list
            force: 強制壓縮（即使未超限）

        Returns:
            壓縮後的 messages list
        """
        if not messages:
            return messages

        total_tokens = self._estimate_tokens(messages)

        # 未超限且不強制 → 直接返回
        if not force and total_tokens < self.config.max_context_tokens * 0.85:
            return messages

        log.info(f"記憶壓縮啟動: {total_tokens} tokens (上限 {self.config.max_context_tokens})")

        # 分離 system 和對話訊息
        system_msgs = []
        conversation = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msgs.append(msg)
            else:
                conversation.append(msg)

        if not conversation:
            return messages

        # 分離：保留最近 N 輪 + 舊的需壓縮
        recent, old = self._split_recent(conversation)

        if len(old) < self.config.min_chunk_size:
            # 太少不值得壓縮
            return messages

        # 將舊對話分塊壓縮
        chunks = self._chunk_messages(old)
        summaries = []

        for chunk in chunks:
            summary_text = self._summarize_chunk(chunk)
            if summary_text:
                summaries.append({
                    "role": "assistant",
                    "content": f"[歷史摘要] {summary_text}",
                })

        # 組合結果
        result = system_msgs + summaries + recent

        new_tokens = self._estimate_tokens(result)
        saved = total_tokens - new_tokens
        log.info(f"記憶壓縮完成: {total_tokens} → {new_tokens} tokens (節省 {saved})")

        return result

    def should_condense(self, messages: List[Dict]) -> bool:
        """檢查是否需要壓縮"""
        total_tokens = self._estimate_tokens(messages)
        return total_tokens >= self.config.max_context_tokens * 0.85

    def get_token_usage(self, messages: List[Dict]) -> dict:
        """取得 token 用量資訊"""
        total = self._estimate_tokens(messages)
        return {
            "estimated_tokens": total,
            "max_tokens": self.config.max_context_tokens,
            "usage_pct": round(total / self.config.max_context_tokens * 100, 1),
            "message_count": len(messages),
            "needs_condensing": total >= self.config.max_context_tokens * 0.85,
        }

    # ===== 內部方法 =====

    def _split_recent(self, conversation: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """分離最近 N 輪和更舊的對話"""
        keep_count = self.config.keep_recent_turns * 2  # user+assistant = 1 輪

        if len(conversation) <= keep_count:
            return conversation, []

        split_point = len(conversation) - keep_count
        return conversation[split_point:], conversation[:split_point]

    def _chunk_messages(self, messages: List[Dict], chunk_size: int = 6) -> List[List[Dict]]:
        """將訊息分塊"""
        chunks = []
        for i in range(0, len(messages), chunk_size):
            chunk = messages[i:i + chunk_size]
            if len(chunk) >= self.config.min_chunk_size:
                chunks.append(chunk)
            elif chunks:
                # 不足最小大小，合併到最後一塊
                chunks[-1].extend(chunk)
        return chunks

    def _summarize_chunk(self, chunk: List[Dict]) -> str:
        """用 LLM 摘要一個區塊"""
        # 格式化對話
        formatted = ""
        for msg in chunk:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, list):
                # 多模態訊息
                content = " ".join(
                    p.get("text", "[image]") if isinstance(p, dict) else str(p)
                    for p in content
                )
            # 截斷過長的單條訊息
            if len(content) > 500:
                content = content[:500] + "..."
            formatted += f"[{role}]: {content}\n"

        prompt = self.SUMMARY_PROMPT.format(chunk=formatted)

        # 嘗試用 Ollama 摘要
        try:
            import requests
            ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            model = self.config.summary_model or os.environ.get("CB_LLM_MODEL", "qwen3:8b")

            resp = requests.post(
                f"{ollama_base}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 300},
                },
                timeout=30,
            )
            if resp.status_code == 200:
                result = resp.json().get("response", "").strip()
                # 清理 thinking tags
                if "<think>" in result:
                    import re
                    result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL).strip()
                if result:
                    return result
        except Exception as e:
            log.warning(f"LLM 摘要失敗，使用 fallback: {e}")

        # Fallback: 簡單截斷摘要
        return self._fallback_summary(chunk)

    def _fallback_summary(self, chunk: List[Dict]) -> str:
        """Fallback 摘要（不用 LLM）"""
        parts = []
        for msg in chunk:
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    p.get("text", "") if isinstance(p, dict) else str(p)
                    for p in content
                )
            role = msg.get("role", "")
            if role == "user" and content:
                # 保留用戶訊息的前 80 字
                parts.append(f"用戶: {content[:80]}")
            elif role == "assistant" and content:
                # 保留助手回覆的前 60 字
                parts.append(f"回覆: {content[:60]}")

        if not parts:
            return ""
        return " | ".join(parts[:4])

    def _estimate_tokens(self, messages: List[Dict]) -> int:
        """估算 token 數"""
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                for p in content:
                    if isinstance(p, dict):
                        total_chars += len(p.get("text", ""))
                    else:
                        total_chars += len(str(p))
            elif isinstance(content, str):
                total_chars += len(content)
        # 中文約 1.5-2 字元 = 1 token，英文約 4 字元 = 1 token
        # 混合取 ~3.5 字元/token
        return int(total_chars / self.config.estimate_ratio)

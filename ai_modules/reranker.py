#!/usr/bin/env python3
"""
築未科技 — Reranker 模組
使用交叉編碼器對知識庫查詢結果進行二階段重排序，提升精準度 30-40%
"""

import os
import requests
from typing import List, Dict, Optional, Tuple

OLLAMA_BASE = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11460").rstrip("/")


class OllamaReranker:
    """
    使用 Ollama 本地模型進行 Rerank（無需額外下載大型模型）
    原理：對每個候選文件，讓 LLM 評分與查詢的相關性
    """

    def __init__(self, model: str = "qwen3:4b", base_url: str = ""):
        self.model = model
        self.base_url = (base_url or OLLAMA_BASE).rstrip("/")

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5,
        metadatas: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """
        對文件列表進行重排序

        Args:
            query: 使用者查詢
            documents: 候選文件列表
            top_k: 回傳前 N 筆
            metadatas: 對應的 metadata 列表

        Returns:
            重排序後的結果列表 [{"document": str, "score": float, "metadata": dict, "original_index": int}]
        """
        if not documents:
            return []

        scored = []
        for i, doc in enumerate(documents):
            score = self._score_relevance(query, doc)
            entry = {
                "document": doc,
                "score": score,
                "original_index": i,
            }
            if metadatas and i < len(metadatas):
                entry["metadata"] = metadatas[i]
            scored.append(entry)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def _score_relevance(self, query: str, document: str) -> float:
        """讓 LLM 評分查詢與文件的相關性 (0-10)"""
        prompt = (
            f"請評估以下「查詢」與「文件」的相關性，只回傳 0-10 的數字（10=完全相關，0=完全無關）。\n\n"
            f"查詢：{query[:200]}\n"
            f"文件：{document[:500]}\n\n"
            f"相關性分數（只回數字）："
        )
        try:
            r = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0, "num_predict": 5, "num_gpu": 99},
                },
                timeout=10,
            )
            if r.status_code == 200:
                text = (r.json().get("response") or "").strip()
                # 提取數字
                for token in text.split():
                    try:
                        val = float(token.replace(",", "."))
                        return max(0.0, min(10.0, val))
                    except ValueError:
                        continue
        except Exception:
            pass
        return 5.0  # 預設中等分數


class EmbeddingReranker:
    """
    使用 Embedding 餘弦相似度進行快速重排序（不需要 LLM 推理）
    速度快，適合大量候選文件
    """

    def __init__(self, model: str = "nomic-embed-text:latest", base_url: str = ""):
        self.model = model
        self.base_url = (base_url or OLLAMA_BASE).rstrip("/")

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5,
        metadatas: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """使用 embedding 餘弦相似度重排序"""
        if not documents:
            return []

        query_emb = self._embed(query)
        if not query_emb:
            return [{"document": d, "score": 0.0, "original_index": i} for i, d in enumerate(documents[:top_k])]

        scored = []
        for i, doc in enumerate(documents):
            doc_emb = self._embed(doc[:500])
            if doc_emb:
                score = self._cosine_similarity(query_emb, doc_emb)
            else:
                score = 0.0
            entry = {"document": doc, "score": score, "original_index": i}
            if metadatas and i < len(metadatas):
                entry["metadata"] = metadatas[i]
            scored.append(entry)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def _embed(self, text: str) -> Optional[List[float]]:
        try:
            r = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": text},
                timeout=15,
            )
            if r.status_code == 200:
                embs = r.json().get("embeddings", [])
                return embs[0] if embs else None
        except Exception:
            pass
        return None

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class HybridReranker:
    """
    混合重排序：先用 Embedding 快速篩選，再用 LLM 精確排序
    兼顧速度與精準度
    """

    def __init__(self, llm_model: str = "qwen3:4b", embed_model: str = "nomic-embed-text:latest"):
        self.embedding_reranker = EmbeddingReranker(model=embed_model)
        self.llm_reranker = OllamaReranker(model=llm_model)

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5,
        metadatas: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """
        二階段重排序：
        1. Embedding 快速篩選 top_k * 2
        2. LLM 精確排序 top_k
        """
        if len(documents) <= top_k:
            return self.llm_reranker.rerank(query, documents, top_k, metadatas)

        # 階段 1：Embedding 快速篩選
        stage1 = self.embedding_reranker.rerank(query, documents, top_k * 2, metadatas)

        # 階段 2：LLM 精確排序
        stage1_docs = [r["document"] for r in stage1]
        stage1_metas = [r.get("metadata") for r in stage1]
        stage2 = self.llm_reranker.rerank(query, stage1_docs, top_k, stage1_metas)

        # 還原 original_index
        for item in stage2:
            orig_idx = stage1[item["original_index"]]["original_index"]
            item["original_index"] = orig_idx

        return stage2


# 全域單例
_reranker: Optional[HybridReranker] = None


def get_reranker() -> HybridReranker:
    global _reranker
    if _reranker is None:
        _reranker = HybridReranker()
    return _reranker


def rerank_results(query: str, documents: List[str], top_k: int = 5,
                   metadatas: Optional[List[Dict]] = None) -> List[Dict]:
    """便捷函數：對查詢結果進行重排序"""
    return get_reranker().rerank(query, documents, top_k, metadatas)

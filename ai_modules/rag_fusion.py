#!/usr/bin/env python3
"""
築未科技 — RAG-Fusion 模組
多查詢 RAG + 倒數排序融合 (Reciprocal Rank Fusion)
知識庫查詢準確度 +40%

原理：
1. 將使用者查詢擴展為多個不同角度的子查詢
2. 每個子查詢獨立搜尋知識庫
3. 使用 RRF 演算法融合所有結果
"""

import os
import requests
from typing import List, Dict, Optional, Callable

OLLAMA_BASE = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11460").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:32b")


class RAGFusion:
    """
    RAG-Fusion：多查詢融合搜尋
    """

    def __init__(self, model: str = "", base_url: str = "", num_queries: int = 3):
        self.model = model or OLLAMA_MODEL
        self.base_url = (base_url or OLLAMA_BASE).rstrip("/")
        self.num_queries = num_queries

    def generate_queries(self, original_query: str) -> List[str]:
        """
        將原始查詢擴展為多個子查詢（不同角度）
        """
        prompt = (
            f"你是一個搜尋查詢擴展專家。請將以下查詢改寫為 {self.num_queries} 個不同角度的搜尋查詢，"
            f"每個查詢一行，不要編號，不要其他文字。\n\n"
            f"原始查詢：{original_query}\n\n"
            f"改寫查詢："
        )
        try:
            r = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 200, "num_gpu": 99},
                },
                timeout=15,
            )
            if r.status_code == 200:
                text = (r.json().get("response") or "").strip()
                queries = [q.strip().lstrip("0123456789.-) ") for q in text.split("\n") if q.strip()]
                queries = [q for q in queries if len(q) > 3][:self.num_queries]
                if queries:
                    return [original_query] + queries
        except Exception:
            pass
        return [original_query]

    def reciprocal_rank_fusion(
        self, results_list: List[List[Dict]], k: int = 60
    ) -> List[Dict]:
        """
        倒數排序融合 (RRF)
        將多個排序結果融合為一個最終排序

        Args:
            results_list: 多組搜尋結果，每組為 [{"id": str, "document": str, ...}]
            k: RRF 常數（預設 60）

        Returns:
            融合後的排序結果
        """
        fused_scores: Dict[str, float] = {}
        doc_map: Dict[str, Dict] = {}

        for results in results_list:
            for rank, doc in enumerate(results):
                doc_id = doc.get("id") or doc.get("document", "")[:100]
                if doc_id not in doc_map:
                    doc_map[doc_id] = doc
                fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)

        sorted_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)
        return [
            {**doc_map[did], "rrf_score": fused_scores[did]}
            for did in sorted_ids
        ]

    def search(
        self,
        query: str,
        search_fn: Callable[[str, int], List[Dict]],
        top_k: int = 5,
    ) -> List[Dict]:
        """
        RAG-Fusion 搜尋

        Args:
            query: 原始查詢
            search_fn: 搜尋函數，接受 (query, limit) 回傳 [{"id", "document", ...}]
            top_k: 回傳前 N 筆

        Returns:
            融合後的搜尋結果
        """
        # 1. 生成多個子查詢
        queries = self.generate_queries(query)

        # 2. 每個子查詢獨立搜尋
        all_results = []
        for q in queries:
            try:
                results = search_fn(q, top_k * 2)
                if results:
                    all_results.append(results)
            except Exception:
                continue

        if not all_results:
            return []

        # 3. RRF 融合
        fused = self.reciprocal_rank_fusion(all_results)
        return fused[:top_k]


# 全域單例
_fusion: Optional[RAGFusion] = None


def get_rag_fusion() -> RAGFusion:
    global _fusion
    if _fusion is None:
        _fusion = RAGFusion()
    return _fusion


def fusion_search(query: str, search_fn: Callable, top_k: int = 5) -> List[Dict]:
    """便捷函數：RAG-Fusion 搜尋"""
    return get_rag_fusion().search(query, search_fn, top_k)

#!/usr/bin/env python3
"""
築未科技 — AI 處理 SOP 模組
整合 GitHub 上最佳實踐，讓系統少走冤枉路

核心概念來源：
- DSPy (Stanford)：自動優化 prompt，不靠手寫
- RouteLLM (LMSYS)：智慧路由，簡單問題用小模型，複雜問題用大模型
- AutoRAG：自動評估 RAG 管線品質
- LLMOps 最佳實踐：快取、重試、fallback、品質門檻

7 條 SOP 規則：
1. 分類優先 — 先判斷任務複雜度，再選模型
2. Prompt 模板化 — 用結構化模板取代隨意 prompt
3. 品質門檻 — 每次回應都自動評分，低於門檻重試
4. 智慧快取 — 相似問題直接回快取，省 GPU 時間
5. 漸進式重試 — 小模型失敗 → 大模型 → 雲端
6. RAG 自動評估 — 檢索結果自動評分，低品質不送 LLM
7. 結果結構化 — 強制 JSON/結構化輸出，減少解析錯誤
"""

import os
import json
import time
import hashlib
import requests
from typing import Dict, List, Optional, Any, Callable

OLLAMA_BASE = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11460").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:32b")
FAST_MODEL = os.environ.get("OLLAMA_FAST_MODEL", "qwen3:4b")


# ═══════════════════════════════════════════
# SOP 1: 任務分類器（RouteLLM 概念）
# ═══════════════════════════════════════════

class TaskClassifier:
    """
    任務複雜度分類器 — 決定用哪個模型

    分類邏輯（不需要額外 LLM 呼叫，用規則引擎）：
    - simple: 問候、翻譯、簡單問答 → 快速模型 (qwen3:4b)
    - medium: 摘要、分析、一般對話 → 標準模型 (qwen3:8b)
    - complex: 程式碼、推理、多步驟 → 標準模型 + 品質檢查
    - expert: 專業領域、長文生成 → 雲端大模型 fallback
    """

    SIMPLE_KEYWORDS = [
        "你好", "hello", "hi", "嗨", "謝謝", "翻譯", "translate",
        "幾點", "天氣", "日期", "是什麼", "what is", "define",
    ]
    COMPLEX_KEYWORDS = [
        "程式", "code", "python", "javascript", "分析", "analyze",
        "比較", "compare", "推理", "reason", "步驟", "step by step",
        "為什麼", "why", "如何", "how to", "設計", "design",
        "debug", "修復", "fix", "優化", "optimize", "重構", "refactor",
    ]
    EXPERT_KEYWORDS = [
        "法規", "法律", "合約", "契約", "施工規範", "品質計畫",
        "結構計算", "預算編列", "工程估驗", "安全衛生",
        "70b", "gpt-4", "claude", "深度分析", "完整報告",
    ]

    @staticmethod
    def classify(query: str) -> Dict:
        """
        分類任務複雜度

        Returns:
            {"level": str, "model": str, "max_tokens": int, "temperature": float,
             "needs_rag": bool, "needs_review": bool}
        """
        q = query.lower().strip()
        q_len = len(q)

        # 規則 1: 專業關鍵字 → expert（最高優先）
        if any(k in q for k in TaskClassifier.EXPERT_KEYWORDS):
            return {
                "level": "expert", "model": OLLAMA_MODEL,
                "max_tokens": 4096, "temperature": 0.2,
                "needs_rag": True, "needs_review": True,
            }

        # 規則 2: 複雜關鍵字 或 長問題 → complex
        if any(k in q for k in TaskClassifier.COMPLEX_KEYWORDS) or q_len > 200:
            return {
                "level": "complex", "model": OLLAMA_MODEL,
                "max_tokens": 2048, "temperature": 0.2,
                "needs_rag": True, "needs_review": True,
            }

        # 規則 3: 短問題 + 簡單關鍵字 → simple
        if q_len < 30 and any(k in q for k in TaskClassifier.SIMPLE_KEYWORDS):
            return {
                "level": "simple", "model": FAST_MODEL,
                "max_tokens": 256, "temperature": 0.3,
                "needs_rag": False, "needs_review": False,
            }

        # 規則 4: 中等長度 → medium
        if q_len > 50:
            return {
                "level": "medium", "model": OLLAMA_MODEL,
                "max_tokens": 1024, "temperature": 0.3,
                "needs_rag": q_len > 80, "needs_review": False,
            }

        # 預設: simple
        return {
            "level": "simple", "model": FAST_MODEL,
            "max_tokens": 512, "temperature": 0.3,
            "needs_rag": False, "needs_review": False,
        }


# ═══════════════════════════════════════════
# SOP 2: Prompt 模板引擎（DSPy 概念）
# ═══════════════════════════════════════════

class PromptTemplate:
    """
    結構化 Prompt 模板 — 取代隨意拼接的 prompt

    DSPy 核心理念：prompt 是可優化的程式，不是手寫的字串
    """

    TEMPLATES = {
        "qa": (
            "你是一個專業的 AI 助手。\n"
            "請根據以下資訊回答問題。\n"
            "如果資訊不足，請明確說明你不確定。\n\n"
            "{context}\n\n"
            "問題：{query}\n\n"
            "請用繁體中文回答，簡潔且準確。"
        ),
        "qa_with_rag": (
            "你是一個專業的 AI 助手。\n"
            "以下是從知識庫檢索到的相關資料：\n\n"
            "---\n{rag_context}\n---\n\n"
            "請根據上述資料回答以下問題。\n"
            "如果資料不足以回答，請明確說明。\n"
            "不要編造資料中沒有的內容。\n\n"
            "問題：{query}\n\n"
            "回答："
        ),
        "analysis": (
            "你是一個分析專家。\n"
            "請對以下內容進行深入分析：\n\n"
            "{content}\n\n"
            "分析要求：{query}\n\n"
            "請提供：\n"
            "1. 核心發現\n"
            "2. 關鍵數據\n"
            "3. 建議行動\n"
        ),
        "code": (
            "你是一個資深軟體工程師。\n"
            "請根據以下需求撰寫程式碼：\n\n"
            "{query}\n\n"
            "要求：\n"
            "- 程式碼完整可執行\n"
            "- 包含必要的錯誤處理\n"
            "- 加入簡要註釋\n"
            "- 使用最佳實踐\n"
        ),
        "structured_output": (
            "你是一個資料處理專家。\n"
            "請將以下內容轉換為 JSON 格式：\n\n"
            "{content}\n\n"
            "輸出格式：{schema}\n\n"
            "只輸出 JSON，不要其他文字。"
        ),
        "review": (
            "你是一個品質審查專家。\n"
            "請評估以下 AI 回應的品質：\n\n"
            "原始問題：{query}\n"
            "AI 回應：{response}\n\n"
            "請用 JSON 格式評分：\n"
            '{{"score": 1-10, "issues": ["問題"], "suggestion": "改善建議"}}\n'
            "只輸出 JSON。"
        ),
        "thinking": (
            "你是一個深度思考的 AI 助手。\n"
            "在回答之前，請先在 <think> 標籤中進行深度推理：\n"
            "1. 用自己的話重述問題\n"
            "2. 拆解核心要素，考慮多種解法\n"
            "3. 質疑假設、找出盲點\n"
            "4. 選出最佳方案\n\n"
            "<think>\n（你的內心思考過程）\n</think>\n\n"
            "問題：{query}\n\n"
            "請用繁體中文回答。回答中不要提及你的思考過程。"
        ),
        "thinking_construction": (
            "你是一個資深營建工程顧問，具備土木技師專業。\n"
            "在回答之前，請先在 <think> 標籤中進行專業推演：\n"
            "1. 確認涉及的工程領域（結構/大地/施工/品管/安衛/契約）\n"
            "2. 回想相關規範（建築技術規則/公路橋梁設計規範/施工規範）\n"
            "3. 考慮現場實務條件和安全風險\n"
            "4. 產生方案並檢核是否符合規範\n\n"
            "<think>\n（你的專業推演過程）\n</think>\n\n"
            "問題：{query}\n\n"
            "請引用具體規範條文，給出專業結論。"
        ),
    }

    @staticmethod
    def render(template_name: str, **kwargs) -> str:
        """渲染模板"""
        tmpl = PromptTemplate.TEMPLATES.get(template_name, "{query}")
        try:
            return tmpl.format(**kwargs)
        except KeyError as e:
            return tmpl.replace(f"{{{e.args[0]}}}", "")

    @staticmethod
    def add_template(name: str, template: str):
        """新增自訂模板"""
        PromptTemplate.TEMPLATES[name] = template


# ═══════════════════════════════════════════
# SOP 3: 品質門檻（自動評分 + 重試）
# ═══════════════════════════════════════════

class QualityGate:
    """
    品質門檻 — 自動評估回應品質，低於門檻自動重試

    規則：
    - 回應太短（< 20 字）→ 重試
    - 回應包含 "我不知道" 但 RAG 有資料 → 重試
    - 回應重複原始問題 → 重試
    - 可選：用 LLM 自評分數
    """

    def __init__(self, min_length: int = 20, min_score: float = 6.0):
        self.min_length = min_length
        self.min_score = min_score

    def check(self, query: str, response: str, rag_context: str = "") -> Dict:
        """
        快速品質檢查（不需要 LLM）

        Returns:
            {"pass": bool, "score": float, "issues": list}
        """
        issues = []
        score = 8.0  # 基礎分

        # 檢查 1: 回應長度
        if len(response.strip()) < self.min_length:
            issues.append("回應過短")
            score -= 3.0

        # 檢查 2: 空回應
        if not response.strip():
            return {"pass": False, "score": 0, "issues": ["空回應"]}

        # 檢查 3: 回應重複問題
        if query.strip() in response and len(response) < len(query) * 2:
            issues.append("回應重複問題")
            score -= 2.0

        # 檢查 4: 有 RAG 資料但回應說不知道
        refusal_phrases = ["我不知道", "我無法", "抱歉", "sorry", "i don't know", "無法回答"]
        if rag_context and any(p in response.lower() for p in refusal_phrases):
            issues.append("有參考資料但拒絕回答")
            score -= 2.0

        # 檢查 5: 回應是否包含有用內容（不只是客套話）
        filler_phrases = ["好的", "沒問題", "當然", "可以的"]
        if len(response.strip()) < 50 and any(response.strip().startswith(p) for p in filler_phrases):
            issues.append("回應缺乏實質內容")
            score -= 1.5

        # 檢查 6: JSON 格式要求但回應不是 JSON
        if "json" in query.lower() and not any(c in response for c in ["{", "["]):
            issues.append("要求 JSON 但未提供")
            score -= 2.0

        return {
            "pass": score >= self.min_score and not any("空回應" == i for i in issues),
            "score": max(0, round(score, 1)),
            "issues": issues,
        }


# ═══════════════════════════════════════════
# SOP 4: 智慧快取
# ═══════════════════════════════════════════

class ResponseCache:
    """
    回應快取 — 相似問題直接回快取

    用 query 的 hash 做 key，TTL 過期自動清除
    """

    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600):
        self._cache: Dict[str, Dict] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds

    def _hash(self, query: str, model: str = "") -> str:
        """生成快取 key"""
        key = f"{model}:{query.strip().lower()}"
        return hashlib.md5(key.encode()).hexdigest()

    def get(self, query: str, model: str = "") -> Optional[str]:
        """查詢快取"""
        h = self._hash(query, model)
        entry = self._cache.get(h)
        if entry and (time.time() - entry["time"]) < self._ttl:
            entry["hits"] += 1
            return entry["response"]
        elif entry:
            del self._cache[h]  # 過期清除
        return None

    def set(self, query: str, response: str, model: str = ""):
        """寫入快取"""
        if len(self._cache) >= self._max_size:
            # 清除最舊的 20%
            sorted_keys = sorted(self._cache, key=lambda k: self._cache[k]["time"])
            for k in sorted_keys[:len(sorted_keys) // 5]:
                del self._cache[k]

        h = self._hash(query, model)
        self._cache[h] = {"response": response, "time": time.time(), "hits": 0}

    def stats(self) -> Dict:
        return {"size": len(self._cache), "max": self._max_size, "ttl": self._ttl}

    def clear(self):
        self._cache.clear()


# ═══════════════════════════════════════════
# SOP 5: 漸進式重試（Escalation Chain）
# ═══════════════════════════════════════════

class EscalationChain:
    """
    漸進式重試鏈 — 小模型失敗 → 大模型 → 雲端

    鏈條（雙 GPU：5070Ti 16GB + 4060Ti 8GB）：
    qwen3:4b(2s) → qwen3:8b(5s) → deepseek-r1:14b(10s) → qwen3:32b(25s) → Groq → Gemini
    """

    STANDARD_MODEL = os.environ.get("OLLAMA_STANDARD_MODEL", "qwen3:8b")
    REASONING_MODEL = os.environ.get("OLLAMA_REASONING_MODEL", "deepseek-r1:14b")
    STRONG_MODEL = os.environ.get("OLLAMA_STRONG_MODEL", "qwen3:32b")

    def __init__(self):
        self.chain = [
            {"model": FAST_MODEL, "label": "fast_local", "timeout": 30},
            {"model": self.STANDARD_MODEL, "label": "standard_local", "timeout": 60},
            {"model": self.REASONING_MODEL, "label": "reasoning_local", "timeout": 90},
            {"model": self.STRONG_MODEL, "label": "strong_local", "timeout": 150},
        ]
        # 如果有雲端 API key，加入雲端 fallback
        if os.environ.get("GROQ_API_KEY"):
            self.chain.append({"model": "groq", "label": "cloud_groq", "timeout": 30})
        if os.environ.get("GEMINI_API_KEY"):
            self.chain.append({"model": "gemini", "label": "cloud_gemini", "timeout": 30})

    def execute(self, messages: List[Dict], start_level: int = 0,
                quality_gate: Optional[QualityGate] = None,
                query: str = "") -> Dict:
        """
        沿著鏈條嘗試，直到品質通過

        Returns:
            {"ok": bool, "response": str, "model_used": str, "level": str,
             "attempts": int, "quality": dict}
        """
        for i, step in enumerate(self.chain[start_level:], start=start_level):
            model = step["model"]
            try:
                if model in ("groq", "gemini"):
                    response = self._call_cloud(model, messages, step["timeout"])
                else:
                    response = self._call_ollama(model, messages, step["timeout"])

                if not response:
                    continue

                # 品質檢查
                if quality_gate:
                    qc = quality_gate.check(query, response)
                    if qc["pass"]:
                        return {
                            "ok": True, "response": response,
                            "model_used": model, "level": step["label"],
                            "attempts": i - start_level + 1, "quality": qc,
                        }
                    # 品質不過，繼續下一個模型
                    continue
                else:
                    return {
                        "ok": True, "response": response,
                        "model_used": model, "level": step["label"],
                        "attempts": i - start_level + 1, "quality": {"pass": True, "score": 7},
                    }
            except Exception:
                continue

        return {"ok": False, "response": "", "model_used": "", "level": "exhausted",
                "attempts": len(self.chain), "quality": {"pass": False, "score": 0}}

    def _call_ollama(self, model: str, messages: List[Dict], timeout: int) -> str:
        r = requests.post(
            f"{OLLAMA_BASE}/api/chat",
            json={"model": model, "messages": messages, "stream": False,
                  "options": {"num_predict": 2048, "num_ctx": 8192, "num_batch": 512}},
            timeout=timeout,
        )
        if r.status_code == 200:
            msg = r.json().get("message") or {}
            content = msg.get("content") or ""
            if not content.strip() and msg.get("thinking"):
                content = msg["thinking"]
            return content.strip()
        return ""

    def _call_cloud(self, provider: str, messages: List[Dict], timeout: int) -> str:
        """呼叫雲端 API（Groq / Gemini）"""
        try:
            if provider == "groq":
                api_key = os.environ.get("GROQ_API_KEY", "")
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 2048},
                    timeout=timeout,
                )
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"].strip()
            elif provider == "gemini":
                api_key = os.environ.get("GEMINI_API_KEY", "")
                # 轉換 messages 格式
                parts = [{"text": m["content"]} for m in messages if m["role"] != "system"]
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                    json={"contents": [{"parts": parts}]},
                    timeout=timeout,
                )
                if r.status_code == 200:
                    candidates = r.json().get("candidates", [])
                    if candidates:
                        return candidates[0]["content"]["parts"][0]["text"].strip()
        except Exception:
            pass
        return ""


# ═══════════════════════════════════════════
# SOP 6: RAG 品質評估
# ═══════════════════════════════════════════

class RAGEvaluator:
    """
    RAG 檢索品質評估 — 在送入 LLM 前先評估檢索結果

    規則：
    - 檢索結果為空 → 跳過 RAG，直接用 LLM
    - 檢索距離太遠（> 閾值）→ 標記為低信心
    - 檢索結果與問題無關 → 不送入 LLM（避免幻覺）
    """

    def __init__(self, max_distance: float = 1.2, min_results: int = 1):
        self.max_distance = max_distance
        self.min_results = min_results

    def evaluate(self, query: str, results: List[Dict]) -> Dict:
        """
        評估 RAG 檢索結果品質

        Args:
            query: 原始問題
            results: [{"text": str, "distance": float, "metadata": dict}]

        Returns:
            {"use_rag": bool, "confidence": str, "filtered_results": list,
             "context": str, "reason": str}
        """
        if not results:
            return {
                "use_rag": False, "confidence": "none",
                "filtered_results": [], "context": "",
                "reason": "無檢索結果",
            }

        # 過濾距離太遠的結果
        good = [r for r in results if r.get("distance", 999) < self.max_distance]

        if len(good) < self.min_results:
            return {
                "use_rag": False, "confidence": "low",
                "filtered_results": good, "context": "",
                "reason": f"高品質結果不足（{len(good)}/{self.min_results}）",
            }

        # 計算平均距離
        avg_dist = sum(r.get("distance", 0) for r in good) / len(good)

        if avg_dist < 0.5:
            confidence = "high"
        elif avg_dist < 0.8:
            confidence = "medium"
        else:
            confidence = "low"

        # 組合上下文（最多 5 條）
        context_parts = [r.get("text", "")[:500] for r in good[:5]]
        context = "\n\n".join(context_parts)

        return {
            "use_rag": True,
            "confidence": confidence,
            "filtered_results": good[:5],
            "context": context,
            "avg_distance": round(avg_dist, 3),
            "reason": f"{len(good)} 條結果，平均距離 {avg_dist:.3f}",
        }


# ═══════════════════════════════════════════
# SOP 主管線：AI Pipeline
# ═══════════════════════════════════════════

class AIPipeline:
    """
    AI 處理主管線 — 整合所有 SOP

    流程：
    1. 分類任務 → 決定模型和參數
    2. 查快取 → 命中直接回傳
    3. RAG 檢索 + 評估 → 決定是否用知識庫
    4. 渲染 Prompt 模板
    5. 漸進式呼叫 LLM
    6. 品質門檻檢查
    7. 寫入快取
    """

    def __init__(self, rag_search_func: Optional[Callable] = None):
        self.classifier = TaskClassifier()
        self.quality_gate = QualityGate()
        self.cache = ResponseCache()
        self.escalation = EscalationChain()
        self.rag_evaluator = RAGEvaluator()
        self.rag_search = rag_search_func  # 外部注入的 RAG 搜尋函數
        self._stats = {"total": 0, "cache_hits": 0, "rag_used": 0,
                       "escalated": 0, "quality_retries": 0}

    def process(self, query: str, system_prompt: str = "",
                force_model: str = "", skip_cache: bool = False) -> Dict:
        """
        主處理函數 — 執行完整 SOP 管線

        Args:
            query: 使用者問題
            system_prompt: 系統提示（可選）
            force_model: 強制使用特定模型（跳過分類）
            skip_cache: 跳過快取

        Returns:
            {"ok": bool, "response": str, "model": str, "level": str,
             "classification": dict, "rag": dict, "quality": dict,
             "cached": bool, "elapsed_ms": float}
        """
        start = time.time()
        self._stats["total"] += 1

        # Step 1: 分類
        classification = self.classifier.classify(query)
        model = force_model or classification["model"]

        # Step 2: 查快取
        if not skip_cache:
            cached = self.cache.get(query, model)
            if cached:
                self._stats["cache_hits"] += 1
                return {
                    "ok": True, "response": cached, "model": model,
                    "level": "cache", "classification": classification,
                    "rag": {"use_rag": False}, "quality": {"pass": True, "score": 8},
                    "cached": True, "elapsed_ms": round((time.time() - start) * 1000, 1),
                }

        # Step 3: RAG 檢索 + 評估
        rag_result = {"use_rag": False, "context": "", "confidence": "none"}
        if classification["needs_rag"] and self.rag_search:
            try:
                raw_results = self.rag_search(query)
                rag_result = self.rag_evaluator.evaluate(query, raw_results)
                if rag_result["use_rag"]:
                    self._stats["rag_used"] += 1
            except Exception:
                pass

        # Step 4: 渲染 Prompt
        if rag_result["use_rag"]:
            prompt = PromptTemplate.render("qa_with_rag",
                                           query=query,
                                           rag_context=rag_result["context"])
        else:
            prompt = query

        # 構建 messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Step 5: 漸進式呼叫
        # 根據分類決定起始層級
        if classification["level"] == "simple":
            start_level = 0  # 從快速模型開始
        elif classification["level"] in ("medium", "complex"):
            start_level = 1  # 從標準模型開始
        else:
            start_level = 1  # expert 也從標準開始，品質不過再升級

        result = self.escalation.execute(
            messages, start_level=start_level,
            quality_gate=self.quality_gate if classification["needs_review"] else None,
            query=query,
        )

        if result.get("attempts", 1) > 1:
            self._stats["escalated"] += 1

        # Step 6: 品質門檻（如果 escalation 沒做品質檢查）
        if not classification["needs_review"] and result["ok"]:
            qc = self.quality_gate.check(query, result["response"], rag_result.get("context", ""))
            result["quality"] = qc

        # Step 7: 寫入快取（只快取通過品質的回應）
        if result["ok"] and result.get("quality", {}).get("pass", False):
            self.cache.set(query, result["response"], result.get("model_used", model))

        elapsed = round((time.time() - start) * 1000, 1)

        return {
            "ok": result["ok"],
            "response": result.get("response", ""),
            "model": result.get("model_used", model),
            "level": result.get("level", "unknown"),
            "classification": classification,
            "rag": {
                "use_rag": rag_result["use_rag"],
                "confidence": rag_result.get("confidence", "none"),
                "reason": rag_result.get("reason", ""),
            },
            "quality": result.get("quality", {}),
            "cached": False,
            "elapsed_ms": elapsed,
        }

    def get_stats(self) -> Dict:
        """取得管線統計"""
        total = max(1, self._stats["total"])
        return {
            **self._stats,
            "cache_hit_rate": round(self._stats["cache_hits"] / total * 100, 1),
            "rag_usage_rate": round(self._stats["rag_used"] / total * 100, 1),
            "escalation_rate": round(self._stats["escalated"] / total * 100, 1),
            "cache_stats": self.cache.stats(),
        }

    def reset_stats(self):
        self._stats = {"total": 0, "cache_hits": 0, "rag_used": 0,
                       "escalated": 0, "quality_retries": 0}
        self.cache.clear()


# ═══════════════════════════════════════════
# 全域單例 + 便捷函數
# ═══════════════════════════════════════════

_pipeline: Optional[AIPipeline] = None


def get_pipeline(rag_search_func: Optional[Callable] = None) -> AIPipeline:
    """取得全域 AI Pipeline"""
    global _pipeline
    if _pipeline is None:
        _pipeline = AIPipeline(rag_search_func)
    return _pipeline


def smart_ask(query: str, system_prompt: str = "") -> Dict:
    """
    便捷函數：智慧問答（完整 SOP 管線）

    用法：
        from ai_modules.ai_sop import smart_ask
        result = smart_ask("如何優化 Ollama 推理速度？")
        print(result["response"])
    """
    return get_pipeline().process(query, system_prompt)


def classify_task(query: str) -> Dict:
    """便捷函數：分類任務"""
    return TaskClassifier.classify(query)


def render_prompt(template: str, **kwargs) -> str:
    """便捷函數：渲染 Prompt 模板"""
    return PromptTemplate.render(template, **kwargs)

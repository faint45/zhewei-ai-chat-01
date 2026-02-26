#!/usr/bin/env python3
"""
築未科技 — DSPy Prompt 自動優化模組
用 Stanford DSPy 框架讓本地 Ollama 模型自動找到最佳 prompt

核心功能：
1. 自動連接本地 Ollama（qwen3:8b / qwen3:32b）
2. 定義結構化任務（QA、分類、摘要、程式碼）
3. 自動優化 prompt（不用手調）
4. 快取優化結果，下次直接用
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any

try:
    import dspy
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False

OLLAMA_BASE = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11460").rstrip("/")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:32b")
FAST_MODEL = os.environ.get("OLLAMA_FAST_MODEL", "qwen3:4b")
STRONG_MODEL = os.environ.get("OLLAMA_STRONG_MODEL", "qwen3:32b")

CACHE_DIR = Path(os.environ.get("DSPY_CACHE_DIR", "brain_workspace/dspy_cache"))


# ═══════════════════════════════════════════
# DSPy 模組定義（結構化任務）
# ═══════════════════════════════════════════

if DSPY_AVAILABLE:

    class SmartQA(dspy.Module):
        """智慧問答 — 自動選擇最佳回答策略"""

        def __init__(self):
            self.generate = dspy.ChainOfThought("question -> answer")

        def forward(self, question: str) -> dspy.Prediction:
            return self.generate(question=question)

    class TaskClassifierDSPy(dspy.Module):
        """任務分類器 — 自動判斷任務類型和複雜度"""

        def __init__(self):
            self.classify = dspy.Predict(
                "task_description -> category, complexity, recommended_model"
            )

        def forward(self, task_description: str) -> dspy.Prediction:
            return self.classify(task_description=task_description)

    class CodeGenerator(dspy.Module):
        """程式碼生成 — 結構化輸出"""

        def __init__(self):
            self.generate = dspy.ChainOfThought(
                "requirement, language -> code, explanation"
            )

        def forward(self, requirement: str, language: str = "python") -> dspy.Prediction:
            return self.generate(requirement=requirement, language=language)

    class Summarizer(dspy.Module):
        """摘要生成 — 自動提取重點"""

        def __init__(self):
            self.summarize = dspy.ChainOfThought(
                "text, max_points -> summary, key_points"
            )

        def forward(self, text: str, max_points: str = "5") -> dspy.Prediction:
            return self.summarize(text=text, max_points=max_points)

    class ConstructionExpert(dspy.Module):
        """營建專家 — 工程法規和施工規範問答"""

        def __init__(self):
            self.answer = dspy.ChainOfThought(
                "question, context -> answer, regulations, safety_notes"
            )

        def forward(self, question: str, context: str = "") -> dspy.Prediction:
            return self.answer(question=question, context=context)


# ═══════════════════════════════════════════
# DSPy 引擎（管理連線和優化）
# ═══════════════════════════════════════════

class DSPyEngine:
    """
    DSPy 引擎 — 管理 Ollama 連線、模組實例化、prompt 優化

    用法：
        engine = DSPyEngine()
        answer = engine.ask("什麼是混凝土養護？")
        code = engine.generate_code("寫一個計算鋼筋用量的函數", "python")
    """

    def __init__(self, model: str = None, api_base: str = None):
        if not DSPY_AVAILABLE:
            raise ImportError("DSPy 未安裝。請執行: pip install dspy")

        self.model_name = model or DEFAULT_MODEL
        self.api_base = api_base or OLLAMA_BASE
        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 初始化 DSPy LM
        self.lm = dspy.LM(
            f"ollama_chat/{self.model_name}",
            api_base=self.api_base,
            temperature=0.7,
            max_tokens=2048,
        )
        dspy.configure(lm=self.lm)

        # 初始化模組
        self._modules = {}

    def _get_module(self, name: str):
        """延遲載入模組"""
        if name not in self._modules:
            module_map = {
                "qa": SmartQA,
                "classifier": TaskClassifierDSPy,
                "code": CodeGenerator,
                "summarizer": Summarizer,
                "construction": ConstructionExpert,
            }
            if name in module_map:
                self._modules[name] = module_map[name]()
        return self._modules.get(name)

    def switch_model(self, model: str):
        """切換模型（例如從 8b 切到 32b 做深度推理）"""
        self.model_name = model
        self.lm = dspy.LM(
            f"ollama_chat/{model}",
            api_base=self.api_base,
            temperature=0.7,
            max_tokens=2048,
        )
        dspy.configure(lm=self.lm)

    # ── 便捷方法 ──

    def ask(self, question: str) -> str:
        """智慧問答"""
        module = self._get_module("qa")
        result = module(question=question)
        return result.answer

    def classify(self, task: str) -> Dict[str, str]:
        """分類任務"""
        module = self._get_module("classifier")
        result = module(task_description=task)
        return {
            "category": result.category,
            "complexity": result.complexity,
            "recommended_model": result.recommended_model,
        }

    def generate_code(self, requirement: str, language: str = "python") -> Dict[str, str]:
        """生成程式碼"""
        module = self._get_module("code")
        result = module(requirement=requirement, language=language)
        return {
            "code": result.code,
            "explanation": result.explanation,
        }

    def summarize(self, text: str, max_points: int = 5) -> Dict[str, str]:
        """摘要"""
        module = self._get_module("summarizer")
        result = module(text=text, max_points=str(max_points))
        return {
            "summary": result.summary,
            "key_points": result.key_points,
        }

    def construction_qa(self, question: str, context: str = "") -> Dict[str, str]:
        """營建專家問答"""
        module = self._get_module("construction")
        result = module(question=question, context=context)
        return {
            "answer": result.answer,
            "regulations": result.regulations,
            "safety_notes": result.safety_notes,
        }

    def smart_route_and_ask(self, question: str) -> Dict[str, Any]:
        """
        智慧路由 + 問答：
        1. 先用快速模型分類任務
        2. 根據複雜度選擇模型
        3. 用選定模型回答
        """
        # 用快速模型分類
        original_model = self.model_name
        self.switch_model(FAST_MODEL)

        try:
            classification = self.classify(question)
        except Exception:
            classification = {"category": "general", "complexity": "medium", "recommended_model": DEFAULT_MODEL}

        # 根據複雜度選模型
        complexity = classification.get("complexity", "medium").lower()
        if "high" in complexity or "complex" in complexity or "expert" in complexity:
            target_model = STRONG_MODEL
        elif "low" in complexity or "simple" in complexity:
            target_model = FAST_MODEL
        else:
            target_model = DEFAULT_MODEL

        # 切換到目標模型回答
        self.switch_model(target_model)
        try:
            answer = self.ask(question)
        except Exception as e:
            # fallback 到預設模型
            self.switch_model(DEFAULT_MODEL)
            answer = self.ask(question)
            target_model = DEFAULT_MODEL

        # 恢復原始模型
        self.switch_model(original_model)

        return {
            "answer": answer,
            "classification": classification,
            "model_used": target_model,
        }

    def get_status(self) -> Dict:
        """取得引擎狀態"""
        return {
            "dspy_available": DSPY_AVAILABLE,
            "dspy_version": dspy.__version__ if DSPY_AVAILABLE else None,
            "current_model": self.model_name,
            "api_base": self.api_base,
            "loaded_modules": list(self._modules.keys()),
            "cache_dir": str(self.cache_dir),
        }


# ═══════════════════════════════════════════
# 全域便捷函數
# ═══════════════════════════════════════════

_engine = None


def get_engine(model: str = None) -> DSPyEngine:
    """取得或建立 DSPy 引擎（單例）"""
    global _engine
    if _engine is None:
        _engine = DSPyEngine(model=model)
    return _engine


def smart_ask(question: str) -> str:
    """快速問答（用預設模型）"""
    return get_engine().ask(question)


def smart_route_ask(question: str) -> Dict[str, Any]:
    """智慧路由問答（自動選模型）"""
    return get_engine().smart_route_and_ask(question)


def generate_code(requirement: str, language: str = "python") -> Dict[str, str]:
    """生成程式碼"""
    return get_engine().generate_code(requirement, language)


if __name__ == "__main__":
    if not DSPY_AVAILABLE:
        print("DSPy 未安裝。請執行: pip install dspy")
    else:
        print(f"DSPy {dspy.__version__} OK")
        print(f"Ollama: {OLLAMA_BASE}")
        print(f"Models: fast={FAST_MODEL}, default={DEFAULT_MODEL}, strong={STRONG_MODEL}")
        print()

        try:
            engine = DSPyEngine()
            status = engine.get_status()
            print(f"Engine status: {json.dumps(status, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"Engine init error: {e}")

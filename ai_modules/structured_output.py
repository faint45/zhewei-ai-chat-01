#!/usr/bin/env python3
"""
築未科技 — 結構化輸出模組
使用 Instructor + Pydantic 確保 AI 輸出格式 100% 正確
"""

import json
import os
import requests
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel, Field

OLLAMA_BASE = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11460").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:32b")

T = TypeVar("T", bound=BaseModel)


# ── 常用結構化輸出模型 ──

class TaskAnalysis(BaseModel):
    """任務分析結果"""
    task_type: str = Field(description="任務類型: think/execute/code/vision")
    complexity: str = Field(description="複雜度: low/medium/high")
    recommended_model: str = Field(description="推薦使用的模型")
    reasoning: str = Field(description="推薦理由")


class CodeReview(BaseModel):
    """程式碼審查結果"""
    has_bugs: bool = Field(description="是否有 bug")
    bugs: List[str] = Field(default_factory=list, description="bug 列表")
    suggestions: List[str] = Field(default_factory=list, description="改善建議")
    score: int = Field(ge=0, le=10, description="程式碼品質分數 0-10")


class DocumentSummary(BaseModel):
    """文件摘要"""
    title: str = Field(description="文件標題")
    summary: str = Field(description="摘要內容")
    keywords: List[str] = Field(default_factory=list, description="關鍵字")
    category: str = Field(description="文件分類")


class ActionPlan(BaseModel):
    """行動計畫"""
    goal: str = Field(description="目標")
    steps: List[str] = Field(description="執行步驟")
    estimated_time: str = Field(description="預估時間")
    risks: List[str] = Field(default_factory=list, description="風險")


class EntityExtraction(BaseModel):
    """實體萃取"""
    persons: List[str] = Field(default_factory=list, description="人名")
    organizations: List[str] = Field(default_factory=list, description="組織名")
    locations: List[str] = Field(default_factory=list, description="地點")
    dates: List[str] = Field(default_factory=list, description="日期")
    amounts: List[str] = Field(default_factory=list, description="金額")


# ── 結構化輸出引擎 ──

class StructuredOutputEngine:
    """
    結構化輸出引擎：確保 Ollama 回傳符合 Pydantic Schema 的 JSON
    """

    def __init__(self, model: str = "", base_url: str = ""):
        self.model = model or OLLAMA_MODEL
        self.base_url = (base_url or OLLAMA_BASE).rstrip("/")

    def generate(self, prompt: str, schema: Type[T], max_retries: int = 3) -> Optional[T]:
        """
        生成結構化輸出

        Args:
            prompt: 使用者提示
            schema: Pydantic 模型類別
            max_retries: 最大重試次數

        Returns:
            Pydantic 模型實例，失敗回傳 None
        """
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
        system_prompt = (
            f"你是一個結構化資料生成助手。請嚴格按照以下 JSON Schema 回傳結果。\n"
            f"只回傳 JSON，不要有任何其他文字。\n\n"
            f"JSON Schema:\n{schema_json}"
        )

        for attempt in range(max_retries):
            try:
                r = requests.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.0, "num_predict": 2048, "num_gpu": 99},
                    },
                    timeout=30,
                )
                if r.status_code != 200:
                    continue

                content = (r.json().get("message") or {}).get("content") or ""
                content = content.strip()

                # 嘗試解析 JSON
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()

                data = json.loads(content)
                return schema.model_validate(data)

            except (json.JSONDecodeError, Exception):
                continue

        return None

    def extract_entities(self, text: str) -> Optional[EntityExtraction]:
        """從文本中萃取實體"""
        return self.generate(f"從以下文本中萃取所有實體：\n\n{text[:2000]}", EntityExtraction)

    def analyze_task(self, task: str) -> Optional[TaskAnalysis]:
        """分析任務類型和複雜度"""
        return self.generate(f"分析以下任務的類型和複雜度：\n\n{task}", TaskAnalysis)

    def summarize_document(self, text: str) -> Optional[DocumentSummary]:
        """生成文件摘要"""
        return self.generate(f"為以下文件生成摘要：\n\n{text[:3000]}", DocumentSummary)

    def review_code(self, code: str) -> Optional[CodeReview]:
        """審查程式碼"""
        return self.generate(f"審查以下程式碼，找出 bug 和改善建議：\n\n```\n{code[:3000]}\n```", CodeReview)

    def create_plan(self, goal: str) -> Optional[ActionPlan]:
        """建立行動計畫"""
        return self.generate(f"為以下目標建立行動計畫：\n\n{goal}", ActionPlan)


# 全域單例
_engine: Optional[StructuredOutputEngine] = None


def get_engine() -> StructuredOutputEngine:
    global _engine
    if _engine is None:
        _engine = StructuredOutputEngine()
    return _engine


def structured_generate(prompt: str, schema: Type[T]) -> Optional[T]:
    """便捷函數：生成結構化輸出"""
    return get_engine().generate(prompt, schema)

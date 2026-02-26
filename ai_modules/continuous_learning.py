# -*- coding: utf-8 -*-
"""
築未科技 — Continuous Learning 持續學習系統
借鑑 ECC /learn hook，從工作 session 自動提煉可重用 pattern

機制：
1. Session 結束時分析對話歷史
2. 用 LLM 提煉出可重用的 pattern
3. 自動儲存為 Microagent 知識檔案
4. 下次遇到類似問題時自動觸發

用法：
    from ai_modules.continuous_learning import learner

    # session 結束時呼叫
    new_skills = learner.extract_from_session(messages)

    # 手動教學
    learner.learn("鋼筋搭接規範", content="...", triggers=["鋼筋", "搭接"])
"""
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger("ai_modules.continuous_learning")


@dataclass
class LearnedPattern:
    """提煉出的 pattern"""
    name: str
    content: str
    triggers: List[str]
    source_session: str = ""
    confidence: float = 0.5
    use_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: str = ""
    category: str = ""            # construction / water_alert / general


class ContinuousLearner:
    """
    持續學習引擎

    功能：
    1. 從對話 session 提煉可重用 pattern
    2. 儲存為 Microagent .md 檔案
    3. 管理已學習的 pattern（增刪改查）
    4. 信心度衰減（長期不用的 pattern 降權）
    """

    EXTRACT_PROMPT = """分析以下對話記錄，提煉出可重用的知識 pattern。

要求：
1. 找出這次對話中解決問題的關鍵知識或方法
2. 提煉成通用的、可在未來類似場景重用的知識片段
3. 為每個 pattern 定義觸發詞（中英文皆可）
4. 忽略閒聊和無價值的內容

回覆 JSON 格式：
```json
[
  {
    "name": "pattern-name-kebab-case",
    "category": "construction 或 water_alert 或 general",
    "triggers": ["觸發詞1", "觸發詞2"],
    "content": "完整的知識內容，包含步驟和注意事項",
    "confidence": 0.7
  }
]
```

如果沒有值得提煉的 pattern，回覆空陣列 `[]`。

對話記錄：
{session}"""

    def __init__(self, knowledge_dir: str = ""):
        if not knowledge_dir:
            knowledge_dir = os.path.join(
                os.environ.get("BRAIN_DATA_DIR", "brain_workspace"),
                "learned_patterns",
            )
        self.knowledge_dir = Path(knowledge_dir)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

        # 索引檔
        self._index_path = self.knowledge_dir / "index.json"
        self._index: Dict[str, dict] = {}
        self._load_index()

    def extract_from_session(self, messages: List[Dict],
                             session_id: str = "") -> List[LearnedPattern]:
        """
        從對話 session 提煉 pattern

        Args:
            messages: OpenAI 格式的 messages list
            session_id: session 識別碼

        Returns:
            提煉出的 pattern 列表
        """
        if len(messages) < 4:
            # 太短的對話不值得提煉
            return []

        # 過濾和格式化對話
        formatted = self._format_session(messages)
        if len(formatted) < 200:
            return []

        # 用 LLM 提煉
        patterns_data = self._llm_extract(formatted)
        if not patterns_data:
            return []

        results = []
        for data in patterns_data:
            name = data.get("name", "")
            if not name or name in self._index:
                continue

            pattern = LearnedPattern(
                name=name,
                content=data.get("content", ""),
                triggers=data.get("triggers", []),
                source_session=session_id,
                confidence=data.get("confidence", 0.5),
                category=data.get("category", "general"),
            )

            # 儲存
            self._save_pattern(pattern)
            results.append(pattern)

        if results:
            log.info(f"持續學習: 從 session 提煉出 {len(results)} 個 pattern: "
                     f"{[p.name for p in results]}")

        return results

    def learn(self, name: str, content: str, triggers: List[str] = None,
              category: str = "general", confidence: float = 0.8) -> LearnedPattern:
        """
        手動教學 — 直接新增一個 pattern

        Args:
            name: pattern 名稱（kebab-case）
            content: 知識內容
            triggers: 觸發詞列表
            category: 分類
            confidence: 信心度（手動教學預設較高）
        """
        pattern = LearnedPattern(
            name=name,
            content=content,
            triggers=triggers or [],
            confidence=confidence,
            category=category,
        )
        self._save_pattern(pattern)
        log.info(f"手動學習: {name} (triggers={triggers})")
        return pattern

    def forget(self, name: str) -> bool:
        """遺忘（刪除）一個 pattern"""
        if name not in self._index:
            return False

        md_path = self.knowledge_dir / f"{name}.md"
        if md_path.exists():
            md_path.unlink()

        del self._index[name]
        self._save_index()
        log.info(f"遺忘: {name}")
        return True

    def record_usage(self, name: str):
        """記錄一次使用（提升信心度）"""
        if name in self._index:
            self._index[name]["use_count"] = self._index[name].get("use_count", 0) + 1
            self._index[name]["last_used"] = datetime.now().isoformat()
            # 信心度微增
            conf = self._index[name].get("confidence", 0.5)
            self._index[name]["confidence"] = min(1.0, conf + 0.05)
            self._save_index()

    def list_patterns(self, category: str = "") -> List[dict]:
        """列出所有已學習的 pattern"""
        patterns = list(self._index.values())
        if category:
            patterns = [p for p in patterns if p.get("category") == category]
        return sorted(patterns, key=lambda p: p.get("confidence", 0), reverse=True)

    def get_pattern(self, name: str) -> Optional[dict]:
        """取得 pattern 詳情"""
        return self._index.get(name)

    def get_stats(self) -> dict:
        """取得學習統計"""
        patterns = list(self._index.values())
        categories = {}
        for p in patterns:
            cat = p.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_patterns": len(patterns),
            "by_category": categories,
            "total_uses": sum(p.get("use_count", 0) for p in patterns),
            "avg_confidence": round(
                sum(p.get("confidence", 0) for p in patterns) / max(len(patterns), 1), 2
            ),
        }

    def decay_confidence(self, days_threshold: int = 30, decay_rate: float = 0.05):
        """
        信心度衰減 — 長期不用的 pattern 降權

        建議每日執行一次
        """
        now = datetime.now()
        decayed = 0

        for name, info in self._index.items():
            last_used = info.get("last_used", info.get("created_at", ""))
            if not last_used:
                continue
            try:
                last_dt = datetime.fromisoformat(last_used)
                days_since = (now - last_dt).days
                if days_since > days_threshold:
                    old_conf = info.get("confidence", 0.5)
                    new_conf = max(0.1, old_conf - decay_rate)
                    info["confidence"] = round(new_conf, 2)
                    decayed += 1
            except Exception:
                pass

        if decayed > 0:
            self._save_index()
            log.info(f"信心度衰減: {decayed} 個 pattern")

    def sync_to_microagents(self, target_dir: str = ""):
        """
        將已學習的 pattern 同步到 Microagent 知識目錄

        讓 MicroagentManager 可以載入並自動注入
        """
        if not target_dir:
            target_dir = os.path.join(
                os.environ.get("BRAIN_DATA_DIR", "brain_workspace"),
                "microagents",
            )
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)

        count = 0
        for name, info in self._index.items():
            if info.get("confidence", 0) < 0.3:
                continue  # 太低信心度不同步

            md_path = self.knowledge_dir / f"{name}.md"
            if not md_path.exists():
                continue

            # 複製到 microagent 目錄
            content = md_path.read_text(encoding="utf-8")
            dest = target / f"learned-{name}.md"
            dest.write_text(content, encoding="utf-8")
            count += 1

        log.info(f"同步到 Microagent: {count} 個 pattern → {target_dir}")

    # ===== 內部 =====

    def _format_session(self, messages: List[Dict], max_chars: int = 8000) -> str:
        """格式化 session 為文字"""
        parts = []
        total = 0

        for msg in messages:
            role = msg.get("role", "")
            if role == "system":
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    p.get("text", "") if isinstance(p, dict) else str(p)
                    for p in content
                )
            if not content:
                continue

            # 截斷過長的單條
            if len(content) > 1000:
                content = content[:1000] + "..."

            line = f"[{role}]: {content}"
            if total + len(line) > max_chars:
                break
            parts.append(line)
            total += len(line)

        return "\n".join(parts)

    def _llm_extract(self, session_text: str) -> List[dict]:
        """用 LLM 提煉 pattern"""
        prompt = self.EXTRACT_PROMPT.format(session=session_text)

        try:
            import requests
            ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            model = os.environ.get("CB_LLM_MODEL", "qwen3:8b")

            resp = requests.post(
                f"{ollama_base}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 1000},
                },
                timeout=60,
            )
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                # 清理 thinking tags
                if "<think>" in text:
                    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
                # 提取 JSON
                m = re.search(r'\[.*\]', text, re.DOTALL)
                if m:
                    return json.loads(m.group(0))
        except Exception as e:
            log.warning(f"LLM pattern 提煉失敗: {e}")

        return []

    def _save_pattern(self, pattern: LearnedPattern):
        """儲存 pattern 為 .md 檔案 + 更新索引"""
        # 生成 Microagent 格式 .md
        triggers_str = json.dumps(pattern.triggers, ensure_ascii=False)
        md_content = f"""---
name: {pattern.name}
type: knowledge
triggers: {triggers_str}
category: {pattern.category}
confidence: {pattern.confidence}
---

{pattern.content}
"""
        md_path = self.knowledge_dir / f"{pattern.name}.md"
        md_path.write_text(md_content, encoding="utf-8")

        # 更新索引
        self._index[pattern.name] = {
            "name": pattern.name,
            "triggers": pattern.triggers,
            "category": pattern.category,
            "confidence": pattern.confidence,
            "use_count": pattern.use_count,
            "created_at": pattern.created_at,
            "last_used": pattern.last_used,
            "source_session": pattern.source_session,
        }
        self._save_index()

    def _load_index(self):
        """載入索引"""
        if self._index_path.exists():
            try:
                self._index = json.loads(self._index_path.read_text(encoding="utf-8"))
            except Exception:
                self._index = {}

    def _save_index(self):
        """儲存索引"""
        self._index_path.write_text(
            json.dumps(self._index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# 全局單例
learner = ContinuousLearner()

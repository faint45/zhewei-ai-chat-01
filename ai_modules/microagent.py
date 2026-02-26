# -*- coding: utf-8 -*-
"""
築未科技 — Microagent 輕量知識注入系統
借鑑 OpenHands Microagent 模式，根據關鍵字自動注入專業知識到 LLM context

三種類型：
1. RepoMicroagent — 專案層級，永遠注入（如 CLAUDE.md）
2. KnowledgeMicroagent — 關鍵字觸發（如提到「鋼筋」→ 自動注入鋼筋規範）
3. TaskMicroagent — 用戶主動觸發（/daily-report, /safety-check）

知識檔案格式：.md + YAML frontmatter
---
name: reinforcement-standards
type: knowledge
triggers: ["鋼筋", "rebar", "配筋", "搭接"]
---
## 鋼筋施工規範
...

用法：
    from ai_modules.microagent import microagent_manager

    # 載入知識庫
    microagent_manager.load_from_dir("knowledge/microagents/")

    # 根據用戶訊息自動注入
    injected = microagent_manager.inject(messages, user_message="鋼筋搭接長度多少？")
"""
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger("ai_modules.microagent")


class MicroagentType(Enum):
    REPO = "repo"              # 永遠注入
    KNOWLEDGE = "knowledge"    # 關鍵字觸發
    TASK = "task"              # /command 觸發


@dataclass
class Microagent:
    """輕量知識 Agent"""
    name: str
    content: str                      # Markdown 內容（不含 frontmatter）
    type: MicroagentType = MicroagentType.KNOWLEDGE
    triggers: List[str] = field(default_factory=list)
    description: str = ""
    source: str = ""                  # 檔案路徑
    priority: int = 0                 # 0=正常, 1=高, -1=低

    def match_trigger(self, text: str) -> Optional[str]:
        """檢查文字是否匹配任何觸發詞"""
        text_lower = text.lower()
        for trigger in self.triggers:
            if trigger.lower() in text_lower:
                return trigger
        return None

    def to_system_message(self, triggered_by: str = "") -> str:
        """轉換為系統提示文字"""
        header = f"[知識注入: {self.name}]"
        if triggered_by:
            header += f" (觸發: {triggered_by})"
        return f"{header}\n{self.content}"


class MicroagentManager:
    """
    Microagent 管理器

    功能：
    1. 從目錄載入 .md 知識檔案
    2. 根據用戶訊息自動匹配觸發詞
    3. 注入匹配的知識到 LLM messages
    4. 去重（同一 session 不重複注入相同知識）
    """

    def __init__(self):
        self._repo_agents: Dict[str, Microagent] = {}
        self._knowledge_agents: Dict[str, Microagent] = {}
        self._task_agents: Dict[str, Microagent] = {}
        self._injected_this_session: set = set()  # 本 session 已注入的 agent name

    def load_from_dir(self, directory: str):
        """
        從目錄載入所有 .md 知識檔案

        Args:
            directory: 知識檔案目錄路徑
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            log.warning(f"Microagent 目錄不存在: {directory}")
            return

        count = 0
        for md_file in dir_path.rglob("*.md"):
            if md_file.name.lower() == "readme.md":
                continue
            try:
                agent = self._load_file(md_file)
                if agent:
                    self._register(agent)
                    count += 1
            except Exception as e:
                log.error(f"載入 microagent 失敗 {md_file}: {e}")

        log.info(f"Microagent 載入完成: {count} 個 "
                 f"(repo={len(self._repo_agents)}, "
                 f"knowledge={len(self._knowledge_agents)}, "
                 f"task={len(self._task_agents)})")

    def load_single(self, name: str, content: str, triggers: List[str] = None,
                    agent_type: MicroagentType = MicroagentType.KNOWLEDGE):
        """程式化註冊單個 microagent"""
        agent = Microagent(
            name=name, content=content, type=agent_type,
            triggers=triggers or [],
        )
        self._register(agent)

    def inject(self, messages: List[Dict], user_message: str = "",
               max_inject: int = 3) -> List[Dict]:
        """
        根據用戶訊息自動注入匹配的知識

        Args:
            messages: 現有的 messages list
            user_message: 用戶最新訊息
            max_inject: 最多注入幾個知識片段

        Returns:
            注入知識後的 messages list
        """
        if not user_message:
            # 從 messages 中取最後一條 user 訊息
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        user_message = content
                    break

        if not user_message:
            return messages

        injections = []

        # 1. Repo agents — 永遠注入（如果尚未注入）
        for name, agent in self._repo_agents.items():
            if name not in self._injected_this_session:
                injections.append((agent, "always-on"))
                self._injected_this_session.add(name)

        # 2. Task agents — 檢查 /command
        for name, agent in self._task_agents.items():
            trigger = agent.match_trigger(user_message)
            if trigger and name not in self._injected_this_session:
                injections.append((agent, trigger))
                self._injected_this_session.add(name)

        # 3. Knowledge agents — 關鍵字匹配
        for name, agent in self._knowledge_agents.items():
            if len(injections) >= max_inject:
                break
            trigger = agent.match_trigger(user_message)
            if trigger and name not in self._injected_this_session:
                injections.append((agent, trigger))
                self._injected_this_session.add(name)

        if not injections:
            return messages

        # 組合注入內容
        inject_content = "\n\n---\n\n".join(
            agent.to_system_message(trigger) for agent, trigger in injections
        )

        # 插入到 system message 之後
        result = list(messages)
        insert_idx = 0
        for i, msg in enumerate(result):
            if msg.get("role") == "system":
                insert_idx = i + 1
            else:
                break

        result.insert(insert_idx, {
            "role": "system",
            "content": inject_content,
        })

        log.info(f"Microagent 注入: {[a.name for a, _ in injections]}")
        return result

    def find_matches(self, text: str) -> List[Tuple[str, str]]:
        """找出所有匹配的知識（不注入，只查詢）"""
        matches = []
        for name, agent in self._knowledge_agents.items():
            trigger = agent.match_trigger(text)
            if trigger:
                matches.append((name, trigger))
        for name, agent in self._task_agents.items():
            trigger = agent.match_trigger(text)
            if trigger:
                matches.append((name, trigger))
        return matches

    def get_agent(self, name: str) -> Optional[Microagent]:
        """取得指定 agent"""
        return (self._repo_agents.get(name)
                or self._knowledge_agents.get(name)
                or self._task_agents.get(name))

    def list_agents(self) -> Dict[str, List[str]]:
        """列出所有 agent"""
        return {
            "repo": list(self._repo_agents.keys()),
            "knowledge": list(self._knowledge_agents.keys()),
            "task": list(self._task_agents.keys()),
        }

    def reset_session(self):
        """重設 session 狀態（清除已注入記錄）"""
        self._injected_this_session.clear()

    # ===== 內部 =====

    def _register(self, agent: Microagent):
        """註冊 agent"""
        if agent.type == MicroagentType.REPO:
            self._repo_agents[agent.name] = agent
        elif agent.type == MicroagentType.TASK:
            self._task_agents[agent.name] = agent
        else:
            self._knowledge_agents[agent.name] = agent

    def _load_file(self, path: Path) -> Optional[Microagent]:
        """從 .md 檔案載入 microagent"""
        content = path.read_text(encoding="utf-8")

        # 解析 YAML frontmatter
        metadata, body = self._parse_frontmatter(content)
        if not body.strip():
            return None

        name = metadata.get("name", path.stem)
        type_str = metadata.get("type", "knowledge")
        triggers = metadata.get("triggers", [])
        description = metadata.get("description", "")
        priority = metadata.get("priority", 0)

        # 推斷類型
        if type_str == "repo" or not triggers:
            agent_type = MicroagentType.REPO
        elif any(t.startswith("/") for t in triggers):
            agent_type = MicroagentType.TASK
        else:
            agent_type = MicroagentType.KNOWLEDGE

        return Microagent(
            name=name, content=body.strip(), type=agent_type,
            triggers=triggers, description=description,
            source=str(path), priority=priority,
        )

    @staticmethod
    def _parse_frontmatter(text: str) -> Tuple[dict, str]:
        """解析 YAML frontmatter"""
        if not text.startswith("---"):
            return {}, text

        parts = text.split("---", 2)
        if len(parts) < 3:
            return {}, text

        yaml_str = parts[1].strip()
        body = parts[2]

        # 簡易 YAML 解析（不依賴 PyYAML）
        metadata = {}
        for line in yaml_str.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()
                # 解析 list
                if val.startswith("[") and val.endswith("]"):
                    items = val[1:-1].split(",")
                    metadata[key] = [
                        i.strip().strip('"').strip("'") for i in items if i.strip()
                    ]
                elif val.lower() in ("true", "false"):
                    metadata[key] = val.lower() == "true"
                elif val.isdigit():
                    metadata[key] = int(val)
                else:
                    metadata[key] = val.strip('"').strip("'")

        return metadata, body


# 全局單例
microagent_manager = MicroagentManager()

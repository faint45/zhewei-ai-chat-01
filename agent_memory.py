# -*- coding: utf-8 -*-
"""
築未科技 Agent 記憶持久化模組
支援長期對話記憶、跨會話上下文、語意搜尋
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

MEMORY_DIR = Path("brain_workspace/agent_memory")
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

class AgentMemory:
    """Agent 記憶管理器"""

    def __init__(self, agent_id: str = "default"):
        self.agent_id = agent_id
        self.memory_file = MEMORY_DIR / f"{agent_id}_memory.jsonl"
        self.summary_file = MEMORY_DIR / f"{agent_id}_summary.json"
        self._init_storage()

    def _init_storage(self):
        """初始化儲存"""
        if not self.memory_file.exists():
            self.memory_file.touch()
        if not self.summary_file.exists():
            self._save_summary({
                "last_updated": None,
                "total_sessions": 0,
                "total_interactions": 0,
                "key_topics": [],
                "user_preferences": {},
                "context_summary": ""
            })

    def _load_summary(self) -> Dict:
        """載入摘要"""
        try:
            with open(self.summary_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def _save_summary(self, data: Dict):
        """儲存摘要"""
        with open(self.summary_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def store_interaction(self, user_input: str, ai_response: str, 
                          session_id: str = None, metadata: Dict = None):
        """儲存單次互動"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id or self._get_session_id(),
            "user_input": user_input,
            "ai_response": ai_response,
            "metadata": metadata or {}
        }
        
        with open(self.memory_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        # 更新摘要
        self._update_summary(user_input)

    def _get_session_id(self) -> str:
        """取得會話 ID"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _update_summary(self, user_input: str):
        """更新摘要"""
        summary = self._load_summary()
        summary["last_updated"] = datetime.now().isoformat()
        summary["total_interactions"] = summary.get("total_interactions", 0) + 1
        
        # 提取關鍵詞（簡化版）
        keywords = self._extract_keywords(user_input)
        summary["key_topics"] = list(set(summary.get("key_topics", []) + keywords))[-20:]
        
        self._save_summary(summary)

    def _extract_keywords(self, text: str) -> List[str]:
        """提取關鍵詞"""
        # 簡化的關鍵詞提取
        stopwords = {"的", "是", "在", "了", "和", "與", "或", "及", "等", "請", "幫", "我", "你", "他"}
        words = [w for w in text if len(w) > 1 and w not in stopwords]
        return words[:10]

    def get_recent_context(self, limit: int = 10) -> List[Dict]:
        """取得最近上下文"""
        interactions = []
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-limit:]
                for line in lines:
                    if line.strip():
                        interactions.append(json.loads(line))
        except:
            pass
        return interactions

    def get_session_history(self, session_id: str) -> List[Dict]:
        """取得特定會話的歷史"""
        interactions = []
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        if record.get("session_id") == session_id:
                            interactions.append(record)
        except:
            pass
        return interactions

    def get_context_summary(self) -> str:
        """取得上下文摘要"""
        summary = self._load_summary()
        return summary.get("context_summary", "")

    def update_user_preference(self, key: str, value):
        """更新用戶偏好"""
        summary = self._load_summary()
        if "user_preferences" not in summary:
            summary["user_preferences"] = {}
        summary["user_preferences"][key] = value
        self._save_summary(summary)

    def get_user_preferences(self) -> Dict:
        """取得用戶偏好"""
        summary = self._load_summary()
        return summary.get("user_preferences", {})

    def clear_session(self, session_id: str = None):
        """清除會話"""
        if session_id:
            # 保留其他會話
            remaining = []
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        if record.get("session_id") != session_id:
                            remaining.append(line)
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                f.writelines(remaining)
        else:
            # 清除全部
            self.memory_file.write_text("")

    def search_memory(self, query: str, limit: int = 5) -> List[Dict]:
        """搜尋記憶"""
        results = []
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip() and query in line:
                        record = json.loads(line)
                        results.append(record)
                        if len(results) >= limit:
                            break
        except:
            pass
        return results


# 全域記憶管理器
def get_agent_memory(agent_id: str = "default") -> AgentMemory:
    return AgentMemory(agent_id)


# 便捷函數
def store_conversation(agent_id: str, user_input: str, ai_response: str, **kwargs):
    """儲存對話"""
    memory = get_agent_memory(agent_id)
    memory.store_interaction(user_input, ai_response, **kwargs)


def get_conversation_context(agent_id: str, limit: int = 10) -> List[Dict]:
    """取得對話上下文"""
    memory = get_agent_memory(agent_id)
    return memory.get_recent_context(limit)


if __name__ == "__main__":
    # 測試
    memory = AgentMemory("test_agent")
    memory.store_interaction("你好", "你好！我是 Jarvis。")
    memory.store_interaction("今天天氣如何？", "今天天氣晴朗。")
    
    print("=== 最近上下文 ===")
    for ctx in memory.get_recent_context(5):
        print(f"User: {ctx['user_input']}")
        print(f"AI: {ctx['ai_response']}")
        print("---")

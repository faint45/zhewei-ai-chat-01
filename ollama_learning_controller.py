# -*- coding: utf-8 -*-
"""
築未科技 — Ollama 學習控制模組
讓 AI 協助控制本地 Ollama 模型進行學習

功能：
- 模型訓練狀態監控
- 自動化學習流程
- 學習內容萃取與儲存
"""

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Callable
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

class OllamaLearningController:
    """
    Ollama 學習控制器
    協助用戶控制本地模型進行學習
    """
    
    def __init__(self, stream_callback: Optional[Callable] = None):
        self.base_url = OLLAMA_BASE_URL
        self.stream_callback = stream_callback
        self.active_learnings: dict[str, dict] = {}  # 進行中的學習任務
        
    async def check_status(self) -> dict:
        """檢查 Ollama 服務狀態"""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
                return {
                    "status": "online",
                    "models": data.get("models", []),
                    "count": len(data.get("models", [])),
                }
        except urllib.error.URLError as e:
            return {
                "status": "offline",
                "error": f"無法連接 Ollama: {str(e)}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }
    
    async def learn_topic(
        self,
        topic: str,
        session_id: str,
        depth: str = "standard",  # quick, standard, deep
        sources: list[str] = None
    ) -> dict:
        """
        學習新主題
        
        流程：
        1. 分析主題範圍
        2. 查詢現有知識庫
        3. 產生學習計劃
        4. 執行多輪學習
        5. 萃取精華儲存
        """
        learning_id = f"learn_{session_id}_{int(time.time())}"
        
        self.active_learnings[learning_id] = {
            "id": learning_id,
            "topic": topic,
            "status": "started",
            "progress": 0,
            "started_at": time.time(),
            "results": [],
        }
        
        await self._emit({
            "stage": "learning_init",
            "message": f"📚 初始化學習任務: {topic}",
            "learning_id": learning_id,
        })
        
        try:
            # Step 1: 分析主題
            await self._emit({
                "stage": "analysis",
                "message": "🔍 分析主題範圍與關鍵概念...",
                "progress": 10,
            })
            
            topic_analysis = await self._analyze_topic(topic)
            
            # Step 2: 查詢知識庫
            await self._emit({
                "stage": "knowledge_check",
                "message": "📖 檢查現有知識庫...",
                "progress": 20,
            })
            
            existing_knowledge = await self._check_existing_knowledge(topic)
            
            # Step 3: 產生學習計劃
            await self._emit({
                "stage": "planning",
                "message": "📋 產生個性化學習計劃...",
                "progress": 30,
            })
            
            learning_plan = await self._generate_learning_plan(
                topic, topic_analysis, existing_knowledge, depth
            )
            
            # Step 4: 執行學習
            total_subtopics = len(learning_plan.get("subtopics", []))
            
            for idx, subtopic in enumerate(learning_plan.get("subtopics", [])):
                progress = 30 + (idx / max(total_subtopics, 1)) * 50
                
                await self._emit({
                    "stage": "learning_subtopic",
                    "message": f"🧠 學習 [{idx+1}/{total_subtopics}]: {subtopic['title']}",
                    "progress": int(progress),
                    "subtopic": subtopic,
                })
                
                # 使用本地 Ollama 進行學習
                learning_result = await self._learn_with_ollama(subtopic)
                
                # 精修萃取
                await self._emit({
                    "stage": "extracting",
                    "message": f"✨ 萃取知識精華...",
                    "progress": int(progress + 5),
                })
                
                essence = await self._extract_essence(learning_result, subtopic)
                
                self.active_learnings[learning_id]["results"].append({
                    "subtopic": subtopic,
                    "essence": essence,
                })
                
                # 儲存到知識庫
                await self._store_knowledge(topic, subtopic, essence)
            
            # Step 5: 完成
            self.active_learnings[learning_id]["status"] = "completed"
            self.active_learnings[learning_id]["completed_at"] = time.time()
            
            await self._emit({
                "stage": "completed",
                "message": f"🎉 學習完成！已學習 {total_subtopics} 個子主題",
                "progress": 100,
                "summary": {
                    "topic": topic,
                    "subtopics_learned": total_subtopics,
                    "duration_seconds": int(time.time() - self.active_learnings[learning_id]["started_at"]),
                },
            })
            
            return {
                "ok": True,
                "learning_id": learning_id,
                "topic": topic,
                "subtopics": total_subtopics,
                "results": self.active_learnings[learning_id]["results"],
            }
            
        except Exception as e:
            self.active_learnings[learning_id]["status"] = "failed"
            self.active_learnings[learning_id]["error"] = str(e)
            
            await self._emit({
                "stage": "failed",
                "message": f"❌ 學習失敗: {str(e)}",
                "error": str(e),
            })
            
            return {
                "ok": False,
                "error": str(e),
                "learning_id": learning_id,
            }
    
    async def _analyze_topic(self, topic: str) -> dict:
        """分析主題範圍"""
        # 這裡可以整合外部 AI 進行主題分析
        # 暫時使用簡單的結構化輸出
        return {
            "topic": topic,
            "domain": self._detect_domain(topic),
            "complexity": "medium",
            "estimated_subtopics": 3,
        }
    
    def _detect_domain(self, topic: str) -> str:
        """檢測主題領域"""
        topic_lower = topic.lower()
        domains = {
            "programming": ["code", "程式", "python", "javascript", "開發", "api"],
            "construction": ["營建", "工程", "建築", "施工", "土木", "結構"],
            "business": ["商業", "管理", "行銷", "營運", "策略"],
            "science": ["科學", "物理", "化學", "生物", "研究"],
            "technology": ["科技", "ai", "機器學習", "區塊鏈", "雲端"],
        }
        
        for domain, keywords in domains.items():
            if any(kw in topic_lower for kw in keywords):
                return domain
        return "general"
    
    async def _check_existing_knowledge(self, topic: str) -> list:
        """檢查知識庫中是否已有相關知識"""
        try:
            # 嘗試導入並查詢知識庫
            import sys
            sys.path.insert(0, str(ROOT))
            from jarvis_brain import search_knowledge
            
            results = search_knowledge(topic, top_k=3)
            return results
        except Exception:
            return []
    
    async def _generate_learning_plan(
        self,
        topic: str,
        analysis: dict,
        existing: list,
        depth: str
    ) -> dict:
        """產生學習計劃"""
        # 使用 Ollama 生成學習計劃
        prompt = f"""請為主題「{topic}」產生一個學習計劃。

領域: {analysis['domain']}
深度: {depth}
已有知識: {len(existing)} 條相關記錄

請輸出 JSON 格式:
{{
    "overview": "主題概述",
    "subtopics": [
        {{"title": "子主題1", "key_points": ["要點1", "要點2"]}},
        {{"title": "子主題2", "key_points": ["要點1", "要點2"]}}
    ]
}}

子主題數量: {3 if depth == 'quick' else 5 if depth == 'standard' else 8}"""

        messages = [
            {"role": "system", "content": "你是一個學習規劃專家。請產生結構化的學習計劃。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            from ai_service import OllamaService
            ollama = OllamaService()
            response = await ollama.chat(messages)
            
            # 嘗試解析 JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass
        
        # 回退到預設計劃
        return {
            "overview": f"學習 {topic} 的基礎知識",
            "subtopics": [
                {"title": f"{topic} 基礎概念", "key_points": ["定義", "背景"]},
                {"title": f"{topic} 核心原理", "key_points": ["原理1", "原理2"]},
                {"title": f"{topic} 實際應用", "key_points": ["應用場景", "案例"]},
            ],
        }
    
    async def _learn_with_ollama(self, subtopic: dict) -> str:
        """使用 Ollama 學習子主題"""
        prompt = f"""請詳細解釋「{subtopic['title']}」。

關鍵要點:
{chr(10).join('- ' + kp for kp in subtopic.get('key_points', []))}

請提供:
1. 核心概念解釋
2. 詳細說明
3. 實際例子
4. 相關知識連結"""

        messages = [
            {"role": "system", "content": "你是一個專業的知識講師，請詳細且清晰地解釋知識點。"},
            {"role": "user", "content": prompt}
        ]
        
        from ai_service import OllamaService
        ollama = OllamaService()
        return await ollama.chat(messages)
    
    async def _extract_essence(self, content: str, subtopic: dict) -> str:
        """萃取知識精華"""
        prompt = f"""請將以下內容萃取成知識精華（3-5 個重點）。

主題: {subtopic['title']}
內容:
{content[:2000]}  # 限制長度

請輸出簡潔的精華摘要，每個重點一行。"""

        messages = [
            {"role": "system", "content": "你是一個知識萃取專家。請提取核心重點，去除冗餘。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            from ai_service import OllamaService
            ollama = OllamaService()
            return await ollama.chat(messages)
        except Exception:
            # 如果萃取失敗，返回前 500 字作為精華
            return content[:500] + "..."
    
    async def _store_knowledge(self, topic: str, subtopic: dict, essence: str):
        """儲存知識到知識庫"""
        try:
            import sys
            sys.path.insert(0, str(ROOT))
            from local_learning_system import add_knowledge
            
            question = f"{topic} - {subtopic['title']} 是什麼？"
            add_knowledge(question, essence, source="ollama_learning")
        except Exception as e:
            print(f"儲存知識失敗: {e}")
    
    async def _emit(self, data: dict):
        """發送進度更新"""
        if self.stream_callback:
            await self.stream_callback(data)
    
    def get_learning_status(self, learning_id: str) -> dict:
        """取得學習任務狀態"""
        return self.active_learnings.get(learning_id, {"status": "not_found"})

# 便捷函數
async def quick_learn(topic: str, stream_callback: Optional[Callable] = None) -> dict:
    """快速學習一個主題"""
    controller = OllamaLearningController(stream_callback)
    return await controller.learn_topic(topic, "quick_session", depth="quick")

# 測試
if __name__ == "__main__":
    async def test():
        async def print_progress(data):
            print(f"[{data.get('stage')}] {data.get('message')}")
        
        controller = OllamaLearningController(print_progress)
        
        # 檢查狀態
        status = await controller.check_status()
        print(f"Ollama 狀態: {status}")
        
        # 學習測試
        if status['status'] == 'online':
            result = await controller.learn_topic(
                "FastAPI WebSocket 即時通訊",
                "test_session",
                depth="quick"
            )
            print(f"\n學習結果: {result}")
    
    asyncio.run(test())

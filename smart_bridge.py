# -*- coding: utf-8 -*-
"""
築未科技 — Smart Bridge 智慧型對話橋接服務
Port: 8003

功能：
1. 外網可訪問的即時對話界面 (WebSocket)
2. 視覺化顯示 AI 運作過程（思考 → 執行 → 優化）
3. 智慧型控制 API：兩階段生成（低成本80% + 高品質精修）
4. 本地 Ollama 模型學習控制與協助

架構：
- Phase 1 (80%): Ollama 本地模型 / Groq 免費模型 快速建立框架
- Phase 2 (20%): Gemini / Claude 高品質精修與優化
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx
import uvicorn

# 載入環境變數
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

# 引入現有 AI 服務
from ai_service import SmartAIService, OllamaService, GeminiService, ClaudeService, AIServiceFactory

# 引入 Ollama 學習控制器
try:
    from ollama_learning_controller import OllamaLearningController
    LEARNING_AVAILABLE = True
except ImportError:
    LEARNING_AVAILABLE = False
    print("⚠️ OllamaLearningController 未載入")

# ── Config ──────────────────────────────────────────────
PORT = int(os.environ.get("SMART_BRIDGE_PORT", "8003"))
HOST = os.environ.get("SMART_BRIDGE_HOST", "0.0.0.0")
BRIDGE_WORKSPACE = ROOT / "bridge_workspace"
BRIDGE_WORKSPACE.mkdir(exist_ok=True)
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11460")

# 兩階段模型配置
PHASE1_PROVIDERS = ["ollama", "groq"]  # 低成本快速生成
PHASE2_PROVIDERS = ["gemini", "claude"]  # 高品質精修

# 成本估計（每 1K tokens）
COST_RATES = {
    "ollama": 0.0,      # 本地免費
    "groq": 0.0,        # 免費額度
    "gemini": 0.0005,   # $0.5 / 1M tokens
    "claude": 0.003,    # $3 / 1M tokens
}

# ── 專案管理 ────────────────────────────────────────────
class ProjectManager:
    """專案管理器：支援多專案獨立開發 + 智慧同步"""
    
    def __init__(self):
        self.projects_dir = BRIDGE_WORKSPACE / "projects"
        self.projects_dir.mkdir(exist_ok=True)
        self._projects_file = self.projects_dir / "projects.json"
        self._lock_file = self.projects_dir / ".lock"
        self._last_sync_time = None
        self._load()
    
    def _acquire_lock(self, timeout=5):
        """取得檔案鎖（避免多個實例同時寫入）"""
        start_time = time.time()
        while self._lock_file.exists():
            if time.time() - start_time > timeout:
                # 超時則強制移除鎖（可能是異常退出導致）
                self._lock_file.unlink()
                break
            time.sleep(0.1)
        self._lock_file.touch()
    
    def _release_lock(self):
        """釋放檔案鎖"""
        if self._lock_file.exists():
            self._lock_file.unlink()
    
    def _load(self):
        """載入專案列表（智慧合併遠端與本地變更）"""
        if self._projects_file.exists():
            try:
                disk_data = json.loads(self._projects_file.read_text(encoding="utf-8"))
                
                # 首次載入或需要同步
                if not hasattr(self, 'projects') or self._should_sync():
                    self.projects = disk_data
                    self._last_sync_time = time.time()
                else:
                    # 智慧合併：保留記憶體中較新的資料
                    self._merge_projects(disk_data)
            except Exception as e:
                print(f"⚠️ 載入專案失敗: {e}")
                self._init_default_project()
        else:
            self._init_default_project()
    
    def _init_default_project(self):
        """初始化預設專案"""
        self.projects = {
            "default": {
                "id": "default",
                "name": "預設專案",
                "description": "Smart Bridge 預設工作區",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "color": "cyan",
                "icon": "cube",
                "history": [],
                "context": {},
                "stats": {"messages": 0, "tokens": 0, "cost": 0.0}
            }
        }
        self._save()
    
    def _should_sync(self):
        """判斷是否需要同步（每 5 秒檢查一次）"""
        if not self._last_sync_time:
            return True
        return time.time() - self._last_sync_time > 5
    
    def _merge_projects(self, disk_data: dict):
        """智慧合併專案資料（以 updated_at 時間戳為準）"""
        merged = {}
        all_ids = set(self.projects.keys()) | set(disk_data.keys())
        
        for pid in all_ids:
            mem_proj = self.projects.get(pid)
            disk_proj = disk_data.get(pid)
            
            if not disk_proj:
                # 僅存在記憶體中（新建立的）
                merged[pid] = mem_proj
            elif not mem_proj:
                # 僅存在磁碟中（其他實例建立的）
                merged[pid] = disk_proj
            else:
                # 兩邊都有，比較時間戳
                mem_time = mem_proj.get("updated_at", "")
                disk_time = disk_proj.get("updated_at", "")
                
                if mem_time >= disk_time:
                    merged[pid] = mem_proj
                else:
                    # 磁碟較新，但保留記憶體中未儲存的訊息
                    merged[pid] = disk_proj
                    if len(mem_proj.get("history", [])) > len(disk_proj.get("history", [])):
                        merged[pid]["history"] = mem_proj["history"]
                        merged[pid]["stats"] = mem_proj["stats"]
        
        self.projects = merged
        self._last_sync_time = time.time()
    
    def _save(self):
        """儲存專案列表（帶檔案鎖）"""
        try:
            self._acquire_lock()
            
            # 儲存前先重新載入，確保不覆蓋其他實例的變更
            if self._projects_file.exists():
                disk_data = json.loads(self._projects_file.read_text(encoding="utf-8"))
                self._merge_projects(disk_data)
            
            # 寫入檔案
            self._projects_file.write_text(
                json.dumps(self.projects, ensure_ascii=False, indent=2), 
                encoding="utf-8"
            )
            self._last_sync_time = time.time()
        finally:
            self._release_lock()
    
    def sync(self):
        """手動同步（重新載入磁碟資料）"""
        self._load()
        return {"ok": True, "synced_at": datetime.now().isoformat()}
    
    def list(self):
        """列出所有專案"""
        return list(self.projects.values())
    
    def get(self, project_id: str):
        """取得專案"""
        return self.projects.get(project_id)
    
    def create(self, name: str, description: str = "", color: str = "purple", icon: str = "folder"):
        """建立新專案"""
        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        self.projects[project_id] = {
            "id": project_id,
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "color": color,
            "icon": icon,
            "history": [],
            "context": {},
            "stats": {"messages": 0, "tokens": 0, "cost": 0.0}
        }
        self._save()
        return self.projects[project_id]
    
    def update(self, project_id: str, **kwargs):
        """更新專案"""
        if project_id in self.projects:
            self.projects[project_id].update(kwargs)
            self.projects[project_id]["updated_at"] = datetime.now().isoformat()
            self._save()
            return self.projects[project_id]
        return None
    
    def delete(self, project_id: str):
        """刪除專案"""
        if project_id in self.projects and project_id != "default":
            del self.projects[project_id]
            self._save()
            return True
        return False
    
    def add_message(self, project_id: str, role: str, content: str, metadata: dict = None):
        """新增訊息到專案歷史"""
        if project_id in self.projects:
            msg = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            self.projects[project_id]["history"].append(msg)
            self.projects[project_id]["stats"]["messages"] += 1
            self._save()
            return msg
        return None
    
    def clear_history(self, project_id: str):
        """清除專案對話歷史"""
        if project_id in self.projects:
            self.projects[project_id]["history"] = []
            self.projects[project_id]["stats"]["messages"] = 0
            self._save()
            return True
        return False
    
    def export_project(self, project_id: str):
        """匯出單個專案"""
        project = self.projects.get(project_id)
        if not project:
            return None
        return project
    
    def export_all(self):
        """匯出所有專案"""
        return self.projects
    
    def import_projects(self, data: dict, mode: str = "skip"):
        """
        匯入專案資料
        mode: 'skip' (跳過已存在), 'overwrite' (覆蓋), 'merge' (合併歷史)
        """
        imported = []
        skipped = []
        errors = []
        
        # 支援單個專案或多個專案
        if isinstance(data, dict):
            if "id" in data and "name" in data:
                # 單個專案
                projects_to_import = {data["id"]: data}
            else:
                # 多個專案
                projects_to_import = data
        else:
            return {"ok": False, "error": "無效的資料格式"}
        
        for pid, project_data in projects_to_import.items():
            try:
                # 驗證必要欄位
                if not all(k in project_data for k in ["id", "name"]):
                    errors.append({"id": pid, "error": "缺少必要欄位"})
                    continue
                
                # 檢查是否已存在
                exists = pid in self.projects
                
                if exists:
                    if mode == "skip":
                        skipped.append(pid)
                        continue
                    elif mode == "overwrite":
                        self.projects[pid] = project_data
                        self.projects[pid]["updated_at"] = datetime.now().isoformat()
                        imported.append(pid)
                    elif mode == "merge":
                        # 合併歷史訊息
                        existing = self.projects[pid]
                        existing_history = existing.get("history", [])
                        import_history = project_data.get("history", [])
                        
                        # 合併並去重（根據 timestamp）
                        all_history = existing_history + import_history
                        unique_history = []
                        seen_timestamps = set()
                        for msg in sorted(all_history, key=lambda x: x.get("timestamp", "")):
                            ts = msg.get("timestamp")
                            if ts not in seen_timestamps:
                                unique_history.append(msg)
                                seen_timestamps.add(ts)
                        
                        self.projects[pid]["history"] = unique_history
                        self.projects[pid]["stats"]["messages"] = len(unique_history)
                        self.projects[pid]["updated_at"] = datetime.now().isoformat()
                        imported.append(pid)
                else:
                    # 新專案
                    self.projects[pid] = project_data
                    self.projects[pid]["updated_at"] = datetime.now().isoformat()
                    imported.append(pid)
            
            except Exception as e:
                errors.append({"id": pid, "error": str(e)})
        
        self._save()
        
        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
            "total": len(imported) + len(skipped) + len(errors)
        }

project_manager = ProjectManager()

# ── App ─────────────────────────────────────────────────
app = FastAPI(
    title="築未科技 Smart Bridge",
    description="智慧型對話橋接服務 - 外網對話 + 本地模型學習控制 + 多專案管理",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 AI 服務
smart_ai = SmartAIService()
ollama_ai = smart_ai.ollama
gemini_ai = smart_ai.gemini
claude_ai = smart_ai.claude

# WebSocket 連線管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.sessions: dict[str, dict] = {}  # session_id -> {history, context}
    
    async def connect(self, websocket: WebSocket, session_id: str) -> str:
        await websocket.accept()
        self.active_connections[session_id] = websocket
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": [],
                "context": {},
                "created_at": datetime.now().isoformat(),
            }
        return session_id
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_to_session(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception:
                self.disconnect(session_id)
    
    async def broadcast_operation(self, session_id: str, operation: dict):
        """廣播 AI 運作過程"""
        msg = {
            "type": "operation",
            "timestamp": datetime.now().isoformat(),
            **operation
        }
        await self.send_to_session(session_id, msg)

manager = ConnectionManager()

# ── Smart Bridge Core ───────────────────────────────────
class SmartBridgeCore:
    """
    智慧型橋接核心：兩階段生成 + 即時視覺反饋
    """
    
    def __init__(self):
        self.cost_stats = {
            "total_requests": 0,
            "phase1_tokens": 0,
            "phase2_tokens": 0,
            "estimated_cost": 0.0,
            "saved_cost": 0.0,  # 相比全用高品質模型
        }
    
    async def two_phase_generate(
        self,
        prompt: str,
        session_id: str,
        task_type: str = "code",
        stream_callback: Optional[Callable] = None
    ) -> dict:
        """
        兩階段智慧生成：
        Phase 1: 低成本模型快速生成 80% 框架
        Phase 2: 高品質模型精修優化 20%
        
        即時 stream 運作過程到前端顯示
        """
        start_time = time.time()
        
        # ── Phase 1: 快速框架 (80%) ─────────────────────
        if stream_callback:
            await stream_callback({
                "stage": "phase1_start",
                "message": "🚀 Phase 1: 低成本模型建立框架...",
                "providers": PHASE1_PROVIDERS,
                "estimated_progress": 0,
            })
        
        phase1_result = await self._phase1_generate(prompt, task_type, stream_callback, session_id)
        
        if stream_callback:
            await stream_callback({
                "stage": "phase1_complete",
                "message": f"✅ Phase 1 完成 ({phase1_result['provider']})",
                "duration_ms": phase1_result['duration_ms'],
                "tokens": phase1_result['tokens'],
                "progress": 80,
            })
        
        # ── Phase 2: 精修優化 (20%) ─────────────────────
        if stream_callback:
            await stream_callback({
                "stage": "phase2_start",
                "message": "🎯 Phase 2: 高品質模型精修優化...",
                "providers": PHASE2_PROVIDERS,
                "estimated_progress": 80,
            })
        
        phase2_result = await self._phase2_optimize(
            prompt, phase1_result['content'], task_type, stream_callback, session_id
        )
        
        total_duration = int((time.time() - start_time) * 1000)
        
        # 成本計算
        phase1_cost = phase1_result['tokens'] * COST_RATES.get(phase1_result['provider'], 0) / 1000
        phase2_cost = phase2_result['tokens'] * COST_RATES.get(phase2_result['provider'], 0) / 1000
        total_cost = phase1_cost + phase2_cost
        
        # 如果全用高品質模型的估計成本
        full_quality_cost = (phase1_result['tokens'] + phase2_result['tokens']) * 0.003 / 1000
        saved = full_quality_cost - total_cost
        
        self.cost_stats["total_requests"] += 1
        self.cost_stats["phase1_tokens"] += phase1_result['tokens']
        self.cost_stats["phase2_tokens"] += phase2_result['tokens']
        self.cost_stats["estimated_cost"] += total_cost
        self.cost_stats["saved_cost"] += saved
        
        if stream_callback:
            await stream_callback({
                "stage": "complete",
                "message": f"🎉 完成！總耗時 {total_duration}ms，節省 ${saved:.4f}",
                "duration_ms": total_duration,
                "total_tokens": phase1_result['tokens'] + phase2_result['tokens'],
                "cost": total_cost,
                "saved": saved,
                "progress": 100,
            })
        
        return {
            "ok": True,
            "content": phase2_result['content'],
            "phase1": phase1_result,
            "phase2": phase2_result,
            "total_duration_ms": total_duration,
            "cost_usd": total_cost,
            "saved_usd": saved,
            "improvements": phase2_result.get('improvements', []),
        }
    
    async def _phase1_generate(
        self,
        prompt: str,
        task_type: str,
        stream_callback: Optional[Callable],
        session_id: str
    ) -> dict:
        """第一階段：低成本快速生成框架"""
        
        system_msg = self._get_phase1_system_prompt(task_type)
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ]
        
        # 優先嘗試 Ollama（本地免費）
        providers = ["ollama", "groq"]
        
        for provider in providers:
            try:
                if stream_callback:
                    await stream_callback({
                        "stage": "phase1_try",
                        "message": f"🔄 嘗試 {provider}...",
                        "provider": provider,
                    })
                
                t0 = time.time()
                service = AIServiceFactory.create(provider)
                content = await service.chat(messages)
                duration_ms = int((time.time() - t0) * 1000)
                
                # 估計 tokens
                tokens = len(prompt.split()) + len(content.split())
                
                return {
                    "provider": provider,
                    "content": content,
                    "duration_ms": duration_ms,
                    "tokens": tokens,
                    "success": True,
                }
            except Exception as e:
                if stream_callback:
                    await stream_callback({
                        "stage": "phase1_fail",
                        "message": f"⚠️ {provider} 失敗: {str(e)[:50]}",
                        "provider": provider,
                    })
                continue
        
        # 全部失敗，回退到 Gemini
        if stream_callback:
            await stream_callback({
                "stage": "phase1_fallback",
                "message": "🔄 Phase 1 回退到 Gemini...",
            })
        
        t0 = time.time()
        content = await gemini_ai.chat(messages)
        duration_ms = int((time.time() - t0) * 1000)
        tokens = len(prompt.split()) + len(content.split())
        
        return {
            "provider": "gemini_fallback",
            "content": content,
            "duration_ms": duration_ms,
            "tokens": tokens,
            "success": True,
        }
    
    async def _phase2_optimize(
        self,
        original_prompt: str,
        phase1_content: str,
        task_type: str,
        stream_callback: Optional[Callable],
        session_id: str
    ) -> dict:
        """第二階段：高品質精修優化"""
        
        optimize_prompt = f"""請精修並優化以下內容。

原始需求：
{original_prompt}

初稿（需要優化）：
{phase1_content}

請進行以下優化：
{self._get_phase2_instructions(task_type)}

請輸出優化後的完整內容，並在末尾簡要列出 3-5 個主要改進點。"""
        
        messages = [
            {"role": "system", "content": "你是專業的品質優化專家。請保持內容的完整性，同時顯著提升品質。"},
            {"role": "user", "content": optimize_prompt}
        ]
        
        # 嘗試 Gemini 然後 Claude
        providers = [("gemini", gemini_ai), ("claude", claude_ai)]
        
        for provider_name, service in providers:
            try:
                if stream_callback:
                    await stream_callback({
                        "stage": "phase2_try",
                        "message": f"🎯 使用 {provider_name} 精修...",
                        "provider": provider_name,
                    })
                
                t0 = time.time()
                content = await service.chat(messages)
                duration_ms = int((time.time() - t0) * 1000)
                
                # 提取改進點
                improvements = self._extract_improvements(content)
                content = self._remove_improvements_section(content)
                
                tokens = len(optimize_prompt.split()) + len(content.split())
                
                return {
                    "provider": provider_name,
                    "content": content,
                    "duration_ms": duration_ms,
                    "tokens": tokens,
                    "improvements": improvements,
                    "success": True,
                }
            except Exception as e:
                if stream_callback:
                    await stream_callback({
                        "stage": "phase2_fail",
                        "message": f"⚠️ {provider_name} 失敗: {str(e)[:50]}",
                    })
                continue
        
        # 全部失敗，返回 Phase 1 結果
        return {
            "provider": "phase1_fallback",
            "content": phase1_content,
            "duration_ms": 0,
            "tokens": 0,
            "improvements": [],
            "success": False,
        }
    
    async def code_generation(
        self,
        prompt: str,
        session_id: str,
        stream_callback: Optional[Callable] = None
    ) -> dict:
        """
        自然對話模式
        使用本地 qwen3:8b 模型進行自然對話，像 Cascade 一樣
        """
        start_time = time.time()
        
        if stream_callback:
            await stream_callback({
                "stage": "thinking",
                "message": "� 思考中...",
            })
        
        # 深度推理的系統提示詞（使用 deepseek-r1 的推理能力）
        system_prompt = """你是一個具有深度推理能力的 AI 程式設計助手。你的思考過程類似 Claude 和 o1，能夠進行多步驟推理和複雜問題解決。

核心能力：
1. **深度思考** - 遇到複雜問題時，先在 <think> 標籤中進行推理，再給出答案
2. **多步驟規劃** - 將複雜任務分解為可執行的步驟
3. **自我驗證** - 檢查自己的推理和程式碼是否正確
4. **持續學習** - 從對話歷史中學習用戶的需求和偏好

對話風格：
- 直接、專業，不過度客套
- 遇到複雜問題時，展示你的思考過程
- 提供完整、可執行的解決方案
- 用 Markdown 格式化，程式碼用 ```語言 包裹
- 主動提出改進建議和最佳實踐

程式碼標準：
- 生產級品質，完整可運行
- 完善的錯誤處理和邊界條件
- 清晰的註釋和文檔
- 遵循業界最佳實踐
- 考慮性能、安全性、可維護性

推理格式：
對於複雜問題，使用以下格式：
<think>
1. 問題分析：...
2. 解決方案設計：...
3. 潛在問題：...
4. 最佳實踐：...
</think>

然後提供清晰的答案和程式碼。"""

        # 獲取對話歷史（最近 10 輪）
        history = manager.sessions.get(session_id, {}).get("history", [])
        recent_history = history[-20:] if len(history) > 20 else history
        
        # 構建完整對話
        messages = [{"role": "system", "content": system_prompt}]
        
        # 加入歷史對話
        for msg in recent_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # 加入當前問題
        messages.append({"role": "user", "content": prompt})
        
        try:
            if stream_callback:
                await stream_callback({
                    "stage": "generating",
                    "message": "✍️ 正在回應...",
                })
            
            t0 = time.time()
            content = None
            used_provider = "unknown"
            groq_key = os.environ.get("GROQ_API_KEY", "")

            # 本地 Ollama 優先（local_only 模式）
            try:
                if stream_callback:
                    await stream_callback({"stage": "generating", "message": "🏠 本地模型回應中..."})
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"{OLLAMA_BASE_URL}/api/chat",
                        json={"model": OLLAMA_MODEL, "messages": messages, "stream": False,
                              "options": {"temperature": 0.7, "num_predict": 4096, "num_ctx": 4096}},
                    )
                    content = response.json()["message"]["content"]
                    used_provider = "ollama-local"
            except Exception as e:
                print(f"⚠️ Ollama failed: {e}")

            # Fallback: Groq（僅非 local_only 模式）
            if not content and groq_key and os.environ.get("AI_COST_MODE", "local_only") != "local_only":
                try:
                    if stream_callback:
                        await stream_callback({"stage": "generating", "message": "⚡ Groq 70B 備援中..."})
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                            json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 8192, "temperature": 0.7},
                        )
                        response.raise_for_status()
                        content = response.json()["choices"][0]["message"]["content"]
                        used_provider = "groq-70b"
                except Exception as e2:
                    raise RuntimeError(f"Ollama 和 Groq 都失敗: {e2}")

            duration_ms = int((time.time() - t0) * 1000)
            tokens = len(prompt.split()) + len(content.split())
            
            if stream_callback:
                await stream_callback({
                    "stage": "complete",
                    "message": f"✅ 完成（{used_provider} · {duration_ms}ms）",
                })
            
            # 更新統計
            self.cost_stats["total_requests"] += 1
            self.cost_stats["phase1_tokens"] += tokens
            
            return {
                "ok": True,
                "content": content,
                "provider": used_provider,
                "model": used_provider,
                "duration_ms": duration_ms,
                "tokens": tokens,
                "cost_usd": 0.0,
                "mode": "chat"
            }
            
        except Exception as e:
            error_msg = f"回應失敗: {str(e)}"
            
            if stream_callback:
                await stream_callback({
                    "stage": "error",
                    "message": f"❌ {error_msg}",
                })
            
            return {
                "ok": False,
                "error": error_msg,
                "content": f"抱歉，遇到問題了：{error_msg}",
                "provider": "fallback",
                "duration_ms": int((time.time() - start_time) * 1000),
            }
    
    def _get_phase1_system_prompt(self, task_type: str) -> str:
        """Phase 1 系統提示詞 - 快速生成框架"""
        prompts = {
            "code": "你是一個快速程式碼生成助手。請快速生成可運行的程式碼框架，注重結構完整性和基本功能。不需要過多註釋，保持簡潔實用。",
            "text": "你是一個快速寫作助手。請快速生成內容框架，包含主要觀點和基本結構。不需要過多潤飾，保持清晰表達。",
            "analysis": "你是一個快速分析助手。請快速分析問題並給出主要觀點和初步結論。不需要過多細節，保持邏輯清晰。",
            "learning": "你是一個學習內容生成助手。請快速生成學習材料的框架，包含核心概念和關鍵知識點。",
        }
        return prompts.get(task_type, prompts["text"])
    
    def _get_phase2_instructions(self, task_type: str) -> str:
        """Phase 2 優化指令"""
        instructions = {
            "code": """1. 程式碼品質：修正潛在錯誤、優化性能、提升可讀性
2. 最佳實踐：加入錯誤處理、邊界條件檢查
3. 命名規範：改進變數和函數命名
4. 結構優化：改進程式碼組織和模組化
5. 文件化：添加必要的註釋和文檔字符串""",
            "text": """1. 語言品質：修正語法錯誤、提升表達流暢度
2. 結構優化：改進段落組織和邏輯順序
3. 內容豐富：補充細節和例子
4. 風格統一：保持一致的語氣和風格
5. 專業用詞：使用更精確的詞彙""",
            "analysis": """1. 邏輯嚴謹：檢查論證過程的合理性
2. 觀點深化：補充深入的分析和見解
3. 數據支持：加入具體數據或案例
4. 結論清晰：明確總結主要發現
5. 建議可行：提供具體可行的建議""",
            "learning": """1. 概念準確：確保知識點的正確性
2. 結構清晰：改進知識的組織結構
3. 深入淺出：平衡專業性和易懂性
4. 實用導向：加入實際應用場景
5. 系統完整：補充遺漏的相關知識""",
        }
        return instructions.get(task_type, instructions["text"])
    
    def _extract_improvements(self, content: str) -> list[str]:
        """從內容中提取改進點列表"""
        improvements = []
        # 尋找常見的改進點標記
        lines = content.split('\n')
        in_improvement_section = False
        for line in lines:
            if any(kw in line.lower() for kw in ['改進', '優化', '提升', 'improvement', 'optimize', '主要改變']):
                in_improvement_section = True
            if in_improvement_section:
                if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '-', '*')):
                    improvements.append(line.strip())
                elif len(improvements) > 0 and not line.strip():
                    break
        return improvements[:5]
    
    def _remove_improvements_section(self, content: str) -> str:
        """移除改進點部分，返回純內容"""
        # 尋找常見的分隔標記
        separators = ['\n\n主要改進', '\n\n改進', '\n\n優化', '\n\nImprovements', '\n\n改變']
        for sep in separators:
            if sep in content:
                return content.split(sep)[0].strip()
        return content.strip()

# 初始化核心
bridge_core = SmartBridgeCore()

# ── API Endpoints ───────────────────────────────────────

@app.get("/health")
async def health():
    """健康檢查"""
    return {
        "status": "ok",
        "service": "smart-bridge",
        "version": "1.0.0",
        "sessions": len(manager.active_connections),
    }

@app.get("/api/cost-stats")
async def cost_stats():
    """取得成本統計"""
    return {
        "ok": True,
        **bridge_core.cost_stats,
        "efficiency": f"{bridge_core.cost_stats['saved_cost'] / max(bridge_core.cost_stats['estimated_cost'] + bridge_core.cost_stats['saved_cost'], 0.001) * 100:.1f}%",
    }

# ── 專案管理 API ────────────────────────────────────────
@app.get("/api/projects")
async def list_projects():
    """列出所有專案"""
    return {"ok": True, "projects": project_manager.list()}

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """取得專案詳情"""
    project = project_manager.get(project_id)
    if not project:
        raise HTTPException(404, "專案不存在")
    return {"ok": True, "project": project}

@app.post("/api/projects")
async def create_project(request: Request):
    """建立新專案"""
    data = await request.json()
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(400, "專案名稱不可為空")
    
    project = project_manager.create(
        name=name,
        description=data.get("description", ""),
        color=data.get("color", "purple"),
        icon=data.get("icon", "folder")
    )
    return {"ok": True, "project": project}

@app.put("/api/projects/{project_id}")
async def update_project(project_id: str, request: Request):
    """更新專案"""
    data = await request.json()
    project = project_manager.update(project_id, **data)
    if not project:
        raise HTTPException(404, "專案不存在")
    return {"ok": True, "project": project}

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """刪除專案"""
    if project_id == "default":
        raise HTTPException(400, "無法刪除預設專案")
    if not project_manager.delete(project_id):
        raise HTTPException(404, "專案不存在")
    return {"ok": True}

@app.delete("/api/projects/{project_id}/history")
async def clear_project_history(project_id: str):
    """清除專案對話歷史"""
    if not project_manager.clear_history(project_id):
        raise HTTPException(404, "專案不存在")
    return {"ok": True}

@app.post("/api/projects/sync")
async def sync_projects():
    """手動同步專案資料（重新載入磁碟資料並合併）"""
    result = project_manager.sync()
    return result

@app.get("/api/projects/{project_id}/export")
async def export_project(project_id: str):
    """匯出單個專案"""
    project = project_manager.export_project(project_id)
    if not project:
        raise HTTPException(404, "專案不存在")
    return JSONResponse(project, media_type="application/json")

@app.get("/api/projects/export/all")
async def export_all_projects():
    """匯出所有專案"""
    projects = project_manager.export_all()
    return JSONResponse(projects, media_type="application/json")

@app.post("/api/projects/import")
async def import_projects(request: Request):
    """
    匯入專案資料
    Body: {
        "data": {...},  # 專案資料（單個或多個）
        "mode": "skip" | "overwrite" | "merge"  # 衝突處理模式
    }
    """
    payload = await request.json()
    data = payload.get("data")
    mode = payload.get("mode", "skip")
    
    if not data:
        raise HTTPException(400, "缺少專案資料")
    
    if mode not in ["skip", "overwrite", "merge"]:
        raise HTTPException(400, "無效的匯入模式")
    
    result = project_manager.import_projects(data, mode)
    return result

@app.post("/api/generate")
async def api_generate(request: Request):
    """
    智慧型兩階段生成 API
    先用低成本模型生成80%，再用高品質模型精修
    """
    payload = await request.json()
    prompt = str((payload or {}).get("prompt", "")).strip()
    task_type = str((payload or {}).get("task_type", "code")).strip()
    
    if not prompt:
        raise HTTPException(400, "prompt is required")
    
    # 非同步生成（無 streaming）
    result = await bridge_core.two_phase_generate(prompt, "api", task_type)
    return result

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 對話端點
    即時顯示 AI 運作過程
    """
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    await manager.connect(websocket, session_id)
    
    try:
        # 發送歡迎訊息
        await manager.send_to_session(session_id, {
            "type": "connected",
            "session_id": session_id,
            "message": "🌉 Smart Bridge 已連接！",
            "features": [
                "兩階段智慧生成（低成本80% + 高品質精修）",
                "即時視覺化運作過程",
                "本地 Ollama 模型學習控制",
            ],
        })
        
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            
            msg_type = request.get("type", "chat")
            
            if msg_type == "chat":
                user_input = request.get("text", "")
                task_type = request.get("task_type", "text")
                mode = request.get("mode", "two_phase")  # 新增：模式選擇
                
                # 記錄用戶訊息
                manager.sessions[session_id]["history"].append({
                    "role": "user",
                    "content": user_input,
                    "timestamp": datetime.now().isoformat(),
                })
                
                # Stream callback
                async def stream_callback(operation: dict):
                    await manager.broadcast_operation(session_id, operation)
                
                # 根據模式選擇生成方式
                if mode == "code_gen":
                    # 程式碼生成模式（使用本地 qwen3:8b）
                    result = await bridge_core.code_generation(
                        user_input, session_id, stream_callback
                    )
                else:
                    # 兩階段生成模式
                    result = await bridge_core.two_phase_generate(
                        user_input, session_id, task_type, stream_callback
                    )
                
                # 記錄 AI 回應（根據模式調整）
                if mode == "code_gen":
                    manager.sessions[session_id]["history"].append({
                        "role": "assistant",
                        "content": result["content"],
                        "timestamp": datetime.now().isoformat(),
                        "meta": {
                            "provider": result.get("provider", "qwen3"),
                            "model": result.get("model", "qwen3:32b"),
                            "mode": "code_generation",
                            "cost": 0.0,
                        },
                    })
                    
                    # 發送程式碼生成結果
                    await manager.send_to_session(session_id, {
                        "type": "response",
                        "content": result["content"],
                        "mode": "code_generation",
                        "meta": {
                            "provider": result.get("provider", "qwen3"),
                            "model": result.get("model", "qwen3:32b"),
                            "duration_ms": result.get("duration_ms", 0),
                            "cost_usd": 0.0,
                            "tokens": result.get("tokens", 0),
                        },
                    })
                else:
                    manager.sessions[session_id]["history"].append({
                        "role": "assistant",
                        "content": result["content"],
                        "timestamp": datetime.now().isoformat(),
                        "meta": {
                            "phase1_provider": result["phase1"]["provider"],
                            "phase2_provider": result["phase2"]["provider"],
                            "cost": result["cost_usd"],
                            "saved": result["saved_usd"],
                        },
                    })
                    
                    # 發送兩階段生成結果
                    await manager.send_to_session(session_id, {
                        "type": "response",
                        "content": result["content"],
                        "mode": "two_phase",
                        "meta": {
                            "phase1_provider": result["phase1"]["provider"],
                            "phase2_provider": result["phase2"]["provider"],
                            "total_duration_ms": result["total_duration_ms"],
                            "cost_usd": result["cost_usd"],
                            "saved_usd": result["saved_usd"],
                            "improvements": result["improvements"],
                        },
                    })
                
            elif msg_type == "learn":
                # 本地模型學習指令
                await handle_learn_command(request, session_id)
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        await manager.send_to_session(session_id, {
            "type": "error",
            "message": f"系統錯誤: {str(e)}",
        })
        manager.disconnect(session_id)

async def handle_learn_command(request: dict, session_id: str):
    """處理學習相關指令 - 使用 OllamaLearningController"""
    action = request.get("action", "status")
    
    if not LEARNING_AVAILABLE:
        await manager.send_to_session(session_id, {
            "type": "error",
            "message": "Ollama 學習控制器未載入",
        })
        return
    
    # 建立學習控制器，帶入 stream callback
    async def stream_callback(data: dict):
        await manager.broadcast_operation(session_id, data)
    
    controller = OllamaLearningController(stream_callback)
    
    if action == "status":
        # 檢查 Ollama 狀態
        status = await controller.check_status()
        await manager.send_to_session(session_id, {
            "type": "learn_status",
            **status,
        })
    
    elif action == "learn_topic":
        # 學習新主題
        topic = request.get("topic", "")
        depth = request.get("depth", "standard")
        
        if topic:
            # 非同步執行學習
            asyncio.create_task(
                controller.learn_topic(topic, session_id, depth)
            )
        else:
            await manager.send_to_session(session_id, {
                "type": "error",
                "message": "請提供學習主題",
            })

# ── Static Files ───────────────────────────────────────
STATIC_DIR = BRIDGE_WORKSPACE / "static"
STATIC_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    """返回前端界面"""
    html_path = STATIC_DIR / "bridge.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse(get_default_html())

def get_default_html() -> str:
    """預設前端界面（如果靜態檔案不存在）"""
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Smart Bridge - 築未科技</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen">
    <div class="max-w-6xl mx-auto p-4">
        <header class="mb-6">
            <h1 class="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent">
                🌉 Smart Bridge
            </h1>
            <p class="text-slate-400">智慧型對話橋接服務 - 兩階段生成 (80%低成本 + 20%高品質)</p>
        </header>
        
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- 對話區 -->
            <div class="bg-slate-800 rounded-lg p-4">
                <h2 class="text-lg font-semibold mb-3">💬 對話</h2>
                <div id="chat" class="h-96 overflow-y-auto bg-slate-950 rounded p-3 mb-3 text-sm"></div>
                <div class="flex gap-2">
                    <input id="input" type="text" placeholder="輸入訊息..." 
                           class="flex-1 bg-slate-700 rounded px-3 py-2 text-sm">
                    <button onclick="send()" class="bg-cyan-600 hover:bg-cyan-500 px-4 py-2 rounded text-sm">
                        發送
                    </button>
                </div>
            </div>
            
            <!-- 運作過程 -->
            <div class="bg-slate-800 rounded-lg p-4">
                <h2 class="text-lg font-semibold mb-3">⚙️ AI 運作過程</h2>
                <div id="operations" class="h-96 overflow-y-auto bg-slate-950 rounded p-3 text-xs font-mono">
                    <div class="text-slate-500">等待連接...</div>
                </div>
            </div>
        </div>
        
        <!-- 進度條 -->
        <div class="mt-4 bg-slate-800 rounded-lg p-4">
            <div class="flex justify-between text-sm mb-2">
                <span id="stage-label">就緒</span>
                <span id="progress-text">0%</span>
            </div>
            <div class="h-2 bg-slate-700 rounded-full overflow-hidden">
                <div id="progress-bar" class="h-full bg-gradient-to-r from-cyan-500 to-purple-500 w-0 transition-all duration-300"></div>
            </div>
        </div>
    </div>
    
    <script>
        const ws = new WebSocket(`wss://${location.host}/ws`);
        const chat = document.getElementById('chat');
        const operations = document.getElementById('operations');
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');
        const stageLabel = document.getElementById('stage-label');
        
        ws.onopen = () => addOp('🟢 WebSocket 已連接', 'text-green-400');
        ws.onclose = () => addOp('🔴 WebSocket 已斷開', 'text-red-400');
        
        ws.onmessage = (e) => {
            const msg = JSON.parse(e.data);
            
            if (msg.type === 'connected') {
                addOp(`✅ ${msg.message}`, 'text-cyan-400');
            }
            else if (msg.type === 'operation') {
                const color = msg.stage?.includes('fail') ? 'text-red-400' :
                             msg.stage?.includes('complete') ? 'text-green-400' :
                             'text-yellow-400';
                addOp(`[${msg.stage}] ${msg.message}`, color);
                
                if (msg.progress !== undefined) {
                    progressBar.style.width = msg.progress + '%';
                    progressText.textContent = msg.progress + '%';
                }
                stageLabel.textContent = msg.stage || '處理中';
            }
            else if (msg.type === 'response') {
                addChat('AI', msg.content, 'text-purple-400');
                addOp(`💰 成本: $${msg.meta.cost_usd.toFixed(4)}, 節省: $${msg.meta.saved_usd.toFixed(4)}`, 'text-green-400');
            }
        };
        
        function addChat(who, text, color) {
            chat.innerHTML += `<div class="${color} mb-2"><b>${who}:</b> ${text}</div>`;
            chat.scrollTop = chat.scrollHeight;
        }
        
        function addOp(text, color = 'text-slate-400') {
            const time = new Date().toLocaleTimeString();
            operations.innerHTML += `<div class="${color}">[${time}] ${text}</div>`;
            operations.scrollTop = operations.scrollHeight;
        }
        
        function send() {
            const input = document.getElementById('input');
            const text = input.value.trim();
            if (!text) return;
            
            addChat('You', text, 'text-cyan-400');
            ws.send(JSON.stringify({type: 'chat', text, task_type: 'code'}));
            input.value = '';
        }
        
        document.getElementById('input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') send();
        });
    </script>
</body>
</html>"""

# ── 掛載 App Builder 模組（構想即系統）──
try:
    from bridge_app_builder import mount_app_builder
    mount_app_builder(app)
except Exception as e:
    print(f"⚠️ App Builder 模組載入失敗: {e}")

# ── AI 創作工作室（無限生圖 · 生影片）──
@app.get("/ai-studio")
async def ai_studio_page():
    html_path = BRIDGE_WORKSPACE / "static" / "ai-studio.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>ai-studio.html not found</h1>", status_code=404)
print("✅ AI 創作工作室已掛載 → /ai-studio")

# ── ComfyUI 本地生圖代理 API ──
import httpx
_COMFYUI_DEFAULT = "http://host.docker.internal:8188"
# 自動偵測：非 Docker 環境用 localhost
try:
    import socket
    socket.getaddrinfo("host.docker.internal", 8188, socket.AF_INET, socket.SOCK_STREAM)
except socket.gaierror:
    _COMFYUI_DEFAULT = "http://localhost:8188"
COMFYUI_BASE = os.environ.get("COMFYUI_URL", _COMFYUI_DEFAULT)

@app.post("/api/comfyui/generate")
async def comfyui_generate(request: Request):
    """本地 ComfyUI 生圖代理：接收 prompt，提交 workflow，輪詢結果，回傳圖片 base64"""
    import base64 as _b64
    body = await request.json()
    prompt_text = body.get("prompt", "")
    ckpt = body.get("checkpoint", "v1-5-pruned-emaonly.safetensors")
    width = body.get("width", 512)
    height = body.get("height", 512)
    steps = body.get("steps", 20)
    cfg = body.get("cfg", 7.0)
    sampler = body.get("sampler", "euler_ancestral")
    seed = body.get("seed", int(time.time()) % (2**32))
    neg = body.get("negative_prompt", "blurry, low quality, distorted, watermark, text, ugly, deformed")

    # Flux Schnell 專用設定
    is_flux = "flux" in ckpt.lower()
    if is_flux:
        steps = body.get("steps", 4)
        cfg = body.get("cfg", 1.0)
        sampler = body.get("sampler", "euler")
        width = body.get("width", 1024)
        height = body.get("height", 1024)

    client_id = str(uuid.uuid4())
    workflow = {
        "3": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": steps, "cfg": cfg,
            "sampler_name": sampler, "scheduler": "normal",
            "denoise": 1.0, "model": ["4", 0], "positive": ["6", 0],
            "negative": ["7", 0], "latent_image": ["5", 0],
        }},
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_text[:500], "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "ai_studio", "images": ["8", 0]}},
    }

    try:
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(f"{COMFYUI_BASE}/prompt", json={"prompt": workflow, "client_id": client_id})
            if r.status_code not in (200, 201):
                return JSONResponse({"error": f"ComfyUI prompt 提交失敗: {r.status_code}"}, status_code=502)
            prompt_id = r.json().get("prompt_id")
            if not prompt_id:
                return JSONResponse({"error": "無 prompt_id"}, status_code=502)

            # 輪詢結果
            for _ in range(180):
                await asyncio.sleep(1)
                hr = await client.get(f"{COMFYUI_BASE}/history/{prompt_id}")
                if hr.status_code != 200:
                    continue
                hist = hr.json()
                if prompt_id not in hist:
                    continue
                outputs = hist[prompt_id].get("outputs", {})
                for node_id, out in outputs.items():
                    images = out.get("images", [])
                    if images:
                        img_info = images[0]
                        img_url = f"{COMFYUI_BASE}/view?filename={img_info['filename']}&subfolder={img_info.get('subfolder','')}&type=output"
                        img_r = await client.get(img_url)
                        if img_r.status_code == 200:
                            b64 = _b64.b64encode(img_r.content).decode()
                            return JSONResponse({"image": f"data:image/png;base64,{b64}", "prompt_id": prompt_id})
                return JSONResponse({"error": "生成完成但無圖片輸出"}, status_code=500)
            return JSONResponse({"error": "生成超時（3分鐘）"}, status_code=504)
    except httpx.ConnectError:
        return JSONResponse({"error": "ComfyUI 未啟動（無法連線 localhost:8188）"}, status_code=503)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/comfyui/status")
async def comfyui_status():
    """檢查 ComfyUI 是否在線 + 列出可用模型"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{COMFYUI_BASE}/system_stats")
            obj_r = await client.get(f"{COMFYUI_BASE}/object_info/CheckpointLoaderSimple")
            models = []
            if obj_r.status_code == 200:
                info = obj_r.json()
                models = info.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
            return JSONResponse({"online": True, "models": models})
    except Exception:
        return JSONResponse({"online": False, "models": []})

print(f"✅ ComfyUI 代理 API 已掛載 → /api/comfyui/* (連線: {COMFYUI_BASE})")

# ── Forge Chroma (SD WebUI) 本地生圖代理 API ──
_FORGE_DEFAULT = "http://host.docker.internal:7860"
try:
    socket.getaddrinfo("host.docker.internal", 7860, socket.AF_INET, socket.SOCK_STREAM)
except socket.gaierror:
    _FORGE_DEFAULT = "http://localhost:7860"
FORGE_BASE = os.environ.get("FORGE_URL", _FORGE_DEFAULT)

@app.post("/api/forge/generate")
async def forge_generate(request: Request):
    """Forge Chroma txt2img 代理：接收 prompt，呼叫 SD WebUI API，回傳圖片 base64"""
    body = await request.json()
    prompt_text = body.get("prompt", "")
    negative = body.get("negative_prompt", "blurry, low quality, distorted, watermark, text, ugly, deformed")
    width = body.get("width", 1024)
    height = body.get("height", 1024)
    steps = body.get("steps", 25)
    cfg_scale = body.get("cfg_scale", 7.0)
    sampler = body.get("sampler_name", "Euler a")
    seed = body.get("seed", -1)
    model = body.get("model", None)

    payload = {
        "prompt": prompt_text,
        "negative_prompt": negative,
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "sampler_name": sampler,
        "seed": seed,
        "batch_size": 1,
        "n_iter": 1,
    }

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            # 切換模型（如果指定）
            if model:
                await client.post(f"{FORGE_BASE}/sdapi/v1/options", json={"sd_model_checkpoint": model}, timeout=120)

            r = await client.post(f"{FORGE_BASE}/sdapi/v1/txt2img", json=payload)
            if r.status_code != 200:
                return JSONResponse({"error": f"Forge API 錯誤: {r.status_code}"}, status_code=502)
            data = r.json()
            images = data.get("images", [])
            if not images:
                return JSONResponse({"error": "Forge 無圖片輸出"}, status_code=500)
            return JSONResponse({"image": f"data:image/png;base64,{images[0]}", "info": data.get("info", "")})
    except httpx.ConnectError:
        return JSONResponse({"error": "Forge Chroma 未啟動（無法連線 localhost:7860）"}, status_code=503)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/forge/status")
async def forge_status():
    """檢查 Forge Chroma 是否在線 + 列出可用模型"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{FORGE_BASE}/sdapi/v1/sd-models")
            if r.status_code == 200:
                models = [m.get("model_name", m.get("title", "")) for m in r.json()]
                opt_r = await client.get(f"{FORGE_BASE}/sdapi/v1/options")
                current = ""
                if opt_r.status_code == 200:
                    current = opt_r.json().get("sd_model_checkpoint", "")
                return JSONResponse({"online": True, "models": models, "current_model": current})
        return JSONResponse({"online": False, "models": []})
    except Exception:
        return JSONResponse({"online": False, "models": []})

@app.get("/api/forge/samplers")
async def forge_samplers():
    """列出 Forge 可用的 sampler"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{FORGE_BASE}/sdapi/v1/samplers")
            if r.status_code == 200:
                return JSONResponse([s.get("name") for s in r.json()])
    except Exception:
        pass
    return JSONResponse(["Euler a", "Euler", "DPM++ 2M", "DPM++ 2M Karras", "DPM++ SDE Karras"])

@app.post("/api/forge/img2img")
async def forge_img2img(request: Request):
    """Forge img2img 代理：參考圖 + prompt → 修改圖片"""
    import base64 as _b64
    body = await request.json()
    prompt_text = body.get("prompt", "")
    negative = body.get("negative_prompt", "blurry, low quality, distorted, watermark, text, ugly, deformed")
    init_image = body.get("init_image", "")  # base64 (不含 data:... 前綴)
    denoising_strength = body.get("denoising_strength", 0.7)
    width = body.get("width", 1024)
    height = body.get("height", 1024)
    steps = body.get("steps", 25)
    cfg_scale = body.get("cfg_scale", 7.0)
    sampler = body.get("sampler_name", "Euler a")
    seed = body.get("seed", -1)
    model = body.get("model", None)

    if not init_image:
        return JSONResponse({"error": "缺少 init_image（base64）"}, status_code=400)

    # 移除 data:image/...;base64, 前綴
    if "base64," in init_image:
        init_image = init_image.split("base64,")[1]

    payload = {
        "prompt": prompt_text,
        "negative_prompt": negative,
        "init_images": [init_image],
        "denoising_strength": denoising_strength,
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "sampler_name": sampler,
        "seed": seed,
        "batch_size": 1,
        "n_iter": 1,
    }

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            if model:
                await client.post(f"{FORGE_BASE}/sdapi/v1/options", json={"sd_model_checkpoint": model}, timeout=120)
            r = await client.post(f"{FORGE_BASE}/sdapi/v1/img2img", json=payload)
            if r.status_code != 200:
                return JSONResponse({"error": f"Forge img2img 錯誤: {r.status_code}"}, status_code=502)
            data = r.json()
            images = data.get("images", [])
            if not images:
                return JSONResponse({"error": "Forge img2img 無圖片輸出"}, status_code=500)
            return JSONResponse({"image": f"data:image/png;base64,{images[0]}", "info": data.get("info", "")})
    except httpx.ConnectError:
        return JSONResponse({"error": "Forge 未啟動"}, status_code=503)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/forge/upscale")
async def forge_upscale(request: Request):
    """Forge 圖片放大（Real-ESRGAN / SwinIR）"""
    import base64 as _b64
    body = await request.json()
    init_image = body.get("image", "")
    upscaler = body.get("upscaler", "R-ESRGAN 4x+")
    scale = body.get("scale", 2)

    if not init_image:
        return JSONResponse({"error": "缺少 image（base64）"}, status_code=400)
    if "base64," in init_image:
        init_image = init_image.split("base64,")[1]

    payload = {
        "resize_mode": 0,
        "upscaling_resize": scale,
        "upscaler_1": upscaler,
        "image": init_image,
    }

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(f"{FORGE_BASE}/sdapi/v1/extra-single-image", json=payload)
            if r.status_code != 200:
                return JSONResponse({"error": f"Forge upscale 錯誤: {r.status_code}"}, status_code=502)
            data = r.json()
            result_img = data.get("image", "")
            if not result_img:
                return JSONResponse({"error": "Forge upscale 無輸出"}, status_code=500)
            return JSONResponse({"image": f"data:image/png;base64,{result_img}"})
    except httpx.ConnectError:
        return JSONResponse({"error": "Forge 未啟動"}, status_code=503)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/forge/batch")
async def forge_batch(request: Request):
    """Forge 批次生圖：一次生成多張"""
    body = await request.json()
    prompt_text = body.get("prompt", "")
    negative = body.get("negative_prompt", "blurry, low quality, distorted, watermark, text, ugly, deformed")
    width = body.get("width", 1024)
    height = body.get("height", 1024)
    steps = body.get("steps", 25)
    cfg_scale = body.get("cfg_scale", 7.0)
    sampler = body.get("sampler_name", "Euler a")
    batch_size = min(body.get("batch_size", 2), 4)
    model = body.get("model", None)

    payload = {
        "prompt": prompt_text,
        "negative_prompt": negative,
        "width": width, "height": height,
        "steps": steps, "cfg_scale": cfg_scale,
        "sampler_name": sampler, "seed": -1,
        "batch_size": batch_size, "n_iter": 1,
    }

    try:
        async with httpx.AsyncClient(timeout=600) as client:
            if model:
                await client.post(f"{FORGE_BASE}/sdapi/v1/options", json={"sd_model_checkpoint": model}, timeout=120)
            r = await client.post(f"{FORGE_BASE}/sdapi/v1/txt2img", json=payload)
            if r.status_code != 200:
                return JSONResponse({"error": f"Forge batch 錯誤: {r.status_code}"}, status_code=502)
            data = r.json()
            images = data.get("images", [])
            return JSONResponse({"images": [f"data:image/png;base64,{img}" for img in images], "count": len(images)})
    except httpx.ConnectError:
        return JSONResponse({"error": "Forge 未啟動"}, status_code=503)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/forge/upscalers")
async def forge_upscalers():
    """列出 Forge 可用的 upscaler"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{FORGE_BASE}/sdapi/v1/upscalers")
            if r.status_code == 200:
                return JSONResponse([u.get("name") for u in r.json()])
    except Exception:
        pass
    return JSONResponse(["R-ESRGAN 4x+", "R-ESRGAN 4x+ Anime6B", "SwinIR_4x", "Lanczos", "Nearest"])

@app.post("/api/ai/enhance-prompt")
async def enhance_prompt(request: Request):
    """用智慧路由增強 prompt — Groq 70B → Gemini → Grok → DeepSeek → Ollama fallback"""
    body = await request.json()
    user_prompt = body.get("prompt", "").strip()
    style = body.get("style", "photorealistic")
    force_local = body.get("local_only", False)
    if not user_prompt:
        return JSONResponse({"error": "缺少 prompt"}, status_code=400)

    system_msg = f"""You are an expert AI image prompt engineer. Enhance the user's image description into a detailed, high-quality prompt for Stable Diffusion / DALL-E.
Rules:
- Output ONLY the enhanced prompt, nothing else
- Add specific details: lighting, camera angle, atmosphere, texture, color palette
- Style target: {style}
- Keep it under 200 words
- If the input is in Chinese, output the enhanced prompt in English (better for AI image models)
- Add quality boosters: masterpiece, best quality, highly detailed, 8K, professional"""

    import re

    # 策略：先嘗試強力雲端模型（免費），失敗才 fallback 到本地 Ollama
    if not force_local:
        try:
            from ai_modules.ai_providers import ask
            result, provider = await asyncio.to_thread(ask, user_prompt, False, system_msg)
            if result and "連線失敗" not in result and "預算已達上限" not in result:
                enhanced = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL).strip()
                if enhanced:
                    return JSONResponse({"ok": True, "original": user_prompt, "enhanced": enhanced, "provider": provider})
        except Exception:
            pass

    # Fallback: 本地 Ollama（零 token）
    try:
        import aiohttp
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{ollama_url}/api/chat", json={
                "model": "qwen3:4b",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {"temperature": 0.8, "num_predict": 300}
            }, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    enhanced = data.get("message", {}).get("content", "").strip()
                    enhanced = re.sub(r'<think>.*?</think>', '', enhanced, flags=re.DOTALL).strip()
                    if enhanced:
                        return JSONResponse({"ok": True, "original": user_prompt, "enhanced": enhanced, "provider": "Ollama (本地)"})
        return JSONResponse({"ok": False, "error": "所有 AI 提供者均無回應"}, status_code=502)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

print(f"✅ Forge Chroma 代理 API 已掛載 → /api/forge/* (連線: {FORGE_BASE})")
print("✅ AI Prompt 增強 API 已掛載 → /api/ai/enhance-prompt (智慧路由: Groq→Gemini→Grok→Ollama)")

# ── 本地運算輔助 API ──

@app.post("/api/ai/translate-prompt")
async def translate_prompt(request: Request):
    """智慧路由翻譯 — Groq 70B → Gemini → Grok → Ollama fallback"""
    body = await request.json()
    user_prompt = body.get("prompt", "").strip()
    force_local = body.get("local_only", False)
    if not user_prompt:
        return JSONResponse({"error": "缺少 prompt"}, status_code=400)

    import re as _re
    has_chinese = bool(_re.search(r'[\u4e00-\u9fff]', user_prompt))
    if not has_chinese:
        return JSONResponse({"ok": True, "translated": user_prompt, "was_chinese": False, "provider": "none"})

    system_msg = """You are a translator. Translate the user's Chinese image description into English for Stable Diffusion.
Rules:
- Output ONLY the English translation, nothing else
- Keep artistic/style terms accurate
- Do NOT add extra details or quality boosters
- Be concise and faithful to the original meaning
- No explanations, no markdown, just the translated prompt"""

    # 策略：先嘗試強力雲端模型（免費），失敗才 fallback 到本地 Ollama
    if not force_local:
        try:
            from ai_modules.ai_providers import ask
            result, provider = await asyncio.to_thread(ask, user_prompt, False, system_msg)
            if result and "連線失敗" not in result and "預算已達上限" not in result:
                translated = _re.sub(r'<think>.*?</think>', '', result, flags=_re.DOTALL).strip()
                if translated:
                    return JSONResponse({"ok": True, "translated": translated, "was_chinese": True, "original": user_prompt, "provider": provider})
        except Exception:
            pass

    # Fallback: 本地 Ollama（零 token）
    try:
        import aiohttp
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{ollama_url}/api/chat", json={
                "model": "qwen3:4b",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 200}
            }, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    translated = data.get("message", {}).get("content", "").strip()
                    translated = _re.sub(r'<think>.*?</think>', '', translated, flags=_re.DOTALL).strip()
                    if translated:
                        return JSONResponse({"ok": True, "translated": translated, "was_chinese": True, "original": user_prompt, "provider": "Ollama (本地)"})
        return JSONResponse({"ok": False, "error": "所有 AI 提供者均無回應"}, status_code=502)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/api/comfyui/generate-video")
async def comfyui_generate_video(request: Request):
    """本地 ComfyUI 影片生成代理（AnimateDiff / SVD workflow）— 零 token 消耗"""
    import base64 as _b64
    body = await request.json()
    prompt_text = body.get("prompt", "")
    width = body.get("width", 512)
    height = body.get("height", 512)
    frames = min(body.get("frames", 16), 32)
    fps = body.get("fps", 8)
    steps = body.get("steps", 20)
    cfg = body.get("cfg", 7.0)
    init_image = body.get("init_image", None)  # base64 data URL for img2vid

    # 解析 ComfyUI 連線位址（優先 localhost，Docker 環境才用 host.docker.internal）
    comfyui_url = COMFYUI_BASE

    # 先檢查 ComfyUI 可用的自訂節點
    available_nodes = set()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            obj_r = await client.get(f"{comfyui_url}/object_info")
            if obj_r.status_code != 200:
                return JSONResponse({"error": "ComfyUI 未啟動（回應異常）", "url": comfyui_url}, status_code=503)
            available_nodes = set(obj_r.json().keys())
    except httpx.ConnectError:
        return JSONResponse({"error": f"ComfyUI 未啟動（無法連線 {comfyui_url}）。請確認 ComfyUI 正在運行。", "url": comfyui_url}, status_code=503)
    except Exception as e:
        return JSONResponse({"error": f"ComfyUI 連線錯誤: {str(e)}", "url": comfyui_url}, status_code=500)

    # 檢查影片生成節點
    has_animatediff = "ADE_AnimateDiffLoaderWithContext" in available_nodes or "AnimateDiffLoaderV1" in available_nodes
    has_svd = "SVD_img2vid_Conditioning" in available_nodes
    has_wan = "WanVideoTextEncode" in available_nodes or "Wan2_1" in available_nodes

    if not has_animatediff and not has_svd and not has_wan:
        return JSONResponse({
            "error": "ComfyUI 缺少影片生成節點。請安裝 AnimateDiff Evolved 自訂節點。",
            "install_guide": "方法：ComfyUI Manager → Install Custom Nodes → 搜尋 'AnimateDiff Evolved' → 安裝 → 重啟 ComfyUI。另外需下載 motion module: mm_sd_v15_v2.ckpt 放到 ComfyUI/custom_nodes/ComfyUI-AnimateDiff-Evolved/models/",
            "available_nodes_count": len(available_nodes)
        }, status_code=501)

    # 取得可用的 checkpoint 模型
    client_id = str(uuid.uuid4())
    ckpt_models = []
    motion_models = []
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            ckpt_r = await client.get(f"{comfyui_url}/object_info/CheckpointLoaderSimple")
            if ckpt_r.status_code == 200:
                ckpt_models = ckpt_r.json().get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
            # 取得 AnimateDiff motion module 列表
            if has_animatediff:
                loader_node = "ADE_AnimateDiffLoaderWithContext" if "ADE_AnimateDiffLoaderWithContext" in available_nodes else "AnimateDiffLoaderV1"
                mm_r = await client.get(f"{comfyui_url}/object_info/{loader_node}")
                if mm_r.status_code == 200:
                    node_info = mm_r.json().get(loader_node, {})
                    inputs = node_info.get("input", {}).get("required", {})
                    model_name_opts = inputs.get("model_name", [[]])
                    if isinstance(model_name_opts, list) and model_name_opts:
                        motion_models = model_name_opts[0] if isinstance(model_name_opts[0], list) else model_name_opts
    except Exception:
        pass

    ckpt = ckpt_models[0] if ckpt_models else "v1-5-pruned-emaonly.safetensors"

    # 建構 AnimateDiff workflow
    if has_animatediff:
        loader_node = "ADE_AnimateDiffLoaderWithContext" if "ADE_AnimateDiffLoaderWithContext" in available_nodes else "AnimateDiffLoaderV1"

        # motion module 必須存在
        if not motion_models:
            return JSONResponse({
                "error": "AnimateDiff 缺少 motion module 模型。",
                "install_guide": "請下載 motion module（如 mm_sd_v15_v2.ckpt）放到 ComfyUI/custom_nodes/ComfyUI-AnimateDiff-Evolved/models/ 目錄，然後重啟 ComfyUI。",
                "download_url": "https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt"
            }, status_code=501)

        motion_model = motion_models[0]

        # AnimateDiff loader 的 inputs
        ad_loader_inputs = {"model": ["3", 0], "model_name": motion_model}
        # 某些版本需要額外參數
        if loader_node == "ADE_AnimateDiffLoaderWithContext":
            ad_loader_inputs["beta_schedule"] = "sqrt_linear (AnimateDiff)"

        workflow = {
            "3": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_text, "clip": ["3", 1]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, low quality, distorted, watermark, text, worst quality", "clip": ["3", 1]}},
            "10": {"class_type": loader_node, "inputs": ad_loader_inputs},
            "11": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": frames}},
            "12": {"class_type": "KSampler", "inputs": {
                "model": ["10", 0], "seed": -1, "steps": steps, "cfg": cfg,
                "sampler_name": "euler_ancestral", "scheduler": "normal",
                "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["11", 0],
                "denoise": 1.0
            }},
            "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["3", 2]}},
        }

        # init_image 支援（img2vid）：用 VAEEncode 取代 EmptyLatentImage
        if init_image:
            try:
                # 去掉 data:image/...;base64, 前綴
                if "," in init_image:
                    init_image = init_image.split(",", 1)[1]
                img_bytes = _b64.b64decode(init_image)
                # 上傳圖片到 ComfyUI
                import io
                async with httpx.AsyncClient(timeout=30) as client:
                    files = {"image": ("init_image.png", io.BytesIO(img_bytes), "image/png")}
                    up_r = await client.post(f"{comfyui_url}/upload/image", files=files, data={"overwrite": "true"})
                    if up_r.status_code == 200:
                        uploaded_name = up_r.json().get("name", "init_image.png")
                        # 用 LoadImage + VAEEncode 取代 EmptyLatentImage
                        workflow["20"] = {"class_type": "LoadImage", "inputs": {"image": uploaded_name}}
                        workflow["21"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["20", 0], "vae": ["3", 2]}}
                        workflow["12"]["inputs"]["latent_image"] = ["21", 0]
                        workflow["12"]["inputs"]["denoise"] = 0.75  # img2vid 保留部分原圖
                        del workflow["11"]  # 移除 EmptyLatentImage
            except Exception as e:
                print(f"⚠️ init_image 處理失敗，改用 txt2vid: {e}")

        # 輸出節點：優先 VHS_VideoCombine（mp4），否則 SaveImage（圖片序列）
        if "VHS_VideoCombine" in available_nodes:
            workflow["14"] = {"class_type": "VHS_VideoCombine", "inputs": {
                "images": ["13", 0], "frame_rate": fps, "filename_prefix": "animatediff",
                "loop_count": 0, "format": "video/h264-mp4",
                "pingpong": False, "save_output": True
            }}
        else:
            workflow["14"] = {"class_type": "SaveImage", "inputs": {
                "images": ["13", 0], "filename_prefix": "animatediff"
            }}
    else:
        return JSONResponse({"error": "僅支援 AnimateDiff workflow，請安裝 AnimateDiff Evolved"}, status_code=501)

    try:
        async with httpx.AsyncClient(timeout=600) as client:
            r = await client.post(f"{comfyui_url}/prompt", json={"prompt": workflow, "client_id": client_id})
            if r.status_code not in (200, 201):
                err_text = r.text[:300] if hasattr(r, 'text') else str(r.status_code)
                return JSONResponse({"error": f"ComfyUI workflow 提交失敗: {err_text}"}, status_code=502)
            prompt_id = r.json().get("prompt_id")
            if not prompt_id:
                return JSONResponse({"error": "ComfyUI 未回傳 prompt_id"}, status_code=502)

            # 輪詢結果（影片生成較慢，最多等 10 分鐘）
            for tick in range(600):
                await asyncio.sleep(1)
                hr = await client.get(f"{comfyui_url}/history/{prompt_id}")
                if hr.status_code != 200:
                    continue
                hist = hr.json()
                if prompt_id in hist:
                    # 檢查是否有錯誤
                    status_info = hist[prompt_id].get("status", {})
                    if status_info.get("status_str") == "error":
                        msgs = status_info.get("messages", [])
                        err_msg = str(msgs)[:300] if msgs else "workflow 執行錯誤"
                        return JSONResponse({"error": f"ComfyUI 執行錯誤: {err_msg}"}, status_code=500)

                    outputs = hist[prompt_id].get("outputs", {})
                    for node_id, out in outputs.items():
                        # 影片輸出（VHS_VideoCombine）
                        gifs = out.get("gifs", [])
                        if gifs:
                            vid_info = gifs[0]
                            vid_url = f"{comfyui_url}/view?filename={vid_info['filename']}&subfolder={vid_info.get('subfolder','')}&type=output"
                            vid_r = await client.get(vid_url)
                            if vid_r.status_code == 200:
                                b64 = _b64.b64encode(vid_r.content).decode()
                                fmt = vid_info.get("format", "video/mp4")
                                return JSONResponse({"video": f"data:{fmt};base64,{b64}", "frames": frames, "fps": fps, "provider": "ComfyUI AnimateDiff"})
                        # 圖片序列輸出（fallback — 組合成 GIF）
                        images = out.get("images", [])
                        if images and len(images) > 1:
                            img_frames = []
                            for img_info in images:
                                img_url = f"{comfyui_url}/view?filename={img_info['filename']}&subfolder={img_info.get('subfolder','')}&type=output"
                                img_r = await client.get(img_url)
                                if img_r.status_code == 200:
                                    img_frames.append(img_r.content)
                            if img_frames:
                                from io import BytesIO
                                from PIL import Image as PILImage
                                pil_frames = [PILImage.open(BytesIO(f)) for f in img_frames]
                                gif_buf = BytesIO()
                                pil_frames[0].save(gif_buf, format='GIF', save_all=True, append_images=pil_frames[1:], duration=int(1000/fps), loop=0)
                                b64 = _b64.b64encode(gif_buf.getvalue()).decode()
                                return JSONResponse({"video": f"data:image/gif;base64,{b64}", "frames": len(img_frames), "fps": fps, "format": "gif", "provider": "ComfyUI AnimateDiff (GIF)"})
                    return JSONResponse({"error": "影片生成完成但無輸出檔案"}, status_code=500)
            return JSONResponse({"error": "影片生成超時（10分鐘）"}, status_code=504)
    except httpx.ConnectError:
        return JSONResponse({"error": f"ComfyUI 連線中斷 ({comfyui_url})"}, status_code=503)
    except Exception as e:
        return JSONResponse({"error": f"影片生成異常: {str(e)[:300]}"}, status_code=500)

@app.get("/api/comfyui/video-status")
async def comfyui_video_status():
    """檢查 ComfyUI 是否支援影片生成（AnimateDiff / SVD）"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{COMFYUI_BASE}/object_info")
            if r.status_code == 200:
                nodes = set(r.json().keys())
                return JSONResponse({
                    "online": True,
                    "animatediff": "ADE_AnimateDiffLoaderWithContext" in nodes or "AnimateDiffLoaderV1" in nodes,
                    "svd": "SVD_img2vid_Conditioning" in nodes,
                    "wan": "WanVideoTextEncode" in nodes,
                    "vhs": "VHS_VideoCombine" in nodes,
                })
    except Exception:
        pass
    return JSONResponse({"online": False, "animatediff": False, "svd": False, "wan": False, "vhs": False})

print("✅ 本地運算輔助 API 已掛載 → /api/ai/translate-prompt, /api/comfyui/generate-video")

if __name__ == "__main__":
    print(f"🌉 Smart Bridge 啟動於 http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)

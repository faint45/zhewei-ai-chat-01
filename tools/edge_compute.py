"""
築未科技大腦 - 邊緣計算軟體
本地節點：推理、前處理、狀態上報，不依賴雲端

擴充功能：
- 多節點角色（compute, sensor, gateway, display, storage）
- 任務佇列系統（TaskQueue, Worker）
- 多後端推理支援（可配置多個模型後端）
- 狀態上報整合
"""
import asyncio
import json
import os
import platform
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

try:
    import httpx
except ImportError:
    httpx = None

BASE = Path(__file__).parent.resolve()

# ===== 節點角色定義 =====
class NodeRole(str, Enum):
    COMPUTE = "compute"  # 運算節點（預設）
    SENSOR = "sensor"  # 感測器節點
    GATEWAY = "gateway"  # 閘道節點
    DISPLAY = "display"  # 顯示節點
    STORAGE = "storage"  # 儲存節點

    @classmethod
    def all_roles(cls) -> list[str]:
        return [role.value for role in cls]


# ===== 任務優先級 =====
class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


# ===== 任務狀態 =====
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class EdgeNode:
    name: str
    role: str = "compute"
    status: str = "idle"
    last_ping: float = 0
    latency_ms: float = 0
    capabilities: list[str] = field(default_factory=list)  # 節點能力清單
    metadata: dict = field(default_factory=dict)  # 節點元數據


@dataclass
class InferenceBackend:
    """推理後端設定"""
    name: str  # 後端名稱（如 ollama, groq, gemini）
    base_url: str  # API 基礎 URL
    model: str  # 模型名稱
    enabled: bool = True  # 是否啟用
    timeout: int = 60  # 超時時間（秒）
    api_key: Optional[str] = None  # API 金鑰（可選）


@dataclass
class Task:
    """任務定義"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "inference"  # 任務類型
    payload: dict = field(default_factory=dict)  # 任務載荷
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class EdgeCompute:
    """
    邊緣計算節點管理：本地推理、任務佇列、狀態上報
    """

    def __init__(self):
        self.nodes: list[EdgeNode] = []
        self._start_time = time.perf_counter()
        self._ops = 0
        self._bytes = 0
        self._lock = threading.Lock()
        
        # 任務佇列
        self._task_queue: deque[Task] = deque()
        self._task_lock = threading.Lock()
        self._running_tasks: dict[str, Task] = {}
        
        # 推理後端
        self._backends: list[InferenceBackend] = []
        self._current_backend_index = 0
        
        # 工作執行緒
        self._worker_running = False
        self._worker_thread: Optional[threading.Thread] = None
        
        # 初始化後端
        self._init_backends()

    def _init_backends(self):
        """初始化推理後端（從環境變數讀取）"""
        # Ollama 後端（預設）
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
        self._backends.append(InferenceBackend(
            name="ollama",
            base_url=ollama_url,
            model=ollama_model,
            enabled=True,
            timeout=60
        ))
        
        # Groq 後端（可選）
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        if groq_key and not groq_key.startswith("your-"):
            self._backends.append(InferenceBackend(
                name="groq",
                base_url="https://api.groq.com/openai/v1",
                model=os.environ.get("GROQ_MODEL", "llama3-70b-8192"),
                enabled=True,
                timeout=30,
                api_key=groq_key
            ))
        
        # Gemini 後端（可選）
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if gemini_key and not gemini_key.startswith("your-"):
            self._backends.append(InferenceBackend(
                name="gemini",
                base_url="https://generativelanguage.googleapis.com/v1beta",
                model=os.environ.get("GEMINI_MODEL", "gemini-pro"),
                enabled=True,
                timeout=30,
                api_key=gemini_key
            ))

    def register_node(
        self,
        name: str,
        role: str = "compute",
        capabilities: Optional[list[str]] = None,
        metadata: Optional[dict] = None
    ) -> EdgeNode:
        """
        註冊邊緣節點
        
        Args:
            name: 節點名稱
            role: 節點角色（compute, sensor, gateway, display, storage）
            capabilities: 節點能力清單
            metadata: 節點元數據
        """
        with self._lock:
            # 驗證角色
            valid_roles = NodeRole.all_roles()
            if role not in valid_roles:
                role = "compute"
            
            n = EdgeNode(
                name=name,
                role=role,
                capabilities=capabilities or [],
                metadata=metadata or {}
            )
            self.nodes.append(n)
            return n

    def get_node_by_name(self, name: str) -> Optional[EdgeNode]:
        """依名稱查找節點"""
        with self._lock:
            for node in self.nodes:
                if node.name == name:
                    return node
        return None

    def get_nodes_by_role(self, role: str) -> list[EdgeNode]:
        """依角色查找節點"""
        with self._lock:
            return [node for node in self.nodes if node.role == role]
        return []

    def record_op(self, bytes_count: int = 0):
        with self._lock:
            self._ops += 1
            self._bytes += bytes_count

    def get_throughput_mbps(self) -> float:
        elapsed = max(time.perf_counter() - self._start_time, 0.001)
        return self._bytes / elapsed / 1024 / 1024

    def get_ops_rate(self) -> float:
        elapsed = max(time.perf_counter() - self._start_time, 0.001)
        return self._ops / elapsed

    def ping_service(self, service_url: str) -> tuple[bool, float]:
        """
        偵測指定服務是否就緒，回傳 (成功, 延遲 ms)
        支援多種服務類型（Ollama、自訂 API 等）
        """
        if not httpx:
            return False, 0.0
        t0 = time.perf_counter()
        try:
            with httpx.Client(timeout=3.0) as c:
                r = c.get(service_url)
                return r.status_code == 200, (time.perf_counter() - t0) * 1000
        except Exception:
            pass
        return False, (time.perf_counter() - t0) * 1000

    async def ping_ollama(self) -> tuple[bool, float]:
        """偵測本地 Ollama 是否就緒，回傳 (成功, 延遲 ms)"""
        if not httpx:
            return False, 0.0
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=3.0) as c:
                r = await c.get(f"{os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')}/api/tags")
                if r.status_code == 200:
                    return True, (time.perf_counter() - t0) * 1000
        except Exception:
            pass
        return False, (time.perf_counter() - t0) * 1000

    async def ping_all_backends(self) -> dict[str, tuple[bool, float]]:
        """
        偵測所有推理後端是否就緒
        
        Returns:
            後端名稱 -> (成功, 延遲 ms) 的字典
        """
        results = {}
        for backend in self._backends:
            if not backend.enabled:
                results[backend.name] = (False, 0.0)
                continue
            
            t0 = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=3.0) as c:
                    if backend.name == "ollama":
                        r = await c.get(f"{backend.base_url}/api/tags")
                        results[backend.name] = (r.status_code == 200, (time.perf_counter() - t0) * 1000)
                    elif backend.name in ("groq", "gemini"):
                        # 其他後端使用 health check 或 models API
                        r = await c.get(
                            f"{backend.base_url}/models",
                            headers={"Authorization": f"Bearer {backend.api_key}"} if backend.api_key else None
                        )
                        results[backend.name] = (r.status_code == 200, (time.perf_counter() - t0) * 1000)
            except Exception:
                results[backend.name] = (False, (time.perf_counter() - t0) * 1000)
        return results

    def get_backend(self, name: Optional[str] = None) -> Optional[InferenceBackend]:
        """
        取得推理後端
        
        Args:
            name: 後端名稱，若為 None 則輪循取得啟用的後端
        """
        if name:
            for backend in self._backends:
                if backend.name == name and backend.enabled:
                    return backend
        else:
            # 輪循取得啟用的後端
            enabled = [b for b in self._backends if b.enabled]
            if enabled:
                backend = enabled[self._current_backend_index % len(enabled)]
                self._current_backend_index += 1
                return backend
        return None

    async def local_inference(
        self,
        prompt: str,
        backend: Optional[str] = None,
        **kwargs
    ) -> str | None:
        """
        邊緣推理：支援多後端
        
        Args:
            prompt: 推理提示
            backend: 指定後端名稱（ollama, groq, gemini），None 則自動選擇
            **kwargs: 其他參數
        
        Returns:
            推理結果字串，失敗返回 None
        """
        if not httpx:
            return None
        
        # 取得指定後端或自動選擇
        inference_backend = self.get_backend(backend)
        if not inference_backend:
            # 嘗試使用 Ollama 作為預設
            inference_backend = self.get_backend("ollama")
        
        if not inference_backend:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=inference_backend.timeout) as c:
                headers = {}
                if inference_backend.api_key:
                    headers["Authorization"] = f"Bearer {inference_backend.api_key}"
                
                if inference_backend.name == "ollama":
                    # Ollama API
                    r = await c.post(
                        f"{inference_backend.base_url}/api/generate",
                        json={
                            "model": kwargs.get("model", inference_backend.model),
                            "prompt": prompt,
                            "stream": False
                        },
                        headers=headers
                    )
                    if r.status_code == 200:
                        self.record_op(len(r.content))
                        return r.json().get("response", "").strip()
                
                elif inference_backend.name == "groq":
                    # Groq API（OpenAI 相容）
                    r = await c.post(
                        f"{inference_backend.base_url}/chat/completions",
                        json={
                            "model": kwargs.get("model", inference_backend.model),
                            "messages": [{"role": "user", "content": prompt}],
                            "stream": False
                        },
                        headers=headers
                    )
                    if r.status_code == 200:
                        self.record_op(len(r.content))
                        return r.json()["choices"][0]["message"]["content"].strip()
                
                elif inference_backend.name == "gemini":
                    # Gemini API
                    r = await c.post(
                        f"{inference_backend.base_url}/models/{inference_backend.model}:generateContent?key={inference_backend.api_key}",
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"temperature": kwargs.get("temperature", 0.7)}
                        }
                    )
                    if r.status_code == 200:
                        self.record_op(len(r.content))
                        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            # 記錄錯誤但不中斷
            pass
        
        return None

    def get_system_info(self, include_nodes: bool = False) -> dict:
        """
        取得本機邊緣節點資訊
        
        Args:
            include_nodes: 是否包含所有節點資訊
        """
        info = {
            "host": platform.node() or "local",
            "os": platform.system(),
            "cwd": str(BASE),
            "uptime_sec": round(time.perf_counter() - self._start_time, 2),
            "ops": self._ops,
            "throughput_mbps": round(self.get_throughput_mbps(), 3),
            "ops_rate": round(self.get_ops_rate(), 2),
            "backends": [
                {
                    "name": b.name,
                    "model": b.model,
                    "enabled": b.enabled,
                    "base_url": b.base_url
                }
                for b in self._backends if b.enabled
            ],
            "task_queue_size": self.get_task_queue_size(),
            "running_tasks": len(self._running_tasks),
        }
        
        if include_nodes:
            info["nodes"] = [
                {
                    "name": node.name,
                    "role": node.role,
                    "status": node.status,
                    "latency_ms": round(node.latency_ms, 2),
                    "capabilities": node.capabilities,
                    "metadata": node.metadata
                }
                for node in self.nodes
            ]
        
        return info

    # ===== 任務佇列系統 =====
    
    def submit_task(
        self,
        task_type: str = "inference",
        payload: Optional[dict] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        **kwargs
    ) -> str:
        """
        提交任務到佇列
        
        Args:
            task_type: 任務類型（inference, compute, custom）
            payload: 任務載荷（包含 prompt 等參數）
            priority: 任務優先級
            **kwargs: 其他任務參數
        
        Returns:
            任務 ID
        """
        task = Task(
            type=task_type,
            payload=payload or {},
            priority=priority,
            **kwargs
        )
        
        with self._task_lock:
            # 依優先級插入佇列（高優先級在前）
            inserted = False
            for i, t in enumerate(self._task_queue):
                if task.priority > t.priority:
                    self._task_queue.insert(i, task)
                    inserted = True
                    break
            if not inserted:
                self._task_queue.append(task)
        
        return task.id

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """取得任務狀態"""
        # 檢查正在執行的任務
        if task_id in self._running_tasks:
            task = self._running_tasks[task_id]
            return {
                "id": task.id,
                "type": task.type,
                "status": task.status.value,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "result": task.result,
                "error": task.error
            }
        
        # 檢查佇列中的任務
        with self._task_lock:
            for task in self._task_queue:
                if task.id == task_id:
                    return {
                        "id": task.id,
                        "type": task.type,
                        "status": task.status.value,
                        "created_at": task.created_at,
                        "priority": task.priority.value
                    }
        
        return None

    def get_task_queue_size(self) -> int:
        """取得任務佇列大小"""
        with self._task_lock:
            return len(self._task_queue)

    def cancel_task(self, task_id: str) -> bool:
        """取消任務"""
        with self._task_lock:
            for i, task in enumerate(self._task_queue):
                if task.id == task_id:
                    task.status = TaskStatus.CANCELLED
                    self._task_queue.remove(task)
                    return True
        
        if task_id in self._running_tasks:
            # 正在執行的任務無法直接取消，只能標記
            return False
        
        return False

    async def _process_task(self, task: Task) -> dict:
        """
        處理單個任務
        
        Returns:
            {"success": bool, "result": Any, "error": Optional[str]}
        """
        try:
            if task.type == "inference":
                # 推理任務
                prompt = task.payload.get("prompt", "")
                backend = task.payload.get("backend")
                kwargs = task.payload.get("kwargs", {})
                
                result = await self.local_inference(prompt, backend, **kwargs)
                if result:
                    return {"success": True, "result": result}
                else:
                    return {"success": False, "error": "推理失敗"}
            
            elif task.type == "compute":
                # 運算任務
                compute_func = task.payload.get("function")
                args = task.payload.get("args", [])
                kwargs = task.payload.get("kwargs", {})
                
                if callable(compute_func):
                    result = compute_func(*args, **kwargs)
                    return {"success": True, "result": result}
                else:
                    return {"success": False, "error": "無效的函數"}
            
            else:
                # 自訂任務
                return {"success": False, "error": f"未知任務類型: {task.type}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _worker_loop(self, on_task_complete: Optional[Callable] = None):
        """
        工作執行緒主迴圈
        
        Args:
            on_task_complete: 任務完成回呼函數
        """
        while self._worker_running:
            task = None
            
            # 取得任務
            with self._task_lock:
                if self._task_queue:
                    task = self._task_queue.popleft()
            
            if task:
                # 執行任務
                task.status = TaskStatus.PROCESSING
                task.started_at = time.time()
                self._running_tasks[task.id] = task
                
                # 執行任務（使用 asyncio）
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(self._process_task(task))
                finally:
                    loop.close()
                
                # 處理結果
                if result["success"]:
                    task.status = TaskStatus.COMPLETED
                    task.result = result["result"]
                else:
                    task.status = TaskStatus.FAILED
                    task.error = result["error"]
                    
                    # 重試邏輯
                    if task.retry_count < task.max_retries:
                        task.retry_count += 1
                        task.status = TaskStatus.PENDING
                        task.started_at = None
                        with self._task_lock:
                            self._task_queue.appendleft(task)  # 重新加入佇列前端
                        del self._running_tasks[task.id]
                        continue
                
                task.completed_at = time.time()
                del self._running_tasks[task.id]
                
                # 呼叫回呼
                if on_task_complete:
                    on_task_complete(task)
            else:
                # 無任務時短暫休眠
                time.sleep(0.1)

    def start_worker(self, on_task_complete: Optional[Callable] = None):
        """
        啟動工作執行緒
        
        Args:
            on_task_complete: 任務完成回呼函數
        """
        if self._worker_running:
            return
        
        self._worker_running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            args=(on_task_complete,),
            daemon=True,
            name="EdgeWorker"
        )
        self._worker_thread.start()

    def stop_worker(self):
        """停止工作執行緒"""
        self._worker_running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
            self._worker_thread = None

    async def run_edge_daemon(
        self,
        on_status: Optional[Callable] = None,
        on_task_complete: Optional[Callable] = None,
        enable_worker: bool = True,
        enable_reporting: bool = False,
        report_url: Optional[str] = None,
        report_interval: int = 60
    ):
        """
        邊緣守護：週期性 ping 本地服務、更新節點狀態、處理任務佇列、上報狀態
        
        Args:
            on_status: 狀態回呼函數，每輪呼叫一次
            on_task_complete: 任務完成回呼函數
            enable_worker: 是否啟動工作執行緒
            enable_reporting: 是否啟用狀態上報
            report_url: 上報 URL（HTTP POST）
            report_interval: 上報間隔（秒）
        """
        # 啟動工作執行緒
        if enable_worker:
            self.start_worker(on_task_complete)
        
        # 註冊本地節點
        local = self.register_node("local", "compute")
        
        # 多服務 ping 配置
        ping_services = {
            "ollama": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/tags",
        }
        
        # 檢查額外服務（可配置）
        extra_services = os.environ.get("EDGE_PING_SERVICES", "").strip()
        if extra_services:
            try:
                services_list = json.loads(extra_services)
                ping_services.update(services_list)
            except (json.JSONDecodeError, TypeError):
                pass
        
        last_report_time = 0
        
        while True:
            now = time.time()
            
            # Ping 所有後端
            backend_results = await self.ping_all_backends()
            
            # Ping Ollama（向後相容）
            ollama_ok = backend_results.get("ollama", (False, 0.0))[0]
            ollama_lat = backend_results.get("ollama", (False, 0.0))[1]
            
            # 更新節點狀態
            local.status = "ready" if ollama_ok else "offline"
            local.last_ping = now
            local.latency_ms = ollama_lat
            
            # 取得系統資訊
            info = self.get_system_info(include_nodes=True)
            info["services"] = {}
            
            # Ping 額外服務
            for service_name, service_url in ping_services.items():
                ok, lat = self.ping_service(service_url)
                info["services"][service_name] = {
                    "ready": ok,
                    "latency_ms": round(lat, 1)
                }
            
            # 添加後端狀態
            info["backends_status"] = {
                name: {"ready": ok, "latency_ms": round(lat, 1)}
                for name, (ok, lat) in backend_results.items()
            }
            
            # 狀態上報
            if enable_reporting and report_url and (now - last_report_time) >= report_interval:
                await self._report_status(report_url, info)
                last_report_time = now
            
            # 呼叫狀態回呼
            if on_status:
                on_status(info)
            
            await asyncio.sleep(10)

    async def _report_status(self, url: str, status_data: dict):
        """
        上報狀態到指定 URL
        
        Args:
            url: 上報 URL
            status_data: 狀態資料
        """
        if not httpx:
            return
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    url,
                    json=status_data,
                    headers={"Content-Type": "application/json"}
                )
        except Exception:
            pass  # 上報失敗不中斷守護


_edge: EdgeCompute | None = None


def get_edge() -> EdgeCompute:
    global _edge
    if _edge is None:
        _edge = EdgeCompute()
    return _edge


async def main():
    """演示邊緣計算系統功能"""
    edge = get_edge()
    
    # 註冊多角色節點
    print("=== 註冊邊緣節點 ===")
    edge.register_node("local", "compute", capabilities=["inference", "compute"])
    edge.register_node("sensor_01", "sensor", capabilities=["temperature", "humidity"])
    edge.register_node("gateway_main", "gateway", capabilities=["routing", "filtering"])
    edge.register_node("display_hall", "display", capabilities=["streaming", "recording"])
    edge.register_node("storage_local", "storage", capabilities=["backup", "archival"])
    
    # 提交推理任務
    print("\n=== 提交推理任務 ===")
    task_id = edge.submit_task(
        task_type="inference",
        payload={
            "prompt": "請用一句話說明什麼是邊緣計算。",
            "backend": None  # 自動選擇後端
        },
        priority=TaskPriority.NORMAL
    )
    print(f"任務已提交: {task_id}")
    
    # 任務完成回呼
    def on_task_complete(task):
        print(f"\n=== 任務完成 ===")
        print(f"任務 ID: {task.id}")
        print(f"類型: {task.type}")
        print(f"狀態: {task.status.value}")
        print(f"結果: {task.result}")
        if task.error:
            print(f"錯誤: {task.error}")
        print(f"執行時間: {task.completed_at - task.started_at:.2f} 秒")
    
    # 狀態更新回呼
    def on_status(info):
        print(f"\n=== 系統狀態 ===")
        print(f"運行時間: {info['uptime_sec']:.2f} 秒")
        print(f"運算次數: {info['ops']}")
        print(f"吞吐量: {info['throughput_mbps']} MB/s")
        print(f"任務佇列: {info['task_queue_size']} 個")
        print(f"執行中任務: {info['running_tasks']} 個")
        print(f"可用後端: {len(info['backends'])} 個")
        
        if "services" in info:
            print(f"\n=== 服務狀態 ===")
            for name, status in info["services"].items():
                print(f"{name}: {'就緒' if status['ready'] else '離線'} (延遲: {status['latency_ms']} ms)")
        
        if "backends_status" in info:
            print(f"\n=== 推理後端狀態 ===")
            for name, status in info["backends_status"].items():
                print(f"{name}: {'就緒' if status['ready'] else '離線'} (延遲: {status['latency_ms']} ms)")
    
    # 啟動守護（啟用工作執行緒）
    print("\n=== 啟動邊緣守護 ===")
    await edge.run_edge_daemon(
        on_status=on_status,
        on_task_complete=on_task_complete,
        enable_worker=True,
        enable_reporting=False
    )


# ===== 使用範例 =====

async def example_multi_nodes():
    """多節點範例"""
    edge = get_edge()
    
    # 註冊感測器節點
    sensor = edge.register_node(
        "sensor_temp_01",
        "sensor",
        capabilities=["temperature", "pressure"],
        metadata={"location": "zone_a", "interval": 5}
    )
    
    # 註冊閘道節點
    gateway = edge.register_node(
        "gateway_main",
        "gateway",
        capabilities=["routing", "aggregation"],
        metadata={"bandwidth": "1Gbps", "latency": "5ms"}
    )
    
    # 依角色查找節點
    sensors = edge.get_nodes_by_role("sensor")
    print(f"感測器節點數量: {len(sensors)}")
    
    # 取得系統資訊（含節點）
    info = edge.get_system_info(include_nodes=True)
    print(f"總節點數: {len(info['nodes'])}")
    
    # 提交運算任務
    def compute_function(x, y):
        return x * y + 100
    
    task_id = edge.submit_task(
        task_type="compute",
        payload={
            "function": compute_function,
            "args": [5, 3],
            "kwargs": {}
        },
        priority=TaskPriority.HIGH
    )
    print(f"運算任務已提交: {task_id}")


async def example_multi_backend():
    """多後端推理範例"""
    edge = get_edge()
    
    # 測試不同後端
    prompts = [
        "什麼是 Python？",
        "解釋機器學習的基本概念。",
        "寫一個快速排序演算法。"
    ]
    
    for i, prompt in enumerate(prompts):
        # 指定使用 Ollama
        task_id = edge.submit_task(
            task_type="inference",
            payload={
                "prompt": prompt,
                "backend": "ollama",
                "kwargs": {"model": "gemma3:4b"}
            },
            priority=TaskPriority.NORMAL
        )
        print(f"提示 {i+1} (Ollama) 任務 ID: {task_id}")
    
    # 自動選擇後端（輪循）
    for i, prompt in enumerate(prompts):
        task_id = edge.submit_task(
            task_type="inference",
            payload={
                "prompt": prompt,
                "backend": None,  # 自動選擇
                "kwargs": {}
            },
            priority=TaskPriority.NORMAL
        )
        print(f"提示 {i+1} (自動選擇) 任務 ID: {task_id}")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
築未科技 — 智慧 Ollama 路由模組
用於混合部署：自動偵測本地 GPU Ollama 與雲端 CPU Ollama，選擇最佳資源
"""

import os
import time
import requests
from typing import Optional, Dict, List
from datetime import datetime, timedelta

class SmartOllamaRouter:
    """
    智慧 Ollama 路由器
    - 自動偵測本地 GPU Ollama 可用性
    - 本地不可用時自動降級為雲端 CPU Ollama
    - 快取偵測結果以減少延遲
    """
    
    def __init__(self):
        # 本地 GPU Ollama（透過 Cloudflare Tunnel）
        self.gpu_url = os.getenv("OLLAMA_GPU_URL", "https://ollama-gpu.zhe-wei.net")
        
        # 雲端 CPU Ollama（Docker 內部）
        self.cpu_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        
        # 偵測超時（秒）
        self.gpu_timeout = int(os.getenv("OLLAMA_GPU_TIMEOUT", "5"))
        self.cpu_timeout = int(os.getenv("OLLAMA_CPU_TIMEOUT", "10"))
        
        # 快取設定
        self.cache_duration = int(os.getenv("OLLAMA_CACHE_DURATION", "60"))  # 快取 60 秒
        self._cache = {
            "gpu_available": None,
            "gpu_models": [],
            "cpu_models": [],
            "last_check": None
        }
        
        # 統計資訊
        self.stats = {
            "gpu_requests": 0,
            "cpu_requests": 0,
            "gpu_failures": 0,
            "last_gpu_success": None,
            "last_cpu_success": None
        }
    
    def _check_ollama_health(self, base_url: str, timeout: int) -> tuple[bool, List[str]]:
        """
        檢查 Ollama 服務健康狀態
        
        Returns:
            (is_available, available_models)
        """
        try:
            response = requests.get(
                f"{base_url}/api/tags",
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                return True, models
            
            return False, []
        
        except requests.exceptions.Timeout:
            return False, []
        except requests.exceptions.ConnectionError:
            return False, []
        except Exception:
            return False, []
    
    def _update_cache(self):
        """更新快取：檢查 GPU 和 CPU Ollama 可用性"""
        # 先檢查 GPU（快速超時）
        gpu_available, gpu_models = self._check_ollama_health(
            self.gpu_url, 
            self.gpu_timeout
        )
        
        # 再檢查 CPU（較長超時）
        cpu_available, cpu_models = self._check_ollama_health(
            self.cpu_url,
            self.cpu_timeout
        )
        
        self._cache = {
            "gpu_available": gpu_available,
            "gpu_models": gpu_models,
            "cpu_models": cpu_models,
            "last_check": datetime.now()
        }
        
        return gpu_available, cpu_available
    
    def _is_cache_valid(self) -> bool:
        """檢查快取是否有效"""
        if self._cache["last_check"] is None:
            return False
        
        elapsed = (datetime.now() - self._cache["last_check"]).total_seconds()
        return elapsed < self.cache_duration
    
    def get_best_ollama_url(self, prefer_gpu: bool = True) -> str:
        """
        取得最佳 Ollama URL
        
        Args:
            prefer_gpu: 是否優先使用 GPU（預設 True）
        
        Returns:
            最佳 Ollama base URL
        """
        # 檢查快取
        if not self._is_cache_valid():
            self._update_cache()
        
        gpu_available = self._cache["gpu_available"]
        
        # 優先使用 GPU（如果可用）
        if prefer_gpu and gpu_available:
            self.stats["gpu_requests"] += 1
            self.stats["last_gpu_success"] = datetime.now()
            return self.gpu_url
        
        # 降級為 CPU
        self.stats["cpu_requests"] += 1
        self.stats["last_cpu_success"] = datetime.now()
        return self.cpu_url
    
    def get_available_models(self, source: str = "auto") -> List[str]:
        """
        取得可用模型列表
        
        Args:
            source: "gpu", "cpu", 或 "auto"（自動選擇）
        
        Returns:
            可用模型列表
        """
        if not self._is_cache_valid():
            self._update_cache()
        
        if source == "gpu":
            return self._cache["gpu_models"]
        elif source == "cpu":
            return self._cache["cpu_models"]
        else:  # auto
            if self._cache["gpu_available"]:
                return self._cache["gpu_models"]
            return self._cache["cpu_models"]
    
    def get_recommended_model(self, task_type: str = "general") -> str:
        """
        根據任務類型推薦模型
        
        Args:
            task_type: "general", "code", "vision", "lightweight"
        
        Returns:
            推薦的模型名稱
        """
        available_models = self.get_available_models()
        
        # GPU 可用時的推薦
        if self._cache["gpu_available"]:
            if task_type == "code":
                # 程式碼：32b 品質最高，8b 次之
                for model in ["qwen3:32b", "qwen3:8b", "qwen3:4b", "zhewei-brain"]:
                    if model in available_models:
                        return model
            elif task_type == "reasoning":
                # 深度推理：32b 優先
                for model in ["qwen3:32b", "qwen3:8b", "zhewei-brain"]:
                    if model in available_models:
                        return model
            elif task_type == "vision":
                for model in ["moondream", "gemma3:4b"]:
                    if model in available_models:
                        return model
            elif task_type == "lightweight":
                # 輕量快速：30b MoE (3B active) 或 4b
                for model in ["qwen3:30b", "qwen3:4b", "gemma3:4b"]:
                    if model in available_models:
                        return model
            else:  # general
                for model in ["qwen3:32b", "qwen3:8b", "qwen3:30b", "qwen3:4b", "gemma3:4b"]:
                    if model in available_models:
                        return model
        
        # CPU 降級時的推薦（輕量模型）
        for model in ["qwen3:30b", "qwen3:4b", "gemma3:4b", "qwen3:8b"]:
            if model in available_models:
                return model
        
        # 如果都沒有，返回第一個可用模型
        return available_models[0] if available_models else "qwen3:4b"
    
    def get_status(self) -> Dict:
        """
        取得路由器狀態
        
        Returns:
            包含狀態資訊的字典
        """
        if not self._is_cache_valid():
            self._update_cache()
        
        return {
            "gpu": {
                "url": self.gpu_url,
                "available": self._cache["gpu_available"],
                "models": self._cache["gpu_models"],
                "requests": self.stats["gpu_requests"],
                "last_success": self.stats["last_gpu_success"].isoformat() if self.stats["last_gpu_success"] else None
            },
            "cpu": {
                "url": self.cpu_url,
                "available": True,  # CPU 應該總是可用
                "models": self._cache["cpu_models"],
                "requests": self.stats["cpu_requests"],
                "last_success": self.stats["last_cpu_success"].isoformat() if self.stats["last_cpu_success"] else None
            },
            "current_mode": "GPU" if self._cache["gpu_available"] else "CPU",
            "cache_valid_until": (self._cache["last_check"] + timedelta(seconds=self.cache_duration)).isoformat() if self._cache["last_check"] else None
        }
    
    def force_refresh(self):
        """強制刷新快取"""
        self._update_cache()

    def get_gpu_config(self, model: str) -> Dict:
        """
        根據模型大小自動配置 GPU offload 參數
        RTX 5070 Ti 16GB + RTX 4060 Ti 8GB = 24GB 總 VRAM + 64GB RAM
        """
        model_lower = model.lower()
        # 70B+ 模型：跨雙卡 + CPU offload
        if any(s in model_lower for s in ["70b", "72b", "65b", "67b"]):
            return {"num_gpu": 35, "num_ctx": 4096, "num_batch": 512,
                    "expected_speed": "8-15 tok/s", "mode": "dual_gpu_cpu_offload"}
        # 30-40B 模型：全 GPU（雙卡 24GB 可全載 Q4）
        if any(s in model_lower for s in ["34b", "32b", "33b", "27b"]):
            return {"num_gpu": 99, "num_ctx": 8192, "num_batch": 512,
                    "expected_speed": "20-35 tok/s", "mode": "full_dual_gpu"}
        # 14B 模型：全 GPU（單卡 16GB 即可）
        if any(s in model_lower for s in ["14b", "13b"]):
            return {"num_gpu": 99, "num_ctx": 8192, "num_batch": 512,
                    "expected_speed": "35-50 tok/s", "mode": "full_gpu"}
        # 8B 以下：全 GPU（單卡綽綽有餘）
        return {"num_gpu": 99, "num_ctx": 8192, "num_batch": 512,
                "expected_speed": "50-120 tok/s", "mode": "full_gpu"}


# 全域單例
_router_instance = None

def get_router() -> SmartOllamaRouter:
    """取得全域路由器實例"""
    global _router_instance
    if _router_instance is None:
        _router_instance = SmartOllamaRouter()
    return _router_instance


# 便捷函數
def get_ollama_url(prefer_gpu: bool = True) -> str:
    """取得最佳 Ollama URL"""
    return get_router().get_best_ollama_url(prefer_gpu)


def get_recommended_model(task_type: str = "general") -> str:
    """取得推薦模型"""
    return get_router().get_recommended_model(task_type)


def get_router_status() -> Dict:
    """取得路由器狀態"""
    return get_router().get_status()


if __name__ == "__main__":
    # 測試路由器
    print("=== 智慧 Ollama 路由器測試 ===\n")
    
    router = get_router()
    
    # 取得狀態
    status = router.get_status()
    print(f"當前模式: {status['current_mode']}")
    print(f"\nGPU Ollama:")
    print(f"  URL: {status['gpu']['url']}")
    print(f"  可用: {status['gpu']['available']}")
    print(f"  模型: {', '.join(status['gpu']['models'][:3])}...")
    
    print(f"\nCPU Ollama:")
    print(f"  URL: {status['cpu']['url']}")
    print(f"  模型: {', '.join(status['cpu']['models'][:3])}...")
    
    # 推薦模型
    print(f"\n推薦模型:")
    print(f"  通用任務: {router.get_recommended_model('general')}")
    print(f"  代碼任務: {router.get_recommended_model('code')}")
    print(f"  視覺任務: {router.get_recommended_model('vision')}")
    
    # 取得最佳 URL
    print(f"\n最佳 Ollama URL: {router.get_best_ollama_url()}")

#!/usr/bin/env python3
"""
築未科技 — 量化推理優化模組（exllamav2 替代方案）
利用 llama-cpp-python + Ollama 原生量化，在 RTX 4060 Ti 8GB 上跑大模型

功能：
- GGUF 模型直接載入（llama-cpp-python）
- GPU/CPU 混合推理（自動分配 layer）
- Ollama 大模型量化建議（70B Q2/Q3 可跑）
- VRAM 用量估算 + 最佳量化方案推薦
- 模型效能比較基準測試
"""

import os
import time
import math
import requests
from typing import Dict, List, Optional

OLLAMA_BASE = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11460").rstrip("/")

# 硬體規格（RTX 5070 Ti 16GB + RTX 4060 Ti 8GB = 24GB VRAM + 64GB RAM）
GPU_VRAM_GB = float(os.environ.get("GPU_VRAM_GB", "24"))
SYSTEM_RAM_GB = float(os.environ.get("SYSTEM_RAM_GB", "64"))


# ═══════════════════════════════════════════
# VRAM 估算引擎
# ═══════════════════════════════════════════

# 量化格式的每參數位元數
QUANT_BPW = {
    "F16": 16.0, "Q8_0": 8.5, "Q6_K": 6.6, "Q5_K_M": 5.7,
    "Q5_K_S": 5.5, "Q5_0": 5.5, "Q4_K_M": 4.8, "Q4_K_S": 4.5,
    "Q4_0": 4.5, "Q3_K_M": 3.9, "Q3_K_S": 3.5, "Q3_K_L": 4.1,
    "Q2_K": 3.4, "IQ4_XS": 4.3, "IQ3_M": 3.7, "IQ2_M": 2.7,
    "IQ2_S": 2.5, "IQ1_M": 1.8,
}

# 常見模型的參數量（十億）
MODEL_PARAMS_B = {
    "1b": 1, "1.5b": 1.5, "3b": 3, "4b": 4, "7b": 7, "8b": 8,
    "13b": 13, "14b": 14, "27b": 27, "32b": 32, "34b": 34,
    "70b": 70, "72b": 72, "405b": 405,
}


def estimate_vram(params_b: float, quant: str = "Q4_K_M", ctx_len: int = 4096) -> Dict:
    """
    估算模型 VRAM 用量

    Args:
        params_b: 參數量（十億）
        quant: 量化格式
        ctx_len: 上下文長度

    Returns:
        {"model_gb": float, "kv_cache_gb": float, "total_gb": float,
         "fits_gpu": bool, "gpu_layers": int, "mode": str}
    """
    bpw = QUANT_BPW.get(quant, 4.8)
    model_gb = (params_b * 1e9 * bpw / 8) / 1e9
    # KV cache: ~2 bytes per token per layer per head_dim
    n_layers = max(1, int(params_b * 3.5))  # 粗估 layer 數
    kv_cache_gb = (ctx_len * n_layers * 128 * 2 * 2) / 1e9  # 2 for K+V
    total_gb = model_gb + kv_cache_gb + 0.5  # +0.5 for overhead

    # 計算可放入 GPU 的 layer 數
    available_vram = GPU_VRAM_GB - 0.8  # 保留 0.8GB 給系統
    if total_gb <= available_vram:
        gpu_layers = 999  # 全部放 GPU
        mode = "full_gpu"
    elif model_gb <= available_vram:
        gpu_layers = 999
        mode = "gpu_model_cpu_kv"
    else:
        # 部分 offload
        layer_size = model_gb / n_layers
        gpu_layers = max(0, int(available_vram / layer_size))
        if gpu_layers > 0:
            mode = f"hybrid_{gpu_layers}_layers_gpu"
        else:
            mode = "cpu_only"

    return {
        "params_b": params_b,
        "quant": quant,
        "ctx_len": ctx_len,
        "model_gb": round(model_gb, 2),
        "kv_cache_gb": round(kv_cache_gb, 2),
        "total_gb": round(total_gb, 2),
        "fits_gpu": total_gb <= GPU_VRAM_GB,
        "gpu_layers": gpu_layers,
        "mode": mode,
        "gpu_vram_gb": GPU_VRAM_GB,
        "system_ram_gb": SYSTEM_RAM_GB,
    }


def recommend_quant(params_b: float, target_speed: str = "balanced") -> List[Dict]:
    """
    推薦最佳量化方案

    Args:
        params_b: 參數量（十億）
        target_speed: "fast" / "balanced" / "quality"

    Returns:
        排序後的量化方案列表
    """
    results = []
    for quant, bpw in sorted(QUANT_BPW.items(), key=lambda x: x[1], reverse=True):
        est = estimate_vram(params_b, quant)
        # 品質分數（bpw 越高越好）
        quality = min(100, int(bpw / 16 * 100))
        # 速度分數（越小越快）
        speed = 100 if est["fits_gpu"] else max(10, int(50 * est["gpu_layers"] / max(1, params_b * 3.5)))

        if target_speed == "fast":
            score = speed * 0.7 + quality * 0.3
        elif target_speed == "quality":
            score = speed * 0.3 + quality * 0.7
        else:
            score = speed * 0.5 + quality * 0.5

        feasible = est["total_gb"] <= (GPU_VRAM_GB + SYSTEM_RAM_GB - 4)
        results.append({
            "quant": quant,
            "bpw": bpw,
            "model_gb": est["model_gb"],
            "total_gb": est["total_gb"],
            "fits_gpu": est["fits_gpu"],
            "gpu_layers": est["gpu_layers"],
            "mode": est["mode"],
            "quality": quality,
            "speed": speed,
            "score": round(score, 1),
            "feasible": feasible,
        })

    results = [r for r in results if r["feasible"]]
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:5]


# ═══════════════════════════════════════════
# llama-cpp-python 直接推理
# ═══════════════════════════════════════════

class GGUFRunner:
    """
    直接載入 GGUF 模型推理（不經過 Ollama）
    適合需要精細控制 GPU offload 的場景
    """

    def __init__(self):
        self._model = None
        self._model_path = None

    def load(self, model_path: str, n_gpu_layers: int = -1, n_ctx: int = 4096) -> Dict:
        """
        載入 GGUF 模型

        Args:
            model_path: .gguf 檔案路徑
            n_gpu_layers: GPU layer 數（-1 = 自動）
            n_ctx: 上下文長度
        """
        try:
            from llama_cpp import Llama
        except ImportError:
            return {"ok": False, "error": "llama-cpp-python 未安裝"}

        if not os.path.exists(model_path):
            return {"ok": False, "error": f"檔案不存在: {model_path}"}

        start = time.time()
        try:
            self._model = Llama(
                model_path=model_path,
                n_gpu_layers=n_gpu_layers,
                n_ctx=n_ctx,
                verbose=False,
            )
            self._model_path = model_path
            elapsed = round(time.time() - start, 1)
            return {"ok": True, "model": model_path, "load_time_s": elapsed,
                    "n_gpu_layers": n_gpu_layers, "n_ctx": n_ctx}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.3) -> Dict:
        """用已載入的 GGUF 模型生成"""
        if not self._model:
            return {"ok": False, "error": "模型未載入，請先呼叫 load()"}

        start = time.time()
        try:
            output = self._model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                echo=False,
            )
            elapsed = time.time() - start
            text = output["choices"][0]["text"] if output.get("choices") else ""
            tokens = output.get("usage", {}).get("completion_tokens", 0)
            tps = tokens / elapsed if elapsed > 0 else 0
            return {
                "ok": True,
                "response": text.strip(),
                "tokens": tokens,
                "elapsed_s": round(elapsed, 2),
                "tokens_per_sec": round(tps, 1),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def unload(self):
        """卸載模型"""
        self._model = None
        self._model_path = None


# ═══════════════════════════════════════════
# Ollama 大模型量化管理
# ═══════════════════════════════════════════

def get_ollama_model_info(model: str) -> Dict:
    """取得 Ollama 模型的量化和大小資訊"""
    try:
        r = requests.post(f"{OLLAMA_BASE}/api/show", json={"name": model}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            details = data.get("details", {})
            size = data.get("size", 0)
            return {
                "ok": True,
                "model": model,
                "family": details.get("family", ""),
                "parameter_size": details.get("parameter_size", ""),
                "quantization_level": details.get("quantization_level", ""),
                "size_gb": round(size / 1e9, 2) if size else 0,
                "format": details.get("format", ""),
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "unknown"}


def suggest_70b_setup() -> Dict:
    """
    推薦在 RTX 4060 Ti 8GB + 64GB RAM 上跑 70B 模型的最佳設定

    Returns:
        {"recommended_model": str, "quant": str, "ollama_command": str,
         "estimated_speed": str, "settings": dict}
    """
    recs = recommend_quant(70, "balanced")
    best = recs[0] if recs else {"quant": "Q2_K", "gpu_layers": 20, "mode": "hybrid"}

    return {
        "recommended_models": [
            {"name": "qwen3:70b", "note": "最強開源模型，Q2 量化約 26GB"},
            {"name": "llama3.1:70b", "note": "Meta 70B，Q4 量化約 40GB"},
            {"name": "deepseek-r1:70b", "note": "推理模型，Q2 量化約 27GB"},
        ],
        "best_quant": best["quant"],
        "estimated_vram": f"{min(GPU_VRAM_GB, best.get('model_gb', 8))} GB GPU + {best.get('total_gb', 30) - GPU_VRAM_GB:.0f} GB RAM",
        "ollama_commands": [
            "ollama pull qwen3:70b",
            "# 或指定量化版本：",
            "ollama pull qwen3:70b-q2_K",
        ],
        "optimal_settings": {
            "num_gpu": best.get("gpu_layers", 20),
            "num_ctx": 2048,
            "num_batch": 128,
            "num_thread": os.cpu_count() or 8,
        },
        "estimated_speed": "2-5 tok/s（混合 GPU+CPU）",
        "tips": [
            "70B Q2_K 約 26GB，需要 64GB RAM",
            "首次載入約 30-60 秒",
            "建議 num_ctx 不超過 2048 以節省記憶體",
            "可用 keep_alive 保持模型在記憶體中",
        ],
    }


def benchmark_model(model: str, prompt: str = "請用一句話解釋量子計算。") -> Dict:
    """Ollama 模型效能基準測試"""
    try:
        # 預熱
        requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json={"model": model, "prompt": "hi", "stream": False,
                  "options": {"num_predict": 1, "num_gpu": 99}},
            timeout=60,
        )
        # 正式測試
        start = time.time()
        r = requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False,
                  "options": {"num_gpu": 99, "num_batch": 512}},
            timeout=120,
        )
        elapsed = time.time() - start
        if r.status_code == 200:
            data = r.json()
            eval_count = data.get("eval_count", 0)
            eval_duration = data.get("eval_duration", 0)
            prompt_eval_duration = data.get("prompt_eval_duration", 0)
            tps = eval_count / (eval_duration / 1e9) if eval_duration > 0 else 0
            return {
                "ok": True,
                "model": model,
                "tokens": eval_count,
                "tokens_per_sec": round(tps, 1),
                "prompt_eval_ms": round(prompt_eval_duration / 1e6, 1),
                "total_elapsed_s": round(elapsed, 2),
                "response": (data.get("response") or "")[:200],
            }
    except Exception as e:
        return {"ok": False, "model": model, "error": str(e)}
    return {"ok": False, "model": model, "error": "unknown"}


# ═══════════════════════════════════════════
# 全域單例
# ═══════════════════════════════════════════

_gguf_runner: Optional[GGUFRunner] = None


def get_gguf_runner() -> GGUFRunner:
    global _gguf_runner
    if _gguf_runner is None:
        _gguf_runner = GGUFRunner()
    return _gguf_runner

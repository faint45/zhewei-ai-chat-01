# -*- coding: utf-8 -*-
"""
築未科技 — 系統自檢與修復模組
─────────────────────────────
檢查項目：
1. Ollama 連線 + 模型可用性（embed / generate）
2. ChromaDB 知識庫完整性
3. AI Provider API Keys
4. 學習管線端對端驗證
5. 自動修復常見問題
"""
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent
TRAINING_DIR = ROOT / "Jarvis_Training"
DB_DIR = TRAINING_DIR / "chroma_db"

OLLAMA_CANDIDATES = [
    os.environ.get("OLLAMA_BASE_URL", "").strip().rstrip("/"),
    "http://localhost:11434",
    "http://localhost:11460",
    "http://host.docker.internal:11434",
    "http://host.docker.internal:11460",
]
OLLAMA_CANDIDATES = [c for c in OLLAMA_CANDIDATES if c]

EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text:latest").strip()
GENERATE_MODEL = os.environ.get("OLLAMA_MODEL", "zhewei-brain:latest").strip()
COLLECTION_NAME = os.environ.get("LEARNING_COLLECTION", "jarvis_training").strip()


# ═══════════════════════════════════════════
# 檢查函式
# ═══════════════════════════════════════════

def check_ollama_connection() -> dict[str, Any]:
    """檢查 Ollama 是否可連線，回傳可用 base_url。"""
    for base in OLLAMA_CANDIDATES:
        try:
            r = requests.get(f"{base}/api/tags", timeout=3)
            if r.status_code == 200:
                models = [m.get("name", "") for m in (r.json().get("models") or []) if m.get("name")]
                return {"ok": True, "base_url": base, "models": models}
        except Exception:
            continue
    return {"ok": False, "error": "無法連線任何 Ollama 端點", "tried": OLLAMA_CANDIDATES}


def check_embed_model() -> dict[str, Any]:
    """檢查 embedding 模型是否可用。"""
    conn = check_ollama_connection()
    if not conn["ok"]:
        return {"ok": False, "error": "Ollama 不可用", "model": EMBED_MODEL}
    base = conn["base_url"]
    models = conn.get("models", [])
    # 檢查模型是否已拉取
    has_model = any(EMBED_MODEL.split(":")[0] in m for m in models)
    if not has_model:
        return {"ok": False, "error": f"模型 {EMBED_MODEL} 未安裝", "available": models, "base_url": base}
    # 實際測試 embed
    try:
        r = requests.post(
            f"{base}/api/embed",
            json={"model": EMBED_MODEL, "input": "自檢測試"},
            timeout=30,
        )
        if r.status_code == 200:
            embs = r.json().get("embeddings", [])
            if embs and len(embs[0]) > 0:
                return {"ok": True, "model": EMBED_MODEL, "dim": len(embs[0]), "base_url": base}
        return {"ok": False, "error": f"Embed 回應異常: HTTP {r.status_code}", "base_url": base}
    except Exception as e:
        return {"ok": False, "error": str(e), "base_url": base}


def check_generate_model() -> dict[str, Any]:
    """檢查生成模型是否可用（快速測試）。"""
    conn = check_ollama_connection()
    if not conn["ok"]:
        return {"ok": False, "error": "Ollama 不可用", "model": GENERATE_MODEL}
    base = conn["base_url"]
    models = conn.get("models", [])
    # 找到可用的生成模型
    preferred = [GENERATE_MODEL, "zhewei-brain:latest", "qwen3:32b", "qwen3:8b", "qwen3:4b", "gemma3:4b"]
    active_model = None
    for m in preferred:
        if any(m.split(":")[0] in avail for avail in models):
            active_model = m
            break
    if not active_model and models:
        # 排除 embed 模型，取第一個
        gen_models = [m for m in models if "embed" not in m.lower() and "nomic" not in m.lower()]
        active_model = gen_models[0] if gen_models else models[0]
    if not active_model:
        return {"ok": False, "error": "無可用生成模型", "available": models}
    # 快速測試
    try:
        r = requests.post(
            f"{base}/api/generate",
            json={"model": active_model, "prompt": "回答OK", "stream": False, "options": {"num_predict": 5}},
            timeout=30,
        )
        if r.status_code == 200:
            resp = (r.json().get("response") or "").strip()
            return {"ok": True, "model": active_model, "test_response": resp[:50], "base_url": base}
        return {"ok": False, "error": f"生成測試失敗: HTTP {r.status_code}", "model": active_model}
    except Exception as e:
        return {"ok": False, "error": str(e), "model": active_model}


def check_chromadb() -> dict[str, Any]:
    """檢查 ChromaDB 知識庫是否正常。"""
    try:
        import chromadb
    except ImportError:
        return {"ok": False, "error": "chromadb 套件未安裝", "can_repair": True, "repair_hint": "pip install chromadb==1.5.0"}
    version = getattr(chromadb, "__version__", "unknown")
    try:
        if not DB_DIR.exists():
            return {"ok": False, "error": f"資料庫目錄不存在: {DB_DIR}", "can_repair": True, "version": version}
        client = chromadb.PersistentClient(path=str(DB_DIR))
        collections = [c.name for c in client.list_collections()]
        if COLLECTION_NAME not in collections:
            return {
                "ok": False,
                "error": f"Collection '{COLLECTION_NAME}' 不存在",
                "existing": collections,
                "can_repair": True,
                "version": version,
            }
        coll = client.get_collection(COLLECTION_NAME)
        count = coll.count()
        # 抽樣驗證
        sample_ok = True
        sample_error = ""
        if count > 0:
            try:
                sample = coll.get(limit=1, include=["documents", "metadatas"])
                if not sample.get("ids"):
                    sample_ok = False
                    sample_error = "抽樣讀取失敗"
            except Exception as e:
                sample_ok = False
                sample_error = str(e)
        return {
            "ok": True,
            "collection": COLLECTION_NAME,
            "count": count,
            "db_dir": str(DB_DIR),
            "sample_ok": sample_ok,
            "sample_error": sample_error,
            "all_collections": collections,
            "version": version,
        }
    except KeyError as e:
        # chromadb 版本不匹配常見錯誤（'_type' KeyError）
        return {
            "ok": False,
            "error": f"ChromaDB 版本不匹配: {e}（目前 {version}，建議升級至 1.5.0）",
            "can_repair": True,
            "repair_hint": "pip install chromadb==1.5.0",
            "version": version,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "can_repair": True, "version": version}


def check_api_keys() -> dict[str, Any]:
    """檢查各 AI Provider API Key 是否已設定。"""
    keys = {
        "GROQ_API_KEY": {"name": "Groq", "required": False},
        "GEMINI_API_KEY": {"name": "Gemini", "required": False},
        "DEEPSEEK_API_KEY": {"name": "DeepSeek", "required": False},
        "MISTRAL_API_KEY": {"name": "Mistral", "required": False},
        "ANTHROPIC_API_KEY": {"name": "Claude", "required": False},
        "XAI_API_KEY": {"name": "Grok (xAI)", "required": False},
        "HUNYUAN_API_KEY": {"name": "騰訊混元", "required": False},
        "DOUBAO_API_KEY": {"name": "字節豆包", "required": False},
        "DASHSCOPE_API_KEY": {"name": "阿里千尋", "required": False},
        "MINIMAX_API_KEY": {"name": "MiniMax", "required": False},
    }
    results = {}
    available_count = 0
    for env_key, info in keys.items():
        val = os.environ.get(env_key, "").strip()
        has_key = bool(val) and not val.startswith("your-")
        results[info["name"]] = {"set": has_key, "env": env_key}
        if has_key:
            available_count += 1
    return {
        "ok": available_count > 0,
        "available_count": available_count,
        "total": len(keys),
        "providers": results,
        "warning": "至少需要一個外部 AI Provider 才能使用學習大模型精華功能" if available_count == 0 else "",
    }


def check_learning_pipeline() -> dict[str, Any]:
    """端對端驗證學習管線：embed → ChromaDB write → read → delete。"""
    embed_check = check_embed_model()
    if not embed_check["ok"]:
        return {"ok": False, "error": f"Embedding 不可用: {embed_check.get('error')}", "stage": "embed"}

    chroma_check = check_chromadb()
    if not chroma_check["ok"]:
        return {"ok": False, "error": f"ChromaDB 不可用: {chroma_check.get('error')}", "stage": "chromadb"}

    # 端對端測試：寫入 → 查詢 → 刪除
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(DB_DIR))
        coll = client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

        test_id = f"selfcheck_{int(time.time())}"
        test_text = "自檢測試：本地學習系統端對端驗證"
        base = embed_check["base_url"]

        # 1. Embed
        r = requests.post(f"{base}/api/embed", json={"model": EMBED_MODEL, "input": test_text}, timeout=30)
        emb = r.json().get("embeddings", [[]])[0]
        if not emb:
            return {"ok": False, "error": "Embedding 回傳空向量", "stage": "embed"}

        # 2. Write
        coll.upsert(
            ids=[test_id],
            documents=[test_text],
            metadatas=[{"question": "自檢測試", "source": "self_check"}],
            embeddings=[emb],
        )

        # 3. Read back
        got = coll.get(ids=[test_id], include=["documents"])
        if not got.get("ids"):
            return {"ok": False, "error": "寫入後讀取失敗", "stage": "read"}

        # 4. Query (semantic search)
        qr = coll.query(query_embeddings=[emb], n_results=1)
        q_ids = (qr.get("ids") or [[]])[0]
        if test_id not in q_ids:
            return {"ok": False, "error": "語意查詢未命中測試資料", "stage": "query"}

        # 5. Cleanup
        coll.delete(ids=[test_id])

        return {"ok": True, "message": "學習管線端對端驗證通過", "kb_count": coll.count()}
    except Exception as e:
        return {"ok": False, "error": str(e), "stage": "e2e"}


def check_gpu_memory() -> dict[str, Any]:
    """檢查 GPU 記憶體使用狀況。"""
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode()
        total_gb = mem.total / 1024**3
        used_gb = mem.used / 1024**3
        free_gb = mem.free / 1024**3
        usage_pct = used_gb / total_gb * 100
        # 模型大小建議
        if free_gb >= 5:
            suggestion = "8B 模型可全 GPU 運行"
        elif free_gb >= 3:
            suggestion = "4B 模型可全 GPU，8B 需部分 offload"
        else:
            suggestion = "VRAM 不足，建議釋放其他 GPU 程式"
        return {
            "ok": True, "gpu_name": name,
            "total_gb": round(total_gb, 1), "used_gb": round(used_gb, 1),
            "free_gb": round(free_gb, 1), "usage_pct": round(usage_pct, 1),
            "suggestion": suggestion,
        }
    except ImportError:
        return {"ok": False, "error": "pynvml 未安裝（pip install nvidia-ml-py）"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ═══════════════════════════════════════════
# 綜合自檢
# ═══════════════════════════════════════════

def full_check() -> dict[str, Any]:
    """執行完整系統自檢，回傳各項目狀態。"""
    results = {}
    overall_ok = True

    # 1. Ollama 連線
    results["ollama"] = check_ollama_connection()
    if not results["ollama"]["ok"]:
        overall_ok = False

    # 2. Embedding 模型
    results["embed_model"] = check_embed_model()
    if not results["embed_model"]["ok"]:
        overall_ok = False

    # 3. 生成模型
    results["generate_model"] = check_generate_model()
    if not results["generate_model"]["ok"]:
        overall_ok = False

    # 4. ChromaDB
    results["chromadb"] = check_chromadb()
    if not results["chromadb"]["ok"]:
        overall_ok = False

    # 5. API Keys
    results["api_keys"] = check_api_keys()
    # API keys 不影響 overall（本地學習不需要）

    # 6. GPU 記憶體
    results["gpu_memory"] = check_gpu_memory()

    # 7. 學習管線端對端
    if results["embed_model"]["ok"] and results["chromadb"]["ok"]:
        results["learning_pipeline"] = check_learning_pipeline()
        if not results["learning_pipeline"]["ok"]:
            overall_ok = False
    else:
        results["learning_pipeline"] = {"ok": False, "error": "前置條件未通過，跳過端對端測試", "stage": "skip"}
        overall_ok = False

    # 系統資訊
    results["system_info"] = {
        "ollama_models": results.get("ollama", {}).get("models", []),
        "gpu": results.get("gpu_memory", {}),
        "optimization": {
            "bitsandbytes": _check_package("bitsandbytes"),
            "llama_cpp": _check_package("llama_cpp"),
            "exllamav2": _check_package("exllamav2"),
            "torch_cuda": _check_torch_cuda(),
        },
        "ai_modules": {
            "reranker": _check_module("ai_modules.reranker"),
            "rag_fusion": _check_module("ai_modules.rag_fusion"),
            "graph_rag": _check_module("ai_modules.graph_rag"),
            "structured_output": _check_module("ai_modules.structured_output"),
            "smart_chunker": _check_module("ai_modules.smart_chunker"),
            "doc_parser": _check_module("ai_modules.doc_parser"),
            "multi_agent": _check_module("ai_modules.multi_agent"),
            "inference_optimizer": _check_module("ai_modules.inference_optimizer"),
            "quant_optimizer": _check_module("ai_modules.quant_optimizer"),
            "ai_sop": _check_module("ai_modules.ai_sop"),
            "local_independence": _check_module("ai_modules.local_independence"),
            "dspy_optimizer": _check_module("ai_modules.dspy_optimizer"),
        },
        "packages": {
            "litellm": _check_package("litellm"),
            "instructor": _check_package("instructor"),
            "langchain_core": _check_package("langchain_core"),
            "langchain_ollama": _check_package("langchain_ollama"),
            "crewai": _check_package_detail("crewai", "Py3.14不相容，替代: ai_modules.multi_agent v2 (Tool/Task/Crew)"),
            "exllamav2_alt": _check_package_detail("exllamav2", "替代: ai_modules.quant_optimizer (GGUF+llama-cpp)"),
            "llama_cpp": _check_package("llama_cpp"),
            "smolagents": _check_package("smolagents"),
            "dspy": _check_package("dspy"),
            "faster_whisper": _check_package("faster_whisper"),
            "guidance": _check_package("guidance"),
            "networkx": _check_package("networkx"),
            "chonkie": _check_package("chonkie"),
            "sentence_transformers": _check_package("sentence_transformers"),
            "llama_index": _check_package("llama_index"),
            "torch": _check_package("torch"),
        },
    }

    return {
        "ok": overall_ok,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "checks": results,
        "summary": _build_summary(results),
    }


def _build_summary(results: dict) -> list[dict]:
    """產生人類可讀的摘要列表。"""
    items = []
    # Ollama
    o = results.get("ollama", {})
    items.append({
        "name": "Ollama 連線",
        "status": "pass" if o.get("ok") else "fail",
        "detail": f"端點: {o.get('base_url', '?')}，模型數: {len(o.get('models', []))}" if o.get("ok") else o.get("error", ""),
    })
    # Embed
    e = results.get("embed_model", {})
    items.append({
        "name": "Embedding 模型",
        "status": "pass" if e.get("ok") else "fail",
        "detail": f"{e.get('model', '?')} ({e.get('dim', '?')}維)" if e.get("ok") else e.get("error", ""),
    })
    # Generate
    g = results.get("generate_model", {})
    items.append({
        "name": "生成模型",
        "status": "pass" if g.get("ok") else "fail",
        "detail": f"{g.get('model', '?')}" if g.get("ok") else g.get("error", ""),
    })
    # ChromaDB
    c = results.get("chromadb", {})
    ver = c.get("version", "?")
    items.append({
        "name": "ChromaDB 知識庫",
        "status": "pass" if c.get("ok") else "fail",
        "detail": f"{c.get('collection', '?')} ({c.get('count', 0)} 筆) v{ver}" if c.get("ok") else f"{c.get('error', '')} [v{ver}]",
    })
    # API Keys
    a = results.get("api_keys", {})
    items.append({
        "name": "AI Provider Keys",
        "status": "pass" if a.get("ok") else "warn",
        "detail": f"{a.get('available_count', 0)}/{a.get('total', 0)} 個已設定",
    })
    # GPU
    gpu = results.get("gpu_memory", {})
    items.append({
        "name": "GPU 記憶體",
        "status": "pass" if gpu.get("ok") else "warn",
        "detail": f"{gpu.get('gpu_name', '?')} — {gpu.get('free_gb', '?')}GB 可用/{gpu.get('total_gb', '?')}GB — {gpu.get('suggestion', '')}" if gpu.get("ok") else gpu.get("error", ""),
    })
    # Pipeline
    p = results.get("learning_pipeline", {})
    items.append({
        "name": "學習管線 (E2E)",
        "status": "pass" if p.get("ok") else "fail",
        "detail": p.get("message", "") if p.get("ok") else p.get("error", ""),
    })
    return items


def _check_package(name: str) -> bool:
    """Check if a Python package is importable."""
    try:
        __import__(name)
        return True
    except Exception:
        return False


def _check_package_detail(name: str, fallback_note: str = "") -> dict:
    """Check package with detailed status info."""
    try:
        __import__(name)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)[:100], "note": fallback_note}


def _check_module(name: str) -> bool:
    """Check if a project module is importable."""
    try:
        __import__(name)
        return True
    except Exception:
        return False


def _check_torch_cuda() -> dict:
    """Check PyTorch CUDA availability."""
    try:
        import torch
        return {
            "available": torch.cuda.is_available(),
            "version": torch.__version__,
            "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        }
    except Exception:
        return {"available": False, "version": None}


# ═══════════════════════════════════════════
# 自動修復
# ═══════════════════════════════════════════

def repair_all() -> dict[str, Any]:
    """嘗試自動修復所有可修復的問題。"""
    actions = []
    errors = []

    # 1. 嘗試拉取缺失的 embed 模型
    conn = check_ollama_connection()
    if conn["ok"]:
        base = conn["base_url"]
        models = conn.get("models", [])
        if not any(EMBED_MODEL.split(":")[0] in m for m in models):
            actions.append(f"拉取 Embedding 模型: {EMBED_MODEL}")
            try:
                r = requests.post(f"{base}/api/pull", json={"name": EMBED_MODEL, "stream": False}, timeout=300)
                if r.status_code == 200:
                    actions.append(f"✅ {EMBED_MODEL} 拉取成功")
                else:
                    errors.append(f"拉取 {EMBED_MODEL} 失敗: HTTP {r.status_code}")
            except Exception as e:
                errors.append(f"拉取 {EMBED_MODEL} 異常: {e}")

        # 檢查生成模型
        gen_available = [m for m in models if "embed" not in m.lower() and "nomic" not in m.lower()]
        if not gen_available:
            fallback_model = "gemma3:4b"
            actions.append(f"拉取備用生成模型: {fallback_model}")
            try:
                r = requests.post(f"{base}/api/pull", json={"name": fallback_model, "stream": False}, timeout=600)
                if r.status_code == 200:
                    actions.append(f"✅ {fallback_model} 拉取成功")
                else:
                    errors.append(f"拉取 {fallback_model} 失敗: HTTP {r.status_code}")
            except Exception as e:
                errors.append(f"拉取 {fallback_model} 異常: {e}")
    else:
        errors.append("Ollama 不可用，無法修復模型問題")

    # 2. 修復 ChromaDB
    try:
        import chromadb
        DB_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(DB_DIR))
        collections = [c.name for c in client.list_collections()]
        if COLLECTION_NAME not in collections:
            actions.append(f"建立 Collection: {COLLECTION_NAME}")
            client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
            actions.append(f"✅ Collection '{COLLECTION_NAME}' 已建立")
        else:
            coll = client.get_collection(COLLECTION_NAME)
            count = coll.count()
            actions.append(f"ChromaDB 正常 ({count} 筆)")
    except ImportError:
        errors.append("chromadb 未安裝，請執行: pip install chromadb")
    except Exception as e:
        errors.append(f"ChromaDB 修復失敗: {e}")

    # 3. 驗證修復結果
    post_check = full_check()

    return {
        "ok": len(errors) == 0,
        "actions": actions,
        "errors": errors,
        "post_check": post_check,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ═══════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "repair":
        print("=== 系統自動修復 ===")
        result = repair_all()
    else:
        print("=== 系統自檢 ===")
        result = full_check()
    print(json.dumps(result, ensure_ascii=False, indent=2))

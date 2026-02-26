#!/usr/bin/env python3
"""
築未科技 — 本地獨立運行模組
漸進式脫離雲端 AI 訂閱，達到真正的本地運行

GitHub 上可用的開源替代方案整合：

┌─────────────────────────────────────────────────────────────────┐
│  雲端訂閱功能          │  本地替代方案              │  狀態     │
├─────────────────────────────────────────────────────────────────┤
│  ChatGPT / Claude      │  Ollama + Open WebUI       │  ✅ 已有  │
│  GPT-4 推理            │  Qwen3:8b / 70b            │  ✅ 已有  │
│  Copilot 寫程式        │  Aider + Qwen3-Coder       │  🔧 可裝  │
│  RAG 知識庫            │  ChromaDB + nomic-embed     │  ✅ 已有  │
│  多 Agent 協作         │  multi_agent.py v2          │  ✅ 已有  │
│  圖片生成              │  Forge + ComfyUI            │  ✅ 已有  │
│  視覺辨識              │  YOLOv8 + moondream         │  ✅ 已有  │
│  OCR 文字辨識          │  EasyOCR                    │  ✅ 已有  │
│  語音轉文字            │  Whisper.cpp                │  🔧 可裝  │
│  Fine-tuning 微調      │  Unsloth + LoRA             │  🔧 可裝  │
│  Prompt 自動優化       │  DSPy + Ollama              │  🔧 可裝  │
│  電腦自動操作          │  Open Interpreter           │  🔧 可裝  │
│  Embedding             │  nomic-embed-text           │  ✅ 已有  │
│  結構化輸出            │  guidance + instructor      │  ✅ 已有  │
└─────────────────────────────────────────────────────────────────┘

硬體：RTX 4060 Ti 8GB + 64GB RAM + i7-14700
"""

import os
import time
import json
import requests
from typing import Dict, List, Optional
from pathlib import Path

OLLAMA_BASE = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11460").rstrip("/")


# ═══════════════════════════════════════════
# 獨立性評估引擎
# ═══════════════════════════════════════════

# 你的系統需要的所有 AI 能力
CAPABILITIES = {
    # ── 已完成（本地運行中）──
    "chat": {
        "name": "對話 / 問答",
        "cloud": "ChatGPT $20/月, Claude $20/月",
        "local": "Ollama qwen3:8b",
        "status": "local",  # local / partial / cloud / available
        "monthly_saving": 40,
        "tools": ["ollama"],
    },
    "reasoning": {
        "name": "深度推理",
        "cloud": "GPT-4o $20/月, Claude Opus $20/月",
        "local": "Qwen3:8b (24 tok/s) 或 Qwen3:70b Q2 (3-5 tok/s)",
        "status": "local",
        "monthly_saving": 40,
        "tools": ["ollama"],
    },
    "code_generation": {
        "name": "程式碼生成",
        "cloud": "GitHub Copilot $10/月, Cursor $20/月",
        "local": "Qwen3:8b + CodeSim 模擬器",
        "status": "local",
        "monthly_saving": 30,
        "tools": ["ollama", "code_simulator"],
    },
    "rag": {
        "name": "知識庫 RAG",
        "cloud": "OpenAI Assistants API, Pinecone",
        "local": "ChromaDB + nomic-embed-text + rag_fusion",
        "status": "local",
        "monthly_saving": 30,
        "tools": ["chromadb", "nomic-embed-text"],
    },
    "multi_agent": {
        "name": "多 Agent 協作",
        "cloud": "CrewAI Cloud, AutoGen Studio",
        "local": "multi_agent.py v2 (Tool/Task/Crew)",
        "status": "local",
        "monthly_saving": 0,
        "tools": ["multi_agent"],
    },
    "image_gen": {
        "name": "圖片生成",
        "cloud": "Midjourney $10/月, DALL-E API",
        "local": "Forge (SD WebUI) + ComfyUI",
        "status": "local",
        "monthly_saving": 10,
        "tools": ["forge", "comfyui"],
    },
    "vision": {
        "name": "視覺辨識",
        "cloud": "GPT-4V API, Google Vision API",
        "local": "YOLOv8 + moondream VLM + EasyOCR",
        "status": "local",
        "monthly_saving": 20,
        "tools": ["yolov8", "moondream", "easyocr"],
    },
    "embedding": {
        "name": "文字向量化",
        "cloud": "OpenAI Embeddings API $0.13/1M tokens",
        "local": "nomic-embed-text (768維, 本地免費)",
        "status": "local",
        "monthly_saving": 10,
        "tools": ["nomic-embed-text"],
    },
    "structured_output": {
        "name": "結構化輸出",
        "cloud": "OpenAI JSON Mode, Claude Tool Use",
        "local": "guidance + instructor + Ollama",
        "status": "local",
        "monthly_saving": 0,
        "tools": ["guidance", "instructor"],
    },

    # ── 可安裝（GitHub 上有成熟方案）──
    "code_assistant": {
        "name": "AI 寫程式助手（IDE 整合）",
        "cloud": "GitHub Copilot $10/月, Cursor $20/月, Windsurf",
        "local": "Aider + Ollama 或 Continue.dev + Ollama",
        "status": "available",
        "monthly_saving": 20,
        "tools": ["aider", "continue.dev"],
        "install": {
            "aider": "pip install aider-chat && aider --model ollama/qwen3:8b",
            "continue": "VS Code 安裝 Continue 擴展 → 設定 Ollama provider",
        },
        "github": "https://github.com/Aider-AI/aider",
    },
    "speech_to_text": {
        "name": "語音轉文字",
        "cloud": "OpenAI Whisper API $0.006/分鐘",
        "local": "faster-whisper 1.2.1 (已安裝, GPU 加速)",
        "status": "local",
        "monthly_saving": 5,
        "tools": ["faster-whisper"],
    },
    "fine_tuning": {
        "name": "模型微調（讓模型學你的領域）",
        "cloud": "OpenAI Fine-tuning $25/1M tokens",
        "local": "Unsloth + QLoRA (需 WSL/Docker，Windows Py3.14 不相容)",
        "status": "available",
        "monthly_saving": 25,
        "tools": ["unsloth"],
        "install": {
            "unsloth": "需在 WSL2 Ubuntu 或 Docker 中執行",
        },
        "github": "https://github.com/unslothai/unsloth",
        "note": "Windows Py3.14 triton/torchvision 衝突，需用 WSL2 或 Docker",
    },
    "prompt_optimization": {
        "name": "Prompt 自動優化",
        "cloud": "手動調 prompt / PromptLayer 訂閱",
        "local": "DSPy 3.1.3 + Ollama (已安裝, 自動找最佳 prompt)",
        "status": "local",
        "monthly_saving": 0,
        "tools": ["dspy"],
    },
    "computer_use": {
        "name": "電腦自動操作（Agent 控制電腦）",
        "cloud": "Claude Computer Use API",
        "local": "Open Interpreter + Ollama (離線模式)",
        "status": "available",
        "monthly_saving": 20,
        "tools": ["open-interpreter"],
        "install": {
            "open-interpreter": (
                "pip install open-interpreter\n"
                "interpreter.offline = True\n"
                "interpreter.llm.model = 'ollama/qwen3:8b'\n"
                "interpreter.llm.api_base = 'http://localhost:11460'"
            ),
        },
        "github": "https://github.com/openinterpreter/open-interpreter",
    },
    "text_to_speech": {
        "name": "文字轉語音",
        "cloud": "ElevenLabs $5/月, OpenAI TTS API",
        "local": "Coqui TTS / Piper TTS (離線, 多語言)",
        "status": "available",
        "monthly_saving": 5,
        "tools": ["piper-tts"],
        "install": {
            "piper": "pip install piper-tts && 下載中文語音模型",
        },
        "github": "https://github.com/rhasspy/piper",
    },
}


def assess_independence() -> Dict:
    """
    評估目前的本地獨立程度

    Returns:
        {"score": int, "local_count": int, "total": int,
         "monthly_saving": float, "capabilities": dict,
         "next_steps": list}
    """
    local_count = 0
    available_count = 0
    cloud_count = 0
    total_saving = 0
    potential_saving = 0
    next_steps = []

    for key, cap in CAPABILITIES.items():
        if cap["status"] == "local":
            local_count += 1
            total_saving += cap["monthly_saving"]
        elif cap["status"] == "available":
            available_count += 1
            potential_saving += cap["monthly_saving"]
            if cap.get("github"):
                next_steps.append({
                    "capability": cap["name"],
                    "tool": list(cap.get("install", {}).keys())[0] if cap.get("install") else "",
                    "github": cap.get("github", ""),
                    "saving": cap["monthly_saving"],
                    "note": cap.get("note", ""),
                })
        else:
            cloud_count += 1

    total = len(CAPABILITIES)
    score = int(local_count / total * 100)

    # 排序：省最多錢的優先
    next_steps.sort(key=lambda x: x["saving"], reverse=True)

    return {
        "score": score,
        "local_count": local_count,
        "available_count": available_count,
        "cloud_count": cloud_count,
        "total": total,
        "monthly_saving_current": total_saving,
        "monthly_saving_potential": potential_saving,
        "monthly_saving_total": total_saving + potential_saving,
        "next_steps": next_steps,
    }


def check_ollama_models() -> Dict:
    """檢查 Ollama 本地模型狀態"""
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        if r.status_code == 200:
            models = r.json().get("models", [])
            total_size = sum(m.get("size", 0) for m in models)
            names = [m["name"] for m in models]

            # 檢查關鍵模型
            has_chat = any("qwen3" in n or "zhewei" in n for n in names)
            has_embed = any("nomic" in n or "embed" in n for n in names)
            has_vision = any("moondream" in n or "llava" in n for n in names)
            has_coder = any("coder" in n for n in names)

            return {
                "ok": True,
                "models": names,
                "count": len(models),
                "total_gb": round(total_size / 1e9, 1),
                "has_chat": has_chat,
                "has_embed": has_embed,
                "has_vision": has_vision,
                "has_coder": has_coder,
                "missing": [
                    m for m in ["qwen3-coder:latest"]
                    if not has_coder
                ],
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "unknown"}


def get_roadmap() -> Dict:
    """
    取得完整的脫離訂閱路線圖

    Returns:
        分階段的行動計畫
    """
    assessment = assess_independence()

    return {
        "current_score": assessment["score"],
        "phases": [
            {
                "phase": 1,
                "name": "基礎本地化（已完成）",
                "status": "done",
                "items": [
                    "✅ Ollama 本地推理 (qwen3:8b, 24 tok/s)",
                    "✅ ChromaDB 知識庫 + nomic-embed-text",
                    "✅ Forge/ComfyUI 本地生圖",
                    "✅ YOLOv8 視覺辨識 + EasyOCR",
                    "✅ multi_agent v2 多 Agent 協作",
                    "✅ AI SOP 管線 (分類/快取/品質門檻)",
                ],
                "saving": "~NT$180/月（已省下）",
            },
            {
                "phase": 2,
                "name": "進階本地化（推薦安裝）",
                "status": "ready",
                "items": [
                    {
                        "name": "Aider — 本地 AI 寫程式（取代 Copilot/Cursor）",
                        "command": "pip install aider-chat",
                        "usage": "aider --model ollama_chat/qwen3:8b --ollama-base-url http://localhost:11460",
                        "github": "https://github.com/Aider-AI/aider",
                        "saving": "NT$600/月",
                        "priority": "HIGH",
                    },
                    {
                        "name": "Unsloth — 本地微調模型（讓 AI 學你的領域）",
                        "command": "pip install unsloth",
                        "usage": "用你的營建知識 JSONL 微調 qwen3:8b → 專屬營建 AI",
                        "github": "https://github.com/unslothai/unsloth",
                        "saving": "NT$750/月",
                        "priority": "HIGH",
                        "note": "RTX 4060 Ti 8GB 用 QLoRA 4-bit 可調 8B 模型",
                    },
                    {
                        "name": "DSPy — 自動優化 Prompt（不用手調）",
                        "command": "pip install dspy",
                        "usage": "自動找到最佳 prompt，品質提升 20-40%",
                        "github": "https://github.com/stanfordnlp/dspy",
                        "saving": "品質提升（間接省錢）",
                        "priority": "MEDIUM",
                    },
                    {
                        "name": "faster-whisper — 本地語音轉文字",
                        "command": "pip install faster-whisper",
                        "usage": "工地語音記錄 → 文字，完全離線",
                        "github": "https://github.com/SYSTRAN/faster-whisper",
                        "saving": "NT$150/月",
                        "priority": "MEDIUM",
                    },
                ],
                "saving": "額外 ~NT$1,500/月",
            },
            {
                "phase": 3,
                "name": "完全獨立（終極目標）",
                "status": "future",
                "items": [
                    {
                        "name": "Qwen3:70b Q2 — 本地跑 70B 大模型",
                        "command": "ollama pull qwen3:70b",
                        "usage": "64GB RAM 可跑，3-5 tok/s，品質接近 GPT-4",
                        "note": "下載約 26GB，首次載入 30-60 秒",
                        "priority": "HIGH",
                    },
                    {
                        "name": "Open Interpreter — AI 自動操作電腦",
                        "command": "pip install open-interpreter",
                        "usage": "用自然語言讓 AI 操作你的電腦",
                        "github": "https://github.com/openinterpreter/open-interpreter",
                        "priority": "MEDIUM",
                    },
                    {
                        "name": "Piper TTS — 本地文字轉語音",
                        "command": "pip install piper-tts",
                        "usage": "中文語音合成，完全離線",
                        "github": "https://github.com/rhasspy/piper",
                        "priority": "LOW",
                    },
                    {
                        "name": "持續微調 — 用 Unsloth 讓模型越來越聰明",
                        "usage": "每月收集對話資料 → 微調 → 模型持續進步",
                        "note": "這是真正脫離雲端的關鍵：模型會越用越好",
                        "priority": "ONGOING",
                    },
                ],
                "saving": "完全脫離所有訂閱",
            },
        ],
        "key_insight": (
            "關鍵洞察：真正脫離訂閱的核心不是「跑模型」（你已經做到了），"
            "而是「讓模型持續進步」。Unsloth 微調 + DSPy 自動優化 prompt "
            "= 你的本地 AI 會越來越聰明，不再需要依賴雲端更新。"
        ),
        "hardware_status": {
            "gpu": "RTX 4060 Ti 8GB — 可跑 ≤8B 全 GPU，14B 部分 GPU，70B 混合",
            "ram": "64GB DDR4 — 足夠跑 70B Q2 量化模型",
            "cpu": "i7-14700 20核28線程 — CPU offload 效能優秀",
            "verdict": "你的硬體已經足夠達到 95% 本地獨立",
        },
    }


def get_cloud_vs_local_comparison() -> List[Dict]:
    """
    雲端訂閱 vs 本地方案的詳細對比

    Returns:
        [{"service": str, "monthly_cost": float, "local_alternative": str,
          "quality_ratio": str, "status": str}]
    """
    return [
        {
            "service": "ChatGPT Plus",
            "monthly_cost": 620,  # NT$
            "local_alternative": "Ollama qwen3:8b (已安裝)",
            "quality_ratio": "85-90%",
            "status": "已替代",
            "note": "日常對話品質相當，複雜推理稍弱",
        },
        {
            "service": "Claude Pro",
            "monthly_cost": 620,
            "local_alternative": "Ollama qwen3:8b + multi_agent v2",
            "quality_ratio": "80-85%",
            "status": "已替代",
            "note": "長文分析用 multi_agent 多步驟補償",
        },
        {
            "service": "GitHub Copilot",
            "monthly_cost": 310,
            "local_alternative": "Aider + qwen3:8b 或 Continue.dev",
            "quality_ratio": "75-85%",
            "status": "可安裝",
            "note": "Qwen3-Coder 在 SWE-Bench 表現優秀",
        },
        {
            "service": "Cursor Pro",
            "monthly_cost": 620,
            "local_alternative": "Aider + qwen3:8b (終端) 或 Continue.dev (VS Code)",
            "quality_ratio": "70-80%",
            "status": "可安裝",
            "note": "複雜重構用 70B 模型補強",
        },
        {
            "service": "Midjourney",
            "monthly_cost": 310,
            "local_alternative": "Forge + NoobAI-XL (已安裝)",
            "quality_ratio": "80-90%",
            "status": "已替代",
            "note": "SDXL 品質接近，可自訂模型",
        },
        {
            "service": "OpenAI API (Embedding)",
            "monthly_cost": 150,
            "local_alternative": "nomic-embed-text (已安裝, 免費)",
            "quality_ratio": "90-95%",
            "status": "已替代",
            "note": "768維，品質接近 text-embedding-3-small",
        },
        {
            "service": "OpenAI API (GPT-4)",
            "monthly_cost": 1000,
            "local_alternative": "Qwen3:70b Q2 (可安裝, 免費)",
            "quality_ratio": "85-90%",
            "status": "可安裝",
            "note": "需 ollama pull qwen3:70b (~26GB)",
        },
        {
            "service": "OpenAI Fine-tuning",
            "monthly_cost": 750,
            "local_alternative": "Unsloth QLoRA (可安裝, 免費)",
            "quality_ratio": "90-95%",
            "status": "可安裝",
            "note": "8GB VRAM 可調 8B 模型，效果更好因為完全控制",
        },
    ]


def print_independence_report():
    """印出完整的獨立性報告"""
    assessment = assess_independence()
    roadmap = get_roadmap()

    print("=" * 60)
    print("  築未科技 — 本地 AI 獨立性報告")
    print("=" * 60)
    print()
    print(f"  獨立性分數: {assessment['score']}%")
    print(f"  本地運行: {assessment['local_count']}/{assessment['total']} 項能力")
    print(f"  可安裝:   {assessment['available_count']} 項")
    print(f"  已省下:   NT${assessment['monthly_saving_current']}/月")
    print(f"  潛在節省: NT${assessment['monthly_saving_potential']}/月")
    print(f"  完全獨立後: NT${assessment['monthly_saving_total']}/月")
    print()

    for phase in roadmap["phases"]:
        status_icon = {"done": "✅", "ready": "🔧", "future": "🎯"}
        print(f"  {status_icon.get(phase['status'], '?')} Phase {phase['phase']}: {phase['name']}")
        print(f"     節省: {phase['saving']}")
        print()

    print(f"  💡 {roadmap['key_insight']}")
    print()


# ═══════════════════════════════════════════
# 全域便捷函數
# ═══════════════════════════════════════════

def independence_score() -> int:
    """取得獨立性分數 (0-100)"""
    return assess_independence()["score"]


def next_steps() -> List[Dict]:
    """取得下一步建議"""
    return assess_independence()["next_steps"]


if __name__ == "__main__":
    print_independence_report()

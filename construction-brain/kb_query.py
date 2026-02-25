# -*- coding: utf-8 -*-
"""
築未科技 Construction Brain
kb_query.py

功能：
  從施工知識庫（ChromaDB）做語意搜尋，
  結合 Ollama 本地模型，回答新案子人員的問題
  （RAG：Retrieval-Augmented Generation）

用法：
    # 互動問答模式
    python kb_query.py --interactive

    # 單次查詢
    python kb_query.py --question "鋼筋混凝土橋墩施工時養護需要幾天？"

    # 針對特定類別查詢
    python kb_query.py --question "混凝土澆置規範" --category 施工規範
"""

import argparse
import os
from pathlib import Path

import httpx

BASE_DIR = Path(os.environ.get("ZHEWEI_BASE", r"C:\ZheweiConstruction"))
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "zhewei-brain")
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120"))

KB_DIR = BASE_DIR / "db" / "kb_chroma"

RAG_SYSTEM_PROMPT = """你是「築未科技」的工地知識庫助理。

你的角色是協助工地主任、監造人員、新進工程師，
快速了解工程施工方法、規範要求、施工程序。

【回答原則】
1. 優先引用提供的「參考資料」段落，並標明出處（文件名稱）
2. 回答要具體、可操作，避免模糊敘述
3. 涉及安全的事項要特別強調
4. 找不到相關資料時，明確說「知識庫中未找到相關資料，建議查閱原始文件」
5. 回答語言：繁體中文，專業術語
6. 格式：條列式或表格，方便快速閱讀

【禁止】
- 不得捏造工程數據（如混凝土強度、養護天數等）
- 未在知識庫中找到依據時，不得臆測規範要求"""


def _get_collection():
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        client = chromadb.PersistentClient(path=str(KB_DIR))
        ef = embedding_functions.DefaultEmbeddingFunction()
        return client.get_or_create_collection(
            name="construction_kb",
            embedding_function=ef,
        )
    except ImportError:
        print("[kb_query] [WARN] chromadb 未安裝：pip install chromadb")
        return None
    except Exception as e:
        print(f"[kb_query] [WARN] ChromaDB 連線失敗：{e}")
        return None


def retrieve(question: str, top_k: int = 5, category: str = None) -> list[dict]:
    """
    從向量索引搜尋最相關的段落

    Returns:
        list of {text, filename, category, score}
    """
    collection = _get_collection()
    if collection is None:
        return []

    where = {"category": category} if category else None
    try:
        results = collection.query(
            query_texts=[question],
            n_results=min(top_k, collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        print(f"[kb_query] 搜尋失敗：{e}")
        return []

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "filename": meta.get("filename", ""),
            "category": meta.get("category", ""),
            "score": round(1 - dist, 3),
        })
    return chunks


def _build_context(chunks: list[dict]) -> str:
    if not chunks:
        return "（知識庫中未找到相關段落）"
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"【參考資料 {i}】來源：{chunk['filename']}（{chunk['category']}）\n"
            f"{chunk['text']}"
        )
    return "\n\n".join(parts)


def answer(question: str, top_k: int = 5, category: str = None) -> str:
    """
    RAG 問答：搜尋 + Ollama 生成回答

    Args:
        question: 問題文字
        top_k: 取最相關的 K 個段落
        category: 限定類別（選填）

    Returns:
        AI 回答文字
    """
    print(f"[kb_query] 搜尋：「{question[:50]}」")
    chunks = retrieve(question, top_k=top_k, category=category)

    if chunks:
        print(f"[kb_query] 找到 {len(chunks)} 個相關段落")
        for i, chunk in enumerate(chunks, 1):
            print(f"  [{i}] {chunk['filename']} (相似度: {chunk['score']:.3f})")
    else:
        print("[kb_query] [WARN] 知識庫無相關資料，以模型本身知識回答")

    context = _build_context(chunks)
    user_prompt = f"""以下是從知識庫找到的相關參考資料：

{context}

---

請根據上述參考資料，回答以下問題：
{question}"""

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.2, "num_ctx": 8192},
    }

    try:
        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            r = client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
    except Exception as e:
        return f"[kb_query] [ERR] Ollama 呼叫失敗：{e}"


def interactive_mode(category: str = None):
    """互動問答模式"""
    print(f"\n{'='*55}")
    print(f"  築未科技 施工知識庫 問答模式")
    print(f"  知識庫位置：{KB_DIR}")
    if category:
        print(f"  搜尋類別：{category}")
    print(f"  輸入 'exit' 或 'quit' 離開")
    print(f"{'='*55}\n")

    collection = _get_collection()
    if collection:
        print(f"  知識庫段落數：{collection.count():,}\n")
    else:
        print("  [WARN] 知識庫尚未建立，請先執行 kb_ingest.py\n")

    while True:
        try:
            question = input("[SEARCH] 你的問題：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再見！")
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit", "離開", "退出"):
            print("再見！")
            break

        print()
        resp = answer(question, category=category)
        print(f"\n{'─'*55}")
        print(resp)
        print(f"{'─'*55}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="築未科技 — 施工知識庫問答（RAG）")
    parser.add_argument("--question", help="單次查詢問題")
    parser.add_argument("--category", default=None,
                        choices=["施工法", "分項計畫書", "施工規範", "監造計畫", "設計圖說", "契約", "標準圖", "其他"],
                        help="限定搜尋類別")
    parser.add_argument("--interactive", action="store_true", help="互動問答模式")
    parser.add_argument("--top_k", type=int, default=5, help="取最相關的 K 個段落")
    args = parser.parse_args()

    if args.interactive or not args.question:
        interactive_mode(category=args.category)
    else:
        resp = answer(args.question, top_k=args.top_k, category=args.category)
        print(f"\n{'─'*55}")
        print(resp)
        print(f"{'─'*55}")

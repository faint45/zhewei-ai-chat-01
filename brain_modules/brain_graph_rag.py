# -*- coding: utf-8 -*-
"""
築未科技大腦 — Graph RAG（圖表理解）
PDF → 圖片 → VLM (Gemini) 描述 → 存入向量庫
查詢時回傳文字 + 圖元索引（含 image_path、page）
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

try:
    from brain_data_config import CHROMA_PATH as _CHROMA_PATH
    from brain_data_config import BRAIN_DATA_DIR
except ImportError:
    _CHROMA_PATH = Path("D:/zhewei_brain_data/brain_chroma_db")
    BRAIN_DATA_DIR = Path("D:/zhewei_brain_data")

GRAPH_RAG_COLLECTION = "brain_graph_rag"
GRAPH_RAG_IMAGES_DIR = BRAIN_DATA_DIR / "graph_rag_images"
_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

_chroma_client = None
_sentence_transformer = None
_gemini_available = False


def _ensure_chroma():
    global _chroma_client, _sentence_transformer
    if _chroma_client is not None:
        return _chroma_client is not None
    try:
        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer
        _chroma_client = chromadb.PersistentClient(
            path=str(_CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False),
        )
        _sentence_transformer = SentenceTransformer(_EMBEDDING_MODEL, device="cpu")
        return True
    except ImportError:
        return False


def _ensure_gemini():
    global _gemini_available
    if _gemini_available:
        return True
    try:
        import google.generativeai as genai
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            return False
        genai.configure(api_key=key)
        _gemini_available = True
        return True
    except Exception:
        return False


def _pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 150) -> list[Path]:
    """將 PDF 每頁轉成 PNG 圖片。"""
    images: list[Path] = []
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = pdf_path.stem
        for i in range(len(doc)):
            page = doc[i]
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
            img_path = output_dir / f"{stem}_p{i + 1}.png"
            pix.save(str(img_path))
            images.append(img_path)
        doc.close()
    except ImportError:
        try:
            from pdf2image import convert_from_path
            output_dir.mkdir(parents=True, exist_ok=True)
            stem = pdf_path.stem
            pages = convert_from_path(str(pdf_path), dpi=dpi)
            for i, img in enumerate(pages):
                img_path = output_dir / f"{stem}_p{i + 1}.png"
                img.save(str(img_path), "PNG")
                images.append(img_path)
        except ImportError:
            pass
    return images


def _vlm_describe_image(image_path: Path, source_name: str, page_num: int) -> str:
    """使用 Gemini 描述圖片內容（含圖表、施工大樣、配筋等）。"""
    if not _ensure_gemini():
        return ""
    try:
        import google.generativeai as genai
        from PIL import Image

        model = genai.GenerativeModel("gemini-1.5-flash")
        img = Image.open(str(image_path)).convert("RGB")
        prompt = (
            "請詳細描述這張圖片的內容。若為營建/施工圖、配筋圖、大樣圖，請標註：\n"
            "- 圖例、標註、尺寸\n"
            "- 鋼筋搭接長度、間距、數量\n"
            "- 連續壁、樑柱、板等構件\n"
            "- 任何可辨識的數字與單位\n"
            "輸出純文字，方便後續搜尋。"
        )
        response = model.generate_content([prompt, img])
        if response and response.text:
            return f"[{source_name} 第{page_num}頁] {response.text.strip()}"
    except Exception:
        pass
    return ""


def ingest_pdf(
    pdf_path: Path,
    source_name: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> dict:
    """
    將 PDF 匯入 Graph RAG：轉圖 → VLM 描述 → 存入 Chroma。
    回傳 {"ok": bool, "pages": int, "errors": [...]}
    """
    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        return {"ok": False, "pages": 0, "errors": ["PDF 不存在"]}
    source_name = source_name or pdf_path.stem
    out_dir = output_dir or (GRAPH_RAG_IMAGES_DIR / pdf_path.stem)
    out_dir.mkdir(parents=True, exist_ok=True)

    images = _pdf_to_images(pdf_path, out_dir)
    if not images:
        return {"ok": False, "pages": 0, "errors": ["PDF 轉圖失敗，請安裝 PyMuPDF 或 pdf2image"]}

    if not _ensure_chroma():
        return {"ok": False, "pages": 0, "errors": ["Chroma 未就緒"]}

    import uuid
    coll = _chroma_client.get_or_create_collection(
        GRAPH_RAG_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    errors: list[str] = []
    count = 0

    for i, img_path in enumerate(images):
        try:
            desc = _vlm_describe_image(img_path, source_name, i + 1)
            if not desc:
                errors.append(f"頁{i+1} VLM 描述失敗")
                continue
            doc_id = f"graph_{pdf_path.stem}_{i + 1}"
            emb = _sentence_transformer.encode([desc[:4000]], normalize_embeddings=True)
            coll.upsert(
                ids=[doc_id],
                embeddings=emb.tolist(),
                documents=[desc[:4000]],
                metadatas=[
                    {
                        "source": source_name,
                        "page": i + 1,
                        "image_path": str(img_path),
                        "pdf_path": str(pdf_path),
                    }
                ],
            )
            count += 1
        except Exception as e:
            errors.append(f"頁{i+1}: {e}")

    return {"ok": count > 0, "pages": count, "errors": errors}


def search_graph_rag(query: str, limit: int = 5, include_images: bool = True) -> list[dict]:
    """
    搜尋 Graph RAG，回傳含文字與圖元索引的結果。
    每筆：{"text": str, "source": str, "page": int, "image_path": str}
    """
    if not _ensure_chroma():
        return []
    try:
        coll = _chroma_client.get_or_create_collection(
            GRAPH_RAG_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        q_emb = _sentence_transformer.encode([query], normalize_embeddings=True)
        results = coll.query(
            query_embeddings=q_emb.tolist(),
            n_results=limit,
            include=["documents", "metadatas"],
        )
        if not results or not results.get("documents") or not results["documents"][0]:
            return []
        docs = results["documents"][0]
        metas = results.get("metadatas") or [[]]
        out: list[dict] = []
        for j, (doc, meta_list) in enumerate(zip(docs, metas[0] if metas else [])):
            meta = meta_list if isinstance(meta_list, dict) else {}
            out.append({
                "text": doc or "",
                "source": meta.get("source", ""),
                "page": int(meta.get("page", 0) or 0),
                "image_path": meta.get("image_path", "") if include_images else "",
            })
        return out
    except Exception:
        return []


def search_graph_rag_str(query: str, limit: int = 5) -> str:
    """回傳字串格式，供 Agent 使用。"""
    hits = search_graph_rag(query, limit=limit)
    if not hits:
        return ""
    lines = ["【Graph RAG 圖表知識】"]
    for h in hits:
        lines.append(f"\n--- {h['source']} 第{h['page']}頁 ---\n{h['text']}")
        if h.get("image_path"):
            lines.append(f"\n（圖檔：{h['image_path']}）")
    return "\n".join(lines)


def is_available() -> bool:
    return _ensure_chroma() and _ensure_gemini()

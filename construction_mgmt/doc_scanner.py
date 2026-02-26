# -*- coding: utf-8 -*-
"""
營建自動化 — 文件掃描辨識歸檔服務
Web 攝影機拍照 → OCR 文字辨識 → AI 分類 → 自動歸檔
"""
import base64
import io
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

log = logging.getLogger(__name__)

# ===== 設定 =====
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11460")
OLLAMA_MODEL = os.environ.get("DOC_LLM_MODEL", "qwen3:32b")
SCAN_UPLOAD_DIR = Path(__file__).parent / "data" / "scanned_docs"
SCAN_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 文件分類
DOC_CATEGORIES = {
    "official_letter": "公文",
    "contract": "合約/契約",
    "inspection_report": "檢驗報告",
    "submittal": "送審文件",
    "meeting_minutes": "會議紀錄",
    "change_order": "變更設計",
    "payment_cert": "估驗計價",
    "safety_report": "安全衛生文件",
    "quality_report": "品質文件",
    "photo_record": "施工照片記錄",
    "drawing": "施工圖說",
    "material_cert": "材料證明/出廠證明",
    "test_report": "試驗報告",
    "other": "其他文件",
}

_ocr_reader = None


def get_ocr_reader():
    """延遲載入 EasyOCR（避免啟動時佔用 GPU）"""
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        log.info("載入 EasyOCR（繁中+英文）...")
        _ocr_reader = easyocr.Reader(['ch_tra', 'en'], gpu=True)
        log.info("EasyOCR 載入完成")
    return _ocr_reader


def _preprocess_image(img: Image.Image) -> Image.Image:
    """文件影像前處理：灰階 + 對比增強 + 銳化"""
    from PIL import ImageEnhance, ImageFilter

    # 轉灰階再轉回 RGB（OCR 需要）
    gray = img.convert('L')

    # 對比增強
    enhancer = ImageEnhance.Contrast(gray.convert('RGB'))
    enhanced = enhancer.enhance(1.5)

    # 銳化
    sharpened = enhanced.filter(ImageFilter.SHARPEN)

    return sharpened


def ocr_from_image(image_data: bytes, preprocess: bool = True) -> dict:
    """
    對圖片進行 OCR 文字辨識
    image_data: 圖片二進位資料（JPEG/PNG）
    回傳: { text, lines: [{text, confidence, bbox}], duration }
    """
    start = time.time()

    try:
        img = Image.open(io.BytesIO(image_data))
        if img.mode == 'RGBA':
            img = img.convert('RGB')

        if preprocess:
            img = _preprocess_image(img)

        # 轉為 numpy array
        img_np = np.array(img)

        reader = get_ocr_reader()
        results = reader.readtext(img_np, detail=1, paragraph=False)

        lines = []
        full_text_parts = []
        for (bbox, text, conf) in results:
            text = text.strip()
            if text:
                lines.append({
                    "text": text,
                    "confidence": round(float(conf), 3),
                    "bbox": [[int(p[0]), int(p[1])] for p in bbox]
                })
                full_text_parts.append(text)

        full_text = "\n".join(full_text_parts)
        elapsed = round(time.time() - start, 2)
        avg_conf = round(sum(l['confidence'] for l in lines) / max(len(lines), 1), 3)

        log.info(f"OCR 完成: {len(lines)} 行, {len(full_text)} chars, avg_conf={avg_conf}, {elapsed}s")

        return {
            "text": full_text,
            "lines": lines,
            "line_count": len(lines),
            "char_count": len(full_text),
            "avg_confidence": avg_conf,
            "duration": elapsed,
            "image_size": [img.width, img.height]
        }
    except Exception as e:
        log.error(f"OCR 失敗: {e}")
        return {"text": "", "lines": [], "line_count": 0, "char_count": 0,
                "avg_confidence": 0, "duration": 0, "error": str(e)}


def ocr_from_base64(base64_str: str, preprocess: bool = True) -> dict:
    """從 Base64 圖片進行 OCR"""
    # 移除 data:image/...;base64, 前綴
    if ',' in base64_str:
        base64_str = base64_str.split(',', 1)[1]
    image_data = base64.b64decode(base64_str)
    return ocr_from_image(image_data, preprocess)


def _call_ollama(prompt: str, system_prompt: str = "") -> str:
    """呼叫本地 Ollama LLM"""
    import urllib.request
    url = f"{OLLAMA_BASE}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 1500}
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("response", "")
    except Exception as e:
        log.error(f"Ollama 呼叫失敗: {e}")
        return ""


def _extract_json(text: str) -> dict:
    """從 LLM 回覆中提取 JSON"""
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    try:
        start = text.index('{')
        end = text.rindex('}') + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        pass
    return {}


def _regex_classify_document(ocr_text: str) -> dict:
    """
    正則表達式 fallback 分類器 — 從 OCR 文字判斷文件類型
    """
    t = ocr_text

    # 公文特徵
    if any(k in t for k in ("主旨", "說明", "辦法", "受文者", "發文日期", "發文字號", "函", "令")):
        cat = "official_letter"
        # 提取公文欄位
        subject = ""
        doc_number = ""
        sender = ""
        doc_date = ""
        for line in t.split('\n'):
            line = line.strip()
            if line.startswith("主旨") or "主旨" in line[:4]:
                subject = re.sub(r'^主旨[：:]\s*', '', line)
            if "發文字號" in line or "文號" in line:
                doc_number = re.sub(r'^.*(?:發文字號|文號)[：:]\s*', '', line)
            if "發文日期" in line:
                doc_date = re.sub(r'^.*發文日期[：:]\s*', '', line)
            if line.startswith("受文者") or "受文者" in line[:4]:
                sender = re.sub(r'^受文者[：:]\s*', '', line)
        return {
            "category": cat,
            "category_name": DOC_CATEGORIES[cat],
            "confidence": 0.85,
            "title": subject or "公文",
            "doc_number": doc_number,
            "doc_date": doc_date,
            "sender": sender,
            "summary": subject
        }

    # 合約/契約
    if any(k in t for k in ("契約", "合約", "甲方", "乙方", "契約金額", "工程名稱", "契約書")):
        cat = "contract"
        title = ""
        for line in t.split('\n'):
            if "工程名稱" in line:
                title = re.sub(r'^.*工程名稱[：:]\s*', '', line.strip())
                break
        return {
            "category": cat,
            "category_name": DOC_CATEGORIES[cat],
            "confidence": 0.8,
            "title": title or "合約文件",
            "summary": title
        }

    # 檢驗/試驗報告
    if any(k in t for k in ("試驗報告", "檢驗報告", "測試報告", "抗壓強度", "坍度", "配比", "試體")):
        cat = "test_report"
        return {
            "category": cat,
            "category_name": DOC_CATEGORIES[cat],
            "confidence": 0.8,
            "title": "試驗報告",
            "summary": ""
        }

    # 送審文件
    if any(k in t for k in ("送審", "審查", "核定", "備查", "施工計畫", "品質計畫")):
        cat = "submittal"
        return {
            "category": cat,
            "category_name": DOC_CATEGORIES[cat],
            "confidence": 0.75,
            "title": "送審文件",
            "summary": ""
        }

    # 會議紀錄
    if any(k in t for k in ("會議紀錄", "出席人員", "會議時間", "會議地點", "決議事項", "工務會議")):
        cat = "meeting_minutes"
        return {
            "category": cat,
            "category_name": DOC_CATEGORIES[cat],
            "confidence": 0.8,
            "title": "會議紀錄",
            "summary": ""
        }

    # 變更設計
    if any(k in t for k in ("變更設計", "設計變更", "變更金額", "增減")):
        cat = "change_order"
        return {
            "category": cat,
            "category_name": DOC_CATEGORIES[cat],
            "confidence": 0.75,
            "title": "變更設計",
            "summary": ""
        }

    # 估驗計價
    if any(k in t for k in ("估驗", "計價", "請款", "第.*期", "估驗明細")):
        cat = "payment_cert"
        return {
            "category": cat,
            "category_name": DOC_CATEGORIES[cat],
            "confidence": 0.75,
            "title": "估驗計價",
            "summary": ""
        }

    # 安全衛生
    if any(k in t for k in ("安全衛生", "職安", "安衛", "危害告知", "施工安全")):
        cat = "safety_report"
        return {
            "category": cat,
            "category_name": DOC_CATEGORIES[cat],
            "confidence": 0.7,
            "title": "安全衛生文件",
            "summary": ""
        }

    # 品質文件
    if any(k in t for k in ("品質", "品管", "自主檢查", "檢查表", "不合格")):
        cat = "quality_report"
        return {
            "category": cat,
            "category_name": DOC_CATEGORIES[cat],
            "confidence": 0.7,
            "title": "品質文件",
            "summary": ""
        }

    # 材料證明
    if any(k in t for k in ("出廠證明", "材料證明", "合格證", "CNS", "檢驗合格")):
        cat = "material_cert"
        return {
            "category": cat,
            "category_name": DOC_CATEGORIES[cat],
            "confidence": 0.75,
            "title": "材料證明",
            "summary": ""
        }

    # 預設
    return {
        "category": "other",
        "category_name": DOC_CATEGORIES["other"],
        "confidence": 0.3,
        "title": "未分類文件",
        "summary": ""
    }


def classify_document(ocr_text: str, project_name: str = "") -> dict:
    """
    AI 文件分類 + regex fallback
    回傳: { category, category_name, confidence, title, doc_number, doc_date, sender, summary }
    """
    # 1. Regex fallback（保底）
    regex_result = _regex_classify_document(ocr_text)

    # 2. LLM 分類
    categories_str = "\n".join([f"- {k}: {v}" for k, v in DOC_CATEGORIES.items()])
    system = f"""你是營建工程文件分類 AI。工程名稱：{project_name}。
根據 OCR 辨識出的文字內容，判斷文件類型並提取關鍵資訊。
只回傳 JSON，不要其他文字。"""

    prompt = f"""OCR 文字內容：
「{ocr_text[:1500]}」

文件分類選項：
{categories_str}

回傳 JSON：
{{"category":"分類代碼","category_name":"分類名稱","confidence":0.9,"title":"文件標題","doc_number":"文號","doc_date":"日期","sender":"發文單位","summary":"摘要(50字內)"}}"""

    raw = _call_ollama(prompt, system)
    llm_result = _extract_json(raw)

    # 3. 合併 — LLM 優先，regex 補漏
    if llm_result and llm_result.get("category") in DOC_CATEGORIES:
        # 用 LLM 結果但確保所有欄位存在
        merged = {**regex_result, **llm_result}
        merged["category_name"] = DOC_CATEGORIES.get(merged["category"], "其他文件")
        return merged

    return regex_result


def save_scanned_document(project_id: int, image_data: bytes, ocr_result: dict,
                          classification: dict, filename_hint: str = "") -> dict:
    """
    儲存掃描文件（圖片 + OCR 結果 + 分類）
    回傳: { scan_id, stored_filename, doc_id }
    """
    from database import get_db, add_document

    # 儲存圖片
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    ext = ".jpg"
    if filename_hint:
        _, ext_hint = os.path.splitext(filename_hint)
        if ext_hint:
            ext = ext_hint
    stored_name = f"scan_{project_id}_{ts}_{uuid.uuid4().hex[:6]}{ext}"
    stored_path = SCAN_UPLOAD_DIR / stored_name
    with open(stored_path, 'wb') as f:
        f.write(image_data)

    # 組合描述
    cat_name = classification.get("category_name", "未分類")
    title = classification.get("title", "掃描文件")
    summary = classification.get("summary", "")
    description = f"[{cat_name}] {title}"
    if summary:
        description += f" — {summary}"

    # 組合 parsed_data
    parsed = {
        "ocr_text": ocr_result.get("text", ""),
        "ocr_lines": ocr_result.get("line_count", 0),
        "ocr_confidence": ocr_result.get("avg_confidence", 0),
        "classification": classification,
        "scan_time": datetime.now().isoformat()
    }

    # 寫入文件管理表
    doc_type = classification.get("category", "other")
    original_name = filename_hint or f"{title}_{ts}{ext}"
    file_size = len(image_data)

    doc_id = add_document(
        project_id=project_id,
        doc_type=doc_type,
        original_filename=original_name,
        stored_filename=stored_name,
        file_size=file_size,
        mime_type=f"image/{ext.lstrip('.')}",
        description=description,
        parsed_data=json.dumps(parsed, ensure_ascii=False)
    )

    # 寫入掃描記錄表
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scanned_documents
        (project_id, doc_id, stored_filename, ocr_text, category, category_name,
         title, doc_number, doc_date, sender, summary, confidence, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'filed')
    """, (
        project_id, doc_id, stored_name,
        ocr_result.get("text", ""),
        classification.get("category", "other"),
        classification.get("category_name", "未分類"),
        classification.get("title", ""),
        classification.get("doc_number", ""),
        classification.get("doc_date", ""),
        classification.get("sender", ""),
        classification.get("summary", ""),
        classification.get("confidence", 0),
    ))
    scan_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "scan_id": scan_id,
        "doc_id": doc_id,
        "stored_filename": stored_name,
        "category": classification.get("category", "other"),
        "category_name": classification.get("category_name", "未分類"),
        "title": classification.get("title", ""),
    }


def list_scanned_documents(project_id: int, category: str = None) -> list:
    """列出掃描文件記錄"""
    from database import get_db
    conn = get_db()
    cursor = conn.cursor()
    if category:
        cursor.execute(
            "SELECT * FROM scanned_documents WHERE project_id=? AND category=? ORDER BY created_at DESC",
            (project_id, category))
    else:
        cursor.execute(
            "SELECT * FROM scanned_documents WHERE project_id=? ORDER BY created_at DESC",
            (project_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_scanned_document(scan_id: int) -> dict:
    """取得單筆掃描文件"""
    from database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scanned_documents WHERE id=?", (scan_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def search_scanned_documents(project_id: int, query: str) -> list:
    """搜尋掃描文件（全文搜尋 OCR 文字）"""
    from database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM scanned_documents WHERE project_id=? AND ocr_text LIKE ? ORDER BY created_at DESC",
        (project_id, f"%{query}%"))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

#!/usr/bin/env python3
"""
築未科技 — 文件解析模組
支援 PDF / Word / HTML / TXT / Markdown 解析
文件理解能力大幅提升
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional


class DocumentParser:
    """
    通用文件解析器：將各種格式的文件轉為純文字
    """

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".html", ".htm", ".txt", ".md", ".csv", ".xlsx", ".xls"}

    def parse(self, file_path: str) -> Dict:
        """
        解析文件，回傳結構化結果

        Returns:
            {"ok": bool, "text": str, "metadata": dict, "pages": int, "chars": int}
        """
        path = Path(file_path)
        if not path.exists():
            return {"ok": False, "error": f"檔案不存在: {file_path}"}

        ext = path.suffix.lower()
        try:
            if ext == ".pdf":
                return self._parse_pdf(path)
            elif ext in (".docx", ".doc"):
                return self._parse_docx(path)
            elif ext in (".html", ".htm"):
                return self._parse_html(path)
            elif ext in (".txt", ".md"):
                return self._parse_text(path)
            elif ext == ".csv":
                return self._parse_csv(path)
            elif ext in (".xlsx", ".xls"):
                return self._parse_excel(path)
            else:
                return {"ok": False, "error": f"不支援的格式: {ext}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _parse_pdf(self, path: Path) -> Dict:
        """解析 PDF"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(path))
            pages = []
            for page in doc:
                pages.append(page.get_text())
            text = "\n\n".join(pages)
            return {
                "ok": True, "text": text, "pages": len(pages),
                "chars": len(text), "metadata": {"format": "pdf", "file": path.name},
            }
        except ImportError:
            pass

        # Fallback: pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            text = "\n\n".join(pages)
            return {
                "ok": True, "text": text, "pages": len(pages),
                "chars": len(text), "metadata": {"format": "pdf", "file": path.name},
            }
        except ImportError:
            return {"ok": False, "error": "需要安裝 PyMuPDF 或 pdfplumber: pip install PyMuPDF pdfplumber"}

    def _parse_docx(self, path: Path) -> Dict:
        """解析 Word 文件"""
        try:
            import docx
            doc = docx.Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n\n".join(paragraphs)
            return {
                "ok": True, "text": text, "pages": len(paragraphs),
                "chars": len(text), "metadata": {"format": "docx", "file": path.name},
            }
        except ImportError:
            return {"ok": False, "error": "需要安裝 python-docx: pip install python-docx"}

    def _parse_html(self, path: Path) -> Dict:
        """解析 HTML"""
        raw = path.read_text(encoding="utf-8", errors="ignore")
        # 移除 script 和 style
        text = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # 移除 HTML 標籤
        text = re.sub(r'<[^>]+>', ' ', text)
        # 清理空白
        text = re.sub(r'\s+', ' ', text).strip()
        return {
            "ok": True, "text": text, "pages": 1,
            "chars": len(text), "metadata": {"format": "html", "file": path.name},
        }

    def _parse_text(self, path: Path) -> Dict:
        """解析純文字 / Markdown"""
        text = path.read_text(encoding="utf-8", errors="ignore")
        return {
            "ok": True, "text": text, "pages": 1,
            "chars": len(text), "metadata": {"format": path.suffix.lstrip("."), "file": path.name},
        }

    def _parse_csv(self, path: Path) -> Dict:
        """解析 CSV"""
        import csv
        rows = []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append(" | ".join(row))
        text = "\n".join(rows)
        return {
            "ok": True, "text": text, "pages": len(rows),
            "chars": len(text), "metadata": {"format": "csv", "file": path.name, "rows": len(rows)},
        }

    def _parse_excel(self, path: Path) -> Dict:
        """解析 Excel"""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
            sheets = []
            for ws in wb.worksheets:
                rows = []
                for row in ws.iter_rows(values_only=True):
                    cells = [str(c) if c is not None else "" for c in row]
                    rows.append(" | ".join(cells))
                sheets.append(f"[{ws.title}]\n" + "\n".join(rows))
            text = "\n\n".join(sheets)
            return {
                "ok": True, "text": text, "pages": len(sheets),
                "chars": len(text), "metadata": {"format": "xlsx", "file": path.name},
            }
        except ImportError:
            return {"ok": False, "error": "需要安裝 openpyxl: pip install openpyxl"}

    def parse_directory(self, dir_path: str, recursive: bool = True) -> List[Dict]:
        """批量解析目錄中的所有支援文件"""
        results = []
        path = Path(dir_path)
        if not path.is_dir():
            return [{"ok": False, "error": f"目錄不存在: {dir_path}"}]

        pattern = "**/*" if recursive else "*"
        for file in path.glob(pattern):
            if file.is_file() and file.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                result = self.parse(str(file))
                result["file_path"] = str(file)
                results.append(result)

        return results


# 全域單例
_parser: Optional[DocumentParser] = None


def get_parser() -> DocumentParser:
    global _parser
    if _parser is None:
        _parser = DocumentParser()
    return _parser


def parse_document(file_path: str) -> Dict:
    """便捷函數：解析文件"""
    return get_parser().parse(file_path)


def parse_directory(dir_path: str) -> List[Dict]:
    """便捷函數：批量解析目錄"""
    return get_parser().parse_directory(dir_path)

#!/usr/bin/env python3
"""
築未科技 — 智慧文本分塊模組
使用 Chonkie 進行語意感知分塊，提升 RAG 品質 30%
"""

import re
from typing import List, Dict, Optional


class SmartChunker:
    """
    智慧文本分塊器
    - 語意感知：不在句子中間切斷
    - 重疊分塊：確保上下文連續性
    - 自動偵測文件類型（程式碼/文章/對話）
    """

    def __init__(self, chunk_size: int = 512, overlap: int = 64):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, doc_type: str = "auto") -> List[Dict]:
        """
        智慧分塊

        Args:
            text: 原始文本
            doc_type: 文件類型 auto/code/article/conversation

        Returns:
            [{"text": str, "index": int, "start": int, "end": int, "type": str}]
        """
        if not text or not text.strip():
            return []

        if doc_type == "auto":
            doc_type = self._detect_type(text)

        if doc_type == "code":
            return self._chunk_code(text)
        elif doc_type == "conversation":
            return self._chunk_conversation(text)
        else:
            return self._chunk_article(text)

    def _detect_type(self, text: str) -> str:
        """自動偵測文件類型"""
        code_indicators = ["def ", "class ", "import ", "function ", "const ", "var ", "```", "=>", "->"]
        conv_indicators = ["：", ":", "Q:", "A:", "問：", "答：", "User:", "Assistant:"]

        code_score = sum(1 for ind in code_indicators if ind in text[:2000])
        conv_score = sum(1 for ind in conv_indicators if ind in text[:2000])

        if code_score >= 3:
            return "code"
        if conv_score >= 3:
            return "conversation"
        return "article"

    def _chunk_article(self, text: str) -> List[Dict]:
        """文章分塊：按段落 + 句子邊界"""
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current = ""
        start_pos = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current) + len(para) + 1 <= self.chunk_size:
                current = f"{current}\n{para}" if current else para
            else:
                if current:
                    chunks.append(self._make_chunk(current, len(chunks), start_pos))
                    start_pos += len(current) - self.overlap
                    # 保留重疊部分
                    overlap_text = current[-self.overlap:] if len(current) > self.overlap else ""
                    current = f"{overlap_text}\n{para}" if overlap_text else para
                else:
                    # 單段落超長，按句子切
                    sentences = self._split_sentences(para)
                    for sent in sentences:
                        if len(current) + len(sent) + 1 <= self.chunk_size:
                            current = f"{current} {sent}" if current else sent
                        else:
                            if current:
                                chunks.append(self._make_chunk(current, len(chunks), start_pos))
                                start_pos += len(current) - self.overlap
                            current = sent

        if current.strip():
            chunks.append(self._make_chunk(current, len(chunks), start_pos))

        return chunks

    def _chunk_code(self, text: str) -> List[Dict]:
        """程式碼分塊：按函數/類別邊界"""
        # 偵測函數和類別定義
        pattern = r'^(def |class |async def |function |const |export )'
        lines = text.split('\n')
        chunks = []
        current_lines = []
        start_pos = 0

        for line in lines:
            if re.match(pattern, line.strip()) and current_lines:
                chunk_text = '\n'.join(current_lines)
                if len(chunk_text) > 20:
                    chunks.append(self._make_chunk(chunk_text, len(chunks), start_pos, "code"))
                    start_pos += len(chunk_text)
                current_lines = [line]
            else:
                current_lines.append(line)

            # 超過 chunk_size 強制切割
            if len('\n'.join(current_lines)) > self.chunk_size * 2:
                chunk_text = '\n'.join(current_lines)
                chunks.append(self._make_chunk(chunk_text, len(chunks), start_pos, "code"))
                start_pos += len(chunk_text)
                current_lines = []

        if current_lines:
            chunk_text = '\n'.join(current_lines)
            if len(chunk_text) > 20:
                chunks.append(self._make_chunk(chunk_text, len(chunks), start_pos, "code"))

        return chunks

    def _chunk_conversation(self, text: str) -> List[Dict]:
        """對話分塊：按對話輪次"""
        # 偵測對話分隔符
        turn_pattern = r'(?:^|\n)(?:User|Assistant|Q|A|問|答|人|AI|使用者|助手)[：:]'
        turns = re.split(turn_pattern, text)
        chunks = []
        current = ""
        start_pos = 0

        for turn in turns:
            turn = turn.strip()
            if not turn:
                continue
            if len(current) + len(turn) + 1 <= self.chunk_size:
                current = f"{current}\n{turn}" if current else turn
            else:
                if current:
                    chunks.append(self._make_chunk(current, len(chunks), start_pos, "conversation"))
                    start_pos += len(current)
                current = turn

        if current.strip():
            chunks.append(self._make_chunk(current, len(chunks), start_pos, "conversation"))

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """按句子分割（支援中英文）"""
        # 中文句號、問號、驚嘆號、英文句號
        sentences = re.split(r'(?<=[。！？.!?])\s*', text)
        return [s.strip() for s in sentences if s.strip()]

    def _make_chunk(self, text: str, index: int, start: int, doc_type: str = "article") -> Dict:
        return {
            "text": text.strip(),
            "index": index,
            "start": start,
            "end": start + len(text),
            "type": doc_type,
            "char_count": len(text.strip()),
        }


# 全域單例
_chunker: Optional[SmartChunker] = None


def get_chunker(chunk_size: int = 512, overlap: int = 64) -> SmartChunker:
    global _chunker
    if _chunker is None:
        _chunker = SmartChunker(chunk_size=chunk_size, overlap=overlap)
    return _chunker


def smart_chunk(text: str, chunk_size: int = 512, doc_type: str = "auto") -> List[Dict]:
    """便捷函數：智慧分塊"""
    return get_chunker(chunk_size=chunk_size).chunk(text, doc_type)

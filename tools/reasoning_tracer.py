"""
築未科技大腦 - AI 運算過程記錄與範本轉換
記錄重點邏輯與推演，輸出為可學習範本，供本地大腦內化
"""
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from brain_data_config import REASONING_LOG, BRAIN_DATA_DIR
from brain_knowledge import add

_lock = threading.Lock()
_buffer: list[dict] = []

# AI 回應中的推理區塊標記（供 extractor 辨識）
REASONING_BLOCK_START = "<!-- REASONING_RECORD -->"
REASONING_BLOCK_END = "<!-- /REASONING_RECORD -->"


def log_step(phase: str, content: str, tool: str = "") -> None:
    """記錄單一運算步驟（供內部 Python 流程呼叫）"""
    if not content or not content.strip():
        return
    entry = {
        "ts": datetime.now().isoformat(),
        "phase": phase,
        "content": content.strip()[:2000],
        "tool": tool,
    }
    with _lock:
        _buffer.append(entry)
        try:
            with open(REASONING_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


def clear_buffer() -> None:
    """清空記憶體緩衝（不影響 ndjson 紀錄）"""
    with _lock:
        _buffer.clear()


def export_to_template(user_query: str = "", steps: Optional[list[dict]] = None) -> str:
    """
    將運算步驟轉為「本地學習範本」格式。
    steps 若為 None 則使用 buffer。
    """
    steps = steps or list(_buffer)
    if not steps:
        return ""
    lines = ["【AI 運算過程範本】"]
    if user_query:
        lines.append(f"用戶需求: {user_query[:300]}")
    lines.append("")
    for i, s in enumerate(steps, 1):
        phase = s.get("phase", "")
        content = s.get("content", "")
        tool = s.get("tool", "")
        parts = [f"{i}. [{phase}]"]
        if tool:
            parts.append(f" 工具:{tool}")
        parts.append(f" {content[:500]}")
        lines.append("".join(parts))
    return "\n".join(lines)


def export_to_brain(user_query: str = "") -> bool:
    """將 buffer 轉為範本並寫入知識庫"""
    template = export_to_template(user_query)
    if not template or len(template.strip()) < 50:
        return False
    try:
        add(template, source="運算過程範本", metadata={"type": "reasoning_template"})
        clear_buffer()
        return True
    except Exception:
        return False


def extract_reasoning_from_text(text: str) -> list[dict]:
    """
    從 AI 回應文字中擷取 <!-- REASONING_RECORD --> 區塊內容。
    回傳結構化步驟列表。
    """
    import re
    steps = []
    pattern = rf"{re.escape(REASONING_BLOCK_START)}\s*([\s\S]*?)\s*{re.escape(REASONING_BLOCK_END)}"
    matches = re.findall(pattern, text)
    for raw in matches:
        block = raw.strip()
        if len(block) < 15:
            continue
        for line in block.split("\n"):
            line = line.strip()
            if not line or len(line) < 10:
                continue
            # 匹配: 1. [階段]: 內容 或 [階段]: 內容 或 - 內容
            m = re.match(r"^(?:\d+[\.\)]\s*)?\[([^\]]+)\]\s*[：:]\s*(.+)$", line)
            if m:
                phase, content = m.group(1).strip(), m.group(2).strip()
            else:
                m2 = re.match(r"^(?:\d+[\.\)]\s*)?(.+?)[：:]\s*(.+)$", line)
                if m2 and len(m2.group(2)) > 20:
                    phase, content = m2.group(1).strip(), m2.group(2).strip()
                else:
                    phase, content = "推演", line
            if len(content) > 15:
                steps.append({"phase": phase[:50], "content": content[:800], "tool": ""})
        if not steps and len(block) > 40:
            steps.append({"phase": "推演", "content": block[:1000], "tool": ""})
    return steps


def learn_from_reasoning_text(text: str, user_query: str = "") -> bool:
    """
    從包含 REASONING_RECORD 區塊的文字擷取推理，轉為範本寫入知識庫。
    """
    steps = extract_reasoning_from_text(text)
    if not steps:
        return False
    template = export_to_template(user_query, steps)
    if len(template.strip()) < 50:
        return False
    try:
        add(template, source="運算過程範本", metadata={"type": "reasoning_template"})
        return True
    except Exception:
        return False

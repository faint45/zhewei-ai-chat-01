"""
築未科技大腦 - 自我學習強化
從對話、Agent 執行結果、開發成功/失敗自動萃取知識並寫入知識庫
"""
import re
import threading
from datetime import datetime
from pathlib import Path

from brain_data_config import SELF_LEARN_LOG
from brain_knowledge import add

SELF_LEARN_FILE = SELF_LEARN_LOG
_lock = threading.Lock()


def _log_entry(kind: str, data: dict):
    """Append-only 紀錄學習事件"""
    import json
    with _lock:
        try:
            entry = {"ts": datetime.now().isoformat(), "kind": kind, **data}
            with open(SELF_LEARN_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


def learn_from_qa(question: str, answer: str, min_len: int = 30) -> bool:
    """
    從問答對萃取值錢知識並寫入知識庫。
    """
    if not question or not answer or len(question.strip()) < 5 or len(answer.strip()) < min_len:
        return False
    q = question.strip()[:500]
    a = answer.strip()[:3000]
    # 排除純廢話
    skip = ["連線失敗", "無回覆", "請輸入", "錯誤", "失敗", "我不確定", "我無法"]
    if any(s in a for s in skip):
        return False
    try:
        text = f"Q: {q}\nA: {a}"
        add(text, source="問答學習", metadata={"type": "qa"})
        _log_entry("qa", {"q_len": len(q), "a_len": len(a)})
        return True
    except Exception:
        return False


def learn_from_agent_success(tool_name: str, args_summary: str, result_preview: str) -> bool:
    """從 Agent 成功執行記錄可重用模式。結構化紀錄供後續改進。"""
    if not tool_name:
        return False
    result_preview = (result_preview or "")[:1500].strip()
    if len(result_preview) < 20:
        return False
    try:
        text = f"【Agent 成功】工具: {tool_name}\n參數摘要: {args_summary}\n結果: {result_preview}"
        add(text, source="Agent 執行", metadata={"type": "agent_success", "tool": tool_name})
        _log_entry("agent_success", {"tool": tool_name, "args_len": len(str(args_summary)), "result_len": len(result_preview)})
        return True
    except Exception:
        return False


def learn_from_agent_failure(tool_name: str, args_summary: str, error_preview: str) -> bool:
    """Agent 工具失敗時記錄，供後續避免相同錯誤。"""
    if not tool_name or not error_preview or len(error_preview.strip()) < 10:
        return False
    try:
        err = error_preview.strip()[:500]
        text = f"【Agent 失敗模式】工具: {tool_name}\n參數: {args_summary}\n錯誤: {err}"
        add(text, source="Agent 失敗", metadata={"type": "agent_failure", "tool": tool_name})
        _log_entry("agent_failure", {"tool": tool_name, "err_len": len(err)})
        return True
    except Exception:
        return False


def learn_from_dev_success(demand: str, code_snippet: str) -> bool:
    """
    開發：成功執行後，記錄任務與解法。
    """
    if not demand or not code_snippet or len(code_snippet) < 20:
        return False
    try:
        snippet = code_snippet.strip()[:2000]
        text = f"【開發成功】任務: {demand}\n代碼:\n{snippet}"
        add(text, source="開發執行", metadata={"type": "dev_success"})
        _log_entry("dev_success", {"demand_len": len(demand)})
        return True
    except Exception:
        return False


def learn_from_dev_failure(demand: str, error_msg: str) -> bool:
    """
    開發：失敗時記錄錯誤模式，供後續避免。
    """
    if not demand or not error_msg or len(error_msg.strip()) < 10:
        return False
    try:
        err = error_msg.strip()[:800]
        text = f"【開發失敗模式】任務: {demand}\n錯誤: {err}"
        add(text, source="開發失敗", metadata={"type": "dev_failure"})
        _log_entry("dev_failure", {"err_len": len(err)})
        return True
    except Exception:
        return False


def learn_from_tool_output(tool_name: str, output: str, success: bool = True) -> bool:
    """
    從工具輸出萃取結構化資訊（如 list_dir、read_file 的結果）。
    """
    if not output or len(output.strip()) < 50:
        return False
    out = output.strip()[:2000]
    try:
        kind = "工具成功" if success else "工具失敗"
        text = f"【{kind}】{tool_name}\n{out}"
        add(text, source=f"工具:{tool_name}", metadata={"type": "tool", "success": success})
        return True
    except Exception:
        return False


def learn_from_reasoning_record(text: str, user_query: str = "") -> bool:
    """
    從 AI 回應中擷取 <!-- REASONING_RECORD --> 區塊，轉為運算過程範本寫入知識庫。
    """
    try:
        from reasoning_tracer import learn_from_reasoning_text
        return learn_from_reasoning_text(text, user_query)
    except Exception:
        return False


def extract_and_learn(text: str, context: str = "對話") -> int:
    """
    從任意文字萃取可學習片段（程式碼塊、列表、步驟）並寫入。
    回傳寫入筆數。
    """
    count = 0
    # 程式碼塊
    code_blocks = re.findall(r"```(?:\w+)?\s*\n([\s\S]*?)```", text)
    for block in code_blocks[:3]:
        b = block.strip()
        if len(b) > 50 and ("def " in b or "import " in b or "function " in b or "const " in b):
            try:
                add(f"【程式碼】\n{b}", source=context, metadata={"type": "code"})
                count += 1
            except Exception:
                pass
    # 編號步驟
    steps = re.findall(r"(?:^|\n)\s*\d+[\.\)]\s*(.+?)(?=\n\s*\d+[\.\)]|\n\n|$)", text, re.DOTALL)
    if len(steps) >= 3:
        combined = "\n".join(s.strip()[:200] for s in steps[:10])
        if len(combined) > 100:
            try:
                add(f"【步驟】\n{combined}", source=context, metadata={"type": "steps"})
                count += 1
            except Exception:
                pass
    return count


def run_scheduled_learn() -> str:
    """
    執行一輪排程學習：檢查是否有待處理日誌、觸發 GitHub 學習等。
    可由 cron / 工作排程器定期呼叫。
    """
    lines = []
    try:
        from brain_github_learner import run_auto_learn_topics
        lines.append("執行 GitHub 主題學習...")
        result = run_auto_learn_topics(per_topic=2)
        lines.append(result[:1500])
    except Exception as e:
        lines.append(f"GitHub 學習跳過: {e}")
    return "\n".join(lines)

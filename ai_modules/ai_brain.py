"""
築未科技大腦 - 多 AI 串聯、知識注入、成本記錄
"""
import asyncio
import os
from typing import Optional

try:
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv()
    _user_env = Path.home() / ".openclaw" / ".env"
    if _user_env.exists():
        load_dotenv(_user_env, override=True)
except ImportError:
    pass


SYSTEM_PROMPT = """築未科技萬能助理。只處理、不解釋。
規則：直接給作法或答案，不說明原因、不教學、不廢話。
對用戶提供的文字、文件、段落須仔細辨識與理解，依內容作答，勿臆測或跳過細節。
嚴禁：自我介紹、LLM 本質分析、意識論述、局限性說明。"""


def _inject_knowledge(prompt: str, user_id: str = "default") -> str:
    """統一檢索：brain_knowledge + Chroma + Mem0；長輸入時會提高文件辨識與理解度"""
    try:
        from brain_retrieve import retrieve_context
        # 使用較長查詢前綴（最多 500 字）以提升文件／段落檢索準度
        q = prompt.strip()[:500]
        ctx = retrieve_context(q, user_id=user_id)
        if ctx:
            return f"{ctx}用戶：{prompt}"
    except Exception:
        try:
            from brain_knowledge import search
            ctx = search(prompt.strip()[:500], limit=8)
            if ctx:
                return f"{ctx}\n\n---\n\n用戶：{prompt}"
        except Exception:
            pass
    return prompt


def _ask_sync(prompt: str, images=None, ensemble: bool = False, system_prompt: str = "", use_coder_model: bool = False) -> tuple[str, str]:
    try:
        from ai_providers import ask_sync
        sys_p = system_prompt or SYSTEM_PROMPT
        return ask_sync(prompt, images=images, ensemble=ensemble, system_prompt=sys_p, use_coder_model=use_coder_model)
    except Exception as e:
        return f"連線失敗: {e}", "無"


def _record_cost(provider: str, prompt_len: int = 0):
    try:
        from ai_cost_tracker import record
        record(provider, prompt_len)
    except Exception:
        pass


def _add_knowledge(text: str, source: str = "對話", question: str = ""):
    try:
        from brain_knowledge import add
        if text and len(text.strip()) > 20:
            add(text.strip()[:2000], source=source)
    except Exception:
        pass
    if question and text:
        try:
            from brain_self_learner import learn_from_qa, extract_and_learn, learn_from_reasoning_record
            learn_from_qa(question, text)
            extract_and_learn(text, context=source)
            learn_from_reasoning_record(text, user_query=question)
        except Exception:
            pass
    try:
        from memory_mem0 import add as mem0_add, is_available as mem0_ok
        if mem0_ok() and text and len(text.strip()) > 30:
            mem0_add("default", text.strip()[:2000], metadata={"source": source})
    except Exception:
        pass


async def ask(
    prompt: str,
    history=None,
    images=None,
    ensemble: bool = True,
    learn: bool = True,
    user_id: str = "default",
    use_coder_model: bool = False,
) -> tuple[str, str]:
    """
    非同步呼叫 AI，注入知識、記錄成本、可寫入知識庫。
    system + context + user 格式，回傳 (回覆文字, 提供者)
    """
    if not prompt or not str(prompt).strip():
        return "請輸入內容。", "無"
    use_image = bool(images)
    enhanced = _inject_knowledge(str(prompt).strip(), user_id=user_id)

    loop = asyncio.get_event_loop()
    resp, provider = await loop.run_in_executor(
        None,
        lambda: _ask_sync(enhanced, images=images, ensemble=ensemble, use_coder_model=use_coder_model),
    )
    if resp:
        _record_cost(provider, len(str(prompt)))
        if learn:
            _add_knowledge(resp, source="對話", question=str(prompt).strip())
    return resp or "無回覆", provider


def get_available_providers():
    """回傳目前可用的 AI 提供者列表。"""
    try:
        from ai_providers import get_available
        return get_available()
    except Exception:
        return ["Ollama"]

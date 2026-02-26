"""
築未科技大腦 Agent - ReAct 式工具調用
依序：思考 → 工具調用 → 觀察 → 直到得出最終回答
若有 agent_enhanced（Mem0、Chroma 等），將自動使用強化版
"""
import asyncio
from typing import Callable

from ai_brain import ask
from agent_tools import parse_tool_call, run_tool, tool_descriptions

def _use_enhanced() -> bool:
    try:
        from agent_enhanced import is_enhanced
        return is_enhanced()
    except Exception:
        return False

AGENT_SYSTEM = """你是築未科技大腦的 AI Agent，能讀寫檔案、撰寫程式碼、建置與部署。
""" + tool_descriptions() + """
流程：
1. 規劃：先分析任務，列出步驟（例如：讀檔→修改→寫回）。
2. 執行：若需工具則輸出 TOOL: 工具名([參數])，等結果後再決定下一步。
3. 反思：每次工具結果後檢查是否達成目標，若失敗請換路徑或參數重試。
- 寫程式：用 read_file 讀取現有檔，再用 write_file 寫入修改或新檔。
- 部署：用 run_build 建置，run_deploy_vercel 部署到 Vercel。
- 版本控制：用 run_git_push(["commit 訊息"]) 提交並推送。
得到足夠資訊後，直接給出最終回答，不要再用 TOOL。
請用繁體中文簡潔回覆。
嚴禁：自我介紹、LLM 本質分析、意識論述、局限性說明。"""

MAX_ITER = 8


async def run_agent(
    user_prompt: str,
    on_step: Callable[[str, str], None] | None = None,
) -> tuple[str, str]:
    """
    執行 Agent 迴圈。
    回傳 (最終回答, 使用的 AI 提供者)
    on_step(tool_result, partial_response) 可選，用於即時顯示步驟。
    """
    # 規劃：複雜任務先產生步驟列表
    plan_prompt = f"{AGENT_SYSTEM}\n\n用戶：{user_prompt}\n\n（若任務需多步驟，請先簡述 1～3 步計畫再執行。若已清楚則直接使用工具。）"
    prompt = plan_prompt
    provider_used = "無"

    for i in range(MAX_ITER):
        resp, provider = await ask(prompt, history=None, ensemble=False, use_coder_model=True)
        provider_used = provider
        if not resp:
            break

        tool_info = parse_tool_call(resp)
        if not tool_info:
            return resp.strip(), provider

        name, args = tool_info
        result = run_tool(name, args)
        if on_step:
            on_step(result, resp)

        has_error = "[錯誤]" in result or "[拒絕]" in result
        args_sum = str(args)[:200] if args else ""
        if result and not has_error:
            try:
                from brain_self_learner import learn_from_agent_success
                learn_from_agent_success(name, args_sum, result[:500])
            except Exception:
                pass
        elif has_error:
            try:
                from brain_self_learner import learn_from_agent_failure
                learn_from_agent_failure(name, args_sum, result[:500])
            except Exception:
                pass

        # 反思：工具失敗時提醒換方法
        ref = ""
        if has_error:
            ref = "【反思】結果未達標，請換路徑、參數或改用其他工具重試。"
        prompt = f"{prompt}\n\n你的輸出：{resp}\n\n[工具結果]\n{result}\n\n{ref}\n\n請根據上述結果繼續，若已完成任務則給出最終回答。"
        if i == MAX_ITER - 2:
            prompt += "\n這是倒數第二輪，請給出最終回答。"

    return "[Agent 未在時限內完成]" if not resp else resp.strip(), provider_used


def run_agent_sync(user_prompt: str, on_step=None, user_id: str = "default", _skip_enhanced: bool = False) -> tuple[str, str]:
    """若有 agent_enhanced 且已啟用，會自動注入 Mem0 + Chroma 後執行。_skip_enhanced 供內部避免遞迴。"""
    if not _skip_enhanced and _use_enhanced():
        try:
            from agent_enhanced import run_agent_sync as enhanced_sync
            return enhanced_sync(user_prompt, on_step, user_id)
        except Exception:
            pass
    try:
        asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, run_agent(user_prompt, on_step)).result(timeout=300)
    except RuntimeError:
        return asyncio.run(run_agent(user_prompt, on_step))

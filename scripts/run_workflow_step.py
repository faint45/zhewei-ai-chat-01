# -*- coding: utf-8 -*-
"""
築未科技 — 本地工作流執行手腳
供雙擊 .bat 或 CLI 呼叫，執行：單次任務、運算（視覺辨識）、生成（報表）、視覺與報表一鍵。
路徑限 D/Z；視覺引擎呼叫與報表分流不更動 agent_tools / report_generator 邏輯。
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

# 專案根目錄
_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = os.environ.get("ZHEWEI_PROJECT_ROOT") or str(_SCRIPT_DIR.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

# 延遲匯入，確保 cwd 與 path 正確
def _get_agent_tools():
    from agent_tools import BRAIN_WORKSPACE, run_vision_engine, generate_progress_report
    return BRAIN_WORKSPACE, run_vision_engine, generate_progress_report


def step_single_task(task: str) -> str:
    """執行單次任務（完整 ReAct 八階段）。有 ANTHROPIC_API_KEY 或 CLAUDE_API_KEY 時注入 ClaudeService 供階段 4/6。"""
    import os
    from ai_service import GeminiService, OllamaService, ClaudeService
    from agent_logic import AgentManager
    claude_key = (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY") or "").strip()
    claude_service = ClaudeService() if claude_key else None
    manager = AgentManager(
        gemini_service=GeminiService(),
        ollama_service=OllamaService(),
        claude_service=claude_service,
    )
    return asyncio.run(manager.run(task))


def step_vision(input_dir: str) -> str:
    """運算：對輸入目錄內圖片執行視覺辨識，回傳逗號分隔 detected。"""
    BRAIN_WORKSPACE, run_vision_engine, _ = _get_agent_tools()
    p = Path(input_dir).resolve() if os.path.isabs(input_dir) else BRAIN_WORKSPACE / input_dir
    if not p.is_dir():
        return f"錯誤：目錄不存在 {p}"
    exts = (".jpg", ".jpeg", ".png", ".bmp")
    images = [f for f in p.iterdir() if f.suffix.lower() in exts]
    if not images:
        return "錯誤：目錄內無支援圖片 (.jpg/.png/.bmp)"
    all_detected = []
    for img in images:
        rel = str(img.relative_to(p)) if p in img.parents else img.name
        r = run_vision_engine(str(img))
        if r.get("ok") and r.get("detected"):
            all_detected.extend(r["detected"])
        else:
            all_detected.append(f"(無辨識:{rel})")
    return ",".join(dict.fromkeys(all_detected)) or "無辨識結果"


def step_generate_report(detected: str) -> str:
    """生成：依辨識結果寫入 Z 槽 Reports（JSONL + CSV）。"""
    _, _, generate_progress_report = _get_agent_tools()
    r = generate_progress_report(detected)
    if r.get("ok"):
        return r.get("message", "報表已寫入 Z 槽 Reports。")
    return r.get("error", str(r))


def step_vision_and_report(input_dir: str) -> str:
    """運算 + 生成：視覺辨識後直接生成報表。"""
    detected = step_vision(input_dir)
    if detected.startswith("錯誤："):
        return detected
    return step_generate_report(detected)


def main():
    parser = argparse.ArgumentParser(description="築未科技本地工作流執行（編碼/撰寫/運算/分配/執行/回饋/生成）")
    parser.add_argument("--step", type=str, required=True,
                        choices=["單次任務", "運算", "生成", "視覺與報表"],
                        help="單次任務=完整 ReAct；運算=視覺辨識；生成=報表；視覺與報表=運算+生成")
    parser.add_argument("--task", type=str, default="", help="單次任務內容（--step 單次任務 時必填）")
    parser.add_argument("--input", type=str, default="", help="輸入目錄（運算/視覺與報表用，預設 D:\\brain_workspace\\input）")
    parser.add_argument("--detected", type=str, default="", help="辨識結果逗號分隔（--step 生成 時使用）")
    args = parser.parse_args()

    if args.step == "單次任務":
        if not args.task.strip():
            print("請提供 --task \"任務內容\"")
            sys.exit(1)
        print(step_single_task(args.task.strip()))
        return
    if args.step == "運算":
        inp = (args.input or r"D:\brain_workspace\input").strip()
        print(step_vision(inp))
        return
    if args.step == "生成":
        det = (args.detected or "").strip()
        if not det:
            print("請提供 --detected \"物件1,物件2,...\"")
            sys.exit(1)
        print(step_generate_report(det))
        return
    if args.step == "視覺與報表":
        inp = (args.input or r"D:\brain_workspace\input").strip()
        print(step_vision_and_report(inp))
        return
    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
築未科技 — E2E 測試腳本（避開終端編碼）
直接呼叫 step_single_task、step_vision_and_report，不需 CLI 傳中文參數。
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.environ.get("ZHEWEI_PROJECT_ROOT") or str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from scripts.run_workflow_step import step_single_task, step_vision_and_report

if __name__ == "__main__":
    print("E2E 單次任務：請列出 D:\\brain_workspace 目錄內容")
    out = step_single_task("請列出 D:\\brain_workspace 目錄內容")
    print(out)
    print("\n---\nE2E 視覺與報表（input 目錄）")
    inp = os.environ.get("BRAIN_WORKSPACE", r"D:\brain_workspace") + r"\input"
    out2 = step_vision_and_report(inp)
    print(out2)
    print("\nE2E 完成。")

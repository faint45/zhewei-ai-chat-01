# -*- coding: utf-8 -*-
"""
築未大腦單次任務啟動器（可置於 D:\\brain_workspace 或專案 brain_workspace）
將專案根目錄加入 path 後執行 agent_logic --task，供部署區 venv 調用。
用法：python run_task.py --task "分析 input/test.jpg 並產出 LPC 標記報表"
"""
import os
import sys
from pathlib import Path

# 專案根目錄（開發區或部署區指向同一主腦）
_here = Path(__file__).resolve().parent
PROJECT_ROOT = os.environ.get("ZHEWEI_PROJECT_ROOT")
if not PROJECT_ROOT:
    if (_here / "agent_logic.py").exists():
        PROJECT_ROOT = str(_here)
    elif (_here.parent / "agent_logic.py").exists():
        PROJECT_ROOT = str(_here.parent)
    else:
        PROJECT_ROOT = str(Path(r"C:\Users\user\Desktop\zhe-wei-tech"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 切換工作目錄至專案根，使 agent_tools 等模組路徑正確
os.chdir(PROJECT_ROOT)

# 委派給 agent_logic 的 __main__
import agent_logic
import asyncio
import argparse
from ai_service import GeminiService, OllamaService

def main():
    parser = argparse.ArgumentParser(description="築未大腦單次任務執行")
    parser.add_argument("--task", type=str, required=True, help="下達任務內容")
    args = parser.parse_args()
    gemini = GeminiService()
    ollama = OllamaService()
    manager = agent_logic.AgentManager(gemini_service=gemini, ollama_service=ollama)
    result = asyncio.run(manager.run(args.task))
    print(result)

if __name__ == "__main__":
    main()

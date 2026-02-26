# -*- coding: utf-8 -*-
"""
築未科技大腦 — CodeBuddy 整合模組
讓本地機器人可呼叫 CodeBuddy CLI 執行程式開發任務
"""
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

# CodeBuddy CLI 指令（codebuddy 或 cbc）
CODEBUDDY_CMD = "codebuddy"
CODEBUDDY_TIMEOUT = 120


def is_available() -> bool:
    """檢查 CodeBuddy CLI 是否已安裝"""
    return shutil.which(CODEBUDDY_CMD) is not None or shutil.which("cbc") is not None


def _get_cmd() -> str:
    """取得可用的 CodeBuddy 指令"""
    if shutil.which(CODEBUDDY_CMD):
        return CODEBUDDY_CMD
    if shutil.which("cbc"):
        return "cbc"
    return CODEBUDDY_CMD


def ask(
    prompt: str,
    output_format: str = "text",
    model: str = "",
    skip_permissions: bool = False,
    working_dir: str = "",
    allowed_tools: list[str] = None,
    timeout: int = CODEBUDDY_TIMEOUT,
) -> tuple[str, bool]:
    """
    呼叫 CodeBuddy CLI 執行單次任務。
    
    Args:
        prompt: 任務描述
        output_format: 輸出格式 (text, json, stream-json)
        model: 模型名稱 (如 gpt-5, gpt-4)
        skip_permissions: 是否跳過權限檢查（修改檔案時需要）
        working_dir: 工作目錄
        allowed_tools: 允許的工具列表
        timeout: 逾時秒數
    
    Returns:
        (回應內容, 是否成功)
    """
    if not is_available():
        return "[錯誤] CodeBuddy CLI 未安裝。請先安裝：https://www.codebuddy.ai/docs/cli/quickstart", False
    
    cmd = [_get_cmd(), "-p", prompt, "--output-format", output_format]
    
    if model:
        cmd.extend(["--model", model])
    
    if skip_permissions:
        cmd.append("--dangerously-skip-permissions")
    
    if allowed_tools:
        cmd.extend(["--allowedTools"] + allowed_tools)
    
    cwd = working_dir or str(Path.cwd())
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
        )
        
        output = result.stdout.strip() or result.stderr.strip()
        
        if output_format == "json" and output:
            try:
                data = json.loads(output)
                return data.get("response", output), result.returncode == 0
            except json.JSONDecodeError:
                pass
        
        return output or "[無回應]", result.returncode == 0
    
    except subprocess.TimeoutExpired:
        return f"[逾時] CodeBuddy 執行超過 {timeout} 秒", False
    except FileNotFoundError:
        return "[錯誤] CodeBuddy CLI 未找到", False
    except Exception as e:
        return f"[錯誤] {e}", False


def code_review(file_path: str, working_dir: str = "") -> tuple[str, bool]:
    """程式碼審查"""
    prompt = f"Review the code in file: {file_path}. Provide suggestions for improvement."
    return ask(prompt, working_dir=working_dir)


def generate_code(description: str, file_path: str = "", working_dir: str = "") -> tuple[str, bool]:
    """生成程式碼"""
    prompt = f"Generate code for: {description}"
    if file_path:
        prompt += f"\nWrite to file: {file_path}"
    return ask(prompt, skip_permissions=bool(file_path), working_dir=working_dir)


def fix_code(file_path: str, error_message: str = "", working_dir: str = "") -> tuple[str, bool]:
    """修復程式碼錯誤"""
    prompt = f"Fix the code in file: {file_path}"
    if error_message:
        prompt += f"\nError message: {error_message}"
    return ask(prompt, skip_permissions=True, working_dir=working_dir)


def explain_code(file_path: str, working_dir: str = "") -> tuple[str, bool]:
    """解釋程式碼"""
    prompt = f"Explain the code in file: {file_path}"
    return ask(prompt, working_dir=working_dir)


def analyze_project(project_dir: str = "") -> tuple[str, bool]:
    """分析專案結構"""
    prompt = "Analyze the project structure and suggest improvements."
    return ask(prompt, working_dir=project_dir or str(Path.cwd()))


def git_commit_message(working_dir: str = "") -> tuple[str, bool]:
    """根據 git diff 生成 commit message"""
    prompt = "Generate a concise commit message based on the current git diff."
    return ask(prompt, working_dir=working_dir)


def run_task(task: str, working_dir: str = "", allow_write: bool = False) -> tuple[str, bool]:
    """
    執行任意開發任務（通用介面）
    
    Args:
        task: 任務描述
        working_dir: 工作目錄
        allow_write: 是否允許寫入檔案
    
    Returns:
        (回應, 是否成功)
    """
    return ask(task, skip_permissions=allow_write, working_dir=working_dir)


# 供 agent_tools 使用的工具描述
TOOL_DESCRIPTION = """
CodeBuddy 工具：呼叫 CodeBuddy AI 執行程式開發任務
- codebuddy_ask(prompt, allow_write=False): 執行任意開發任務
- codebuddy_review(file_path): 程式碼審查
- codebuddy_fix(file_path, error): 修復程式碼
- codebuddy_generate(description, file_path): 生成程式碼
"""


if __name__ == "__main__":
    print("CodeBuddy 整合模組")
    print(f"CLI 可用: {is_available()}")
    if is_available():
        resp, ok = ask("Say hello in Chinese", output_format="text")
        print(f"測試回應: {resp}")
        print(f"成功: {ok}")

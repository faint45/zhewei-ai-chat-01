#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart GUI Agent（主機端）
流程：
1) 截取全螢幕
2) 讓 VLM 輸出結構化 action plan（動態座標）
3) 可選擇直接執行（execute=true）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path

import pyautogui


ROOT = Path(__file__).resolve().parent.parent
DENY_TEXT = [
    "關機",
    "重開機",
    "格式化",
    "刪除系統",
    "自我銷毀",
    "shutdown",
    "reboot",
    "poweroff",
    "format c:",
    "diskpart",
]
DANGEROUS_HOTKEYS = {
    ("alt", "f4"),
    ("ctrl", "alt", "delete"),
    ("win", "r"),
    ("win", "x"),
    ("win", "l"),
}


def _extract_json(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return {}
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _is_dangerous_text(text: str) -> bool:
    low = (text or "").lower()
    return any(p in low for p in DENY_TEXT)


def _plan_with_vlm(instruction: str, screenshot: Path, max_actions: int, provider: str = "auto", strict: bool = False) -> tuple[bool, dict | str]:
    py = ROOT / "Jarvis_Training" / ".venv312" / "Scripts" / "python.exe"
    script = ROOT / "scripts" / "vlm_vision_agent.py"
    prompt = (
        "請你根據畫面，為我規劃可執行的 GUI 操作步驟。"
        "僅輸出 JSON，格式："
        '{"summary":"","actions":[{"action":"move|click|double_click|right_click|type|hotkey|key|wait|scroll","x":0,"y":0,"text":"","keys":[],"seconds":0.5,"amount":-400,"reason":""}]}。'
        f"最多 {max_actions} 步。指令：{instruction}"
    )
    if strict:
        prompt += "。若畫面資訊不足，actions 可為空陣列，summary 請明確寫缺少哪個元素。禁止危險操作。"
    cmd = [
        str(py),
        str(script),
        "--mode",
        "file",
        "--image",
        str(screenshot),
        "--question",
        prompt,
        "--provider",
        provider,
    ]
    try:
        p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=150)
        out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        if not lines:
            return False, "VLM 無回應"
        obj = _extract_json(lines[-1])
        if not obj:
            return True, {"summary": out[-800:], "actions": []}
        if not obj.get("ok", True):
            return False, str(obj.get("error") or "VLM failed")
        result = obj.get("result", {})
        if isinstance(result, dict) and "actions" in result:
            return True, result
        return True, {"summary": str(result)[:600], "actions": []}
    except Exception as e:
        return False, str(e)


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(v)))


def _execute_actions(actions: list[dict], max_actions: int) -> list[str]:
    w, h = pyautogui.size()
    logs: list[str] = []
    for i, raw in enumerate(actions[:max_actions], start=1):
        if not isinstance(raw, dict):
            continue
        a = str(raw.get("action", "")).strip().lower()
        x = _clamp(int(raw.get("x", w // 2) or (w // 2)), 1, max(1, w - 1))
        y = _clamp(int(raw.get("y", h // 2) or (h // 2)), 1, max(1, h - 1))
        text = str(raw.get("text", "") or "")
        keys = raw.get("keys", [])
        sec = float(raw.get("seconds", 0.6) or 0.6)
        amount = int(raw.get("amount", -400) or -400)
        try:
            if a == "move":
                pyautogui.moveTo(x, y, duration=0.2)
            elif a == "click":
                pyautogui.click(x, y)
            elif a == "double_click":
                pyautogui.doubleClick(x, y)
            elif a == "right_click":
                pyautogui.rightClick(x, y)
            elif a == "type":
                if text:
                    if _is_dangerous_text(text):
                        logs.append(f"{i}. blocked type due to safety policy")
                        continue
                    pyautogui.write(text, interval=0.02)
            elif a == "hotkey":
                if isinstance(keys, list) and keys:
                    key_tuple = tuple([str(k).strip().lower() for k in keys[:4] if str(k).strip()])
                    if key_tuple in DANGEROUS_HOTKEYS:
                        logs.append(f"{i}. blocked hotkey={'+'.join(key_tuple)}")
                        continue
                    pyautogui.hotkey(*[str(k) for k in keys[:4]])
            elif a == "key":
                if text:
                    pyautogui.press(text)
            elif a == "wait":
                time.sleep(max(0.1, min(5.0, sec)))
            elif a == "scroll":
                pyautogui.scroll(amount, x=x, y=y)
            else:
                logs.append(f"{i}. skip unsupported action={a}")
                continue
            logs.append(f"{i}. ok action={a} x={x} y={y}")
        except Exception as e:
            logs.append(f"{i}. error action={a}: {e}")
    return logs


def run(instruction: str, execute: bool, max_actions: int, retry_count: int = 3) -> dict:
    low = instruction.lower()
    for p in DENY_TEXT:
        if p in low:
            return {"ok": False, "error": f"blocked by safety policy: {p}"}

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    out_dir = ROOT / "reports" / "smart_gui"
    out_dir.mkdir(parents=True, exist_ok=True)
    retry_count = max(1, min(5, int(retry_count or 3)))
    has_claude = bool((os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY") or "").strip())
    provider_order = ["ollama"]
    if has_claude:
        provider_order.append("claude")
    provider_order.append("auto")

    attempts = []
    best_plan: dict = {}
    best_actions: list[dict] = []
    last_error = ""
    screenshot = None
    for i in range(retry_count):
        provider = provider_order[min(i, len(provider_order) - 1)]
        screenshot = out_dir / f"screen_{int(time.time())}_{i+1}.png"
        pyautogui.screenshot().save(str(screenshot))
        ok, plan_or_err = _plan_with_vlm(
            instruction=instruction,
            screenshot=screenshot,
            max_actions=max_actions,
            provider=provider,
            strict=(i > 0),
        )
        if not ok:
            last_error = str(plan_or_err)
            attempts.append(f"attempt#{i+1}:{provider}:error")
            continue
        plan = plan_or_err if isinstance(plan_or_err, dict) else {}
        actions = plan.get("actions", []) if isinstance(plan, dict) else []
        if not isinstance(actions, list):
            actions = []
        attempts.append(f"attempt#{i+1}:{provider}:actions={len(actions)}")
        best_plan = plan
        best_actions = actions
        # 有可執行動作就停止重試
        if actions:
            break
        # dry-run 允許無 actions，避免無限重試
        if not execute:
            break

    if screenshot is None:
        screenshot = out_dir / f"screen_{int(time.time())}.png"
    plan = best_plan
    actions = best_actions
    result = {
        "ok": True,
        "execute": bool(execute),
        "screenshot": str(screenshot),
        "summary": str(plan.get("summary", "")) if isinstance(plan, dict) else "",
        "actions": actions[:max_actions],
        "attempts": attempts,
    }
    if execute and actions:
        result["execution_logs"] = _execute_actions(actions, max_actions)
    elif execute and not actions:
        result["execution_logs"] = ["no actionable plan returned; stopped safely"]
        result["warning"] = last_error or "VLM did not return executable actions"
    else:
        result["execution_logs"] = ["dry-run: no actions executed"]
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instruction", required=True)
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--max-actions", type=int, default=8)
    ap.add_argument("--retry-count", type=int, default=3)
    args = ap.parse_args()

    res = run(
        instruction=args.instruction,
        execute=args.execute,
        max_actions=max(1, min(20, args.max_actions)),
        retry_count=max(1, min(5, args.retry_count)),
    )
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

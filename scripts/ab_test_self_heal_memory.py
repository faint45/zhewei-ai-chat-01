#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
記憶生效 A/B 測試腳本
驗證自癒記憶是否縮短修復輪數。
- Run A（冷啟動）：以空白記憶執行
- Run B（暖啟動）：沿用 Run A 寫入的記憶再度執行
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 確保能 import self_heal_web_loop
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
for p in (str(ROOT), str(SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

RUNS_DIR = ROOT / "reports" / "self_heal_runs"
AB_REPORT_DIR = ROOT / "reports" / "self_heal_ab"
MEMORY_JSONL = ROOT / "reports" / "self_heal_memory.jsonl"
BACKUP_SUFFIX = ".ab_backup"


def _backup_memory() -> bool:
    if not MEMORY_JSONL.exists():
        return True
    backup = Path(str(MEMORY_JSONL) + BACKUP_SUFFIX)
    try:
        shutil.copy2(MEMORY_JSONL, backup)
        return True
    except Exception:
        return False


def _restore_memory() -> bool:
    backup = Path(str(MEMORY_JSONL) + BACKUP_SUFFIX)
    if not backup.exists():
        return True
    try:
        shutil.copy2(backup, MEMORY_JSONL)
        backup.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _clear_memory() -> None:
    if MEMORY_JSONL.exists():
        MEMORY_JSONL.write_text("", encoding="utf-8")
    else:
        MEMORY_JSONL.parent.mkdir(parents=True, exist_ok=True)
        MEMORY_JSONL.write_text("", encoding="utf-8")


def _run_self_heal(goal: str, max_rounds: int) -> dict[str, Any]:
    import self_heal_web_loop as sh

    return sh.run_self_heal(goal=goal, max_rounds=max_rounds, skip_docker=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Self-Heal Memory A/B Test")
    parser.add_argument(
        "--goal",
        default="Flask API with /health and /users and pytest",
        help="測試目標（英文較穩）",
    )
    parser.add_argument("--max-rounds", type=int, default=3, help="每輪最大修復次數")
    parser.add_argument("--no-cold-clear", action="store_true", help="不清空記憶（Run A 沿用既有記憶）")
    args = parser.parse_args()

    goal = (args.goal or "").strip() or "Flask API with /health and /users and pytest"
    max_rounds = max(1, args.max_rounds)
    cold_clear = not args.no_cold_clear

    AB_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = AB_REPORT_DIR / f"ab_{ts}.json"

    print("[AB] Self-Heal Memory A/B Test")
    print(f"[AB] goal: {goal}")
    print(f"[AB] max_rounds: {max_rounds}")
    print(f"[AB] cold_clear: {cold_clear}")
    print()

    # Backup memory
    if cold_clear:
        if not _backup_memory():
            print("[WARN] Failed to backup memory, proceeding anyway")
        _clear_memory()
        print("[AB] Run A: COLD (memory cleared)")
    else:
        print("[AB] Run A: WARM (using existing memory)")

    # Run A
    print("[AB] Running Run A...")
    try:
        report_a = _run_self_heal(goal=goal, max_rounds=max_rounds)
    except Exception as e:
        report_a = {"ok": False, "rounds": 0, "error": str(e)}
    rounds_a = report_a.get("rounds", 0)
    ok_a = report_a.get("ok", False)
    mem_written_a = report_a.get("memory_entries_written", 0)
    print(f"[AB] Run A: ok={ok_a}, rounds={rounds_a}, memory_written={mem_written_a}")

    # Run B (warm - has memory from A if cold_clear)
    print()
    print("[AB] Run B: WARM (has memory from Run A)")
    print("[AB] Running Run B...")
    try:
        report_b = _run_self_heal(goal=goal, max_rounds=max_rounds)
    except Exception as e:
        report_b = {"ok": False, "rounds": 0, "error": str(e)}
    rounds_b = report_b.get("rounds", 0)
    ok_b = report_b.get("ok", False)
    mem_written_b = report_b.get("memory_entries_written", 0)
    print(f"[AB] Run B: ok={ok_b}, rounds={rounds_b}, memory_written={mem_written_b}")

    # Restore memory
    if cold_clear:
        if _restore_memory():
            print("[AB] Memory restored from backup")
        else:
            print("[WARN] Failed to restore memory backup")

    # Summary
    ab_report: dict[str, Any] = {
        "timestamp": ts,
        "goal": goal,
        "max_rounds": max_rounds,
        "cold_clear": cold_clear,
        "run_a": {
            "ok": ok_a,
            "rounds": rounds_a,
            "memory_entries_written": mem_written_a,
            "run_dir": report_a.get("run_dir", ""),
        },
        "run_b": {
            "ok": ok_b,
            "rounds": rounds_b,
            "memory_entries_written": mem_written_b,
            "run_dir": report_b.get("run_dir", ""),
        },
        "comparison": {
            "rounds_reduced": rounds_a - rounds_b,
            "both_ok": ok_a and ok_b,
            "memory_helped": (rounds_b < rounds_a) if (ok_a and ok_b) else None,
        },
    }

    report_path.write_text(json.dumps(ab_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print("[AB] === Summary ===")
    print(f"[AB] Run A rounds: {rounds_a} | Run B rounds: {rounds_b}")
    print(f"[AB] Rounds reduced: {ab_report['comparison']['rounds_reduced']}")
    if ab_report["comparison"]["memory_helped"] is True:
        print("[AB] Memory EFFECTIVE: Run B used fewer rounds")
    elif ab_report["comparison"]["memory_helped"] is False:
        print("[AB] Memory no effect: Run B used same or more rounds")
    else:
        print("[AB] Inconclusive: one or both runs failed")
    print(f"[AB] Report: {report_path}")

    return 0 if (ok_a or ok_b) else 1


if __name__ == "__main__":
    raise SystemExit(main())

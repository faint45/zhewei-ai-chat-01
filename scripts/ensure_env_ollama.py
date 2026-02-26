#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""確保 .env 有 OLLAMA 模型設定，供一鍵部署使用。"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
EXAMPLE = ROOT / ".env.example"

REQUIRED = {
    "OLLAMA_MODEL": "qwen3:32b",
    "OLLAMA_CODER_MODEL": "qwen3:32b",
    "OLLAMA_REASONING_MODEL": "qwen3:32b",
    "OLLAMA_BASE_URL": "http://localhost:11460",
}


def main() -> int:
    if not ENV.exists() and EXAMPLE.exists():
        ENV.write_text(EXAMPLE.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")

    if not ENV.exists():
        print("No .env or .env.example found")
        return 1

    lines = ENV.read_text(encoding="utf-8", errors="ignore").splitlines()
    existing = {}
    rest = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            rest.append(line)
            continue
        if "=" in s:
            k, _, v = s.partition("=")
            key = k.strip()
            if key in REQUIRED:
                existing[key] = v.strip()
                rest.append(line)
                continue
        rest.append(line)

    changed = False
    for key, default in REQUIRED.items():
        if key not in existing or not str(existing.get(key, "")).strip():
            rest.append(f"{key}={default}")
            changed = True

    if changed:
        ENV.write_text("\n".join(rest) + "\n", encoding="utf-8")
        print("Updated .env with OLLAMA vars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

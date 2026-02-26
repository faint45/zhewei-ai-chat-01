#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Keep these at root so homepage remains operational.
KEEP_AT_ROOT = {
    "HOME.md",
    ".env.example",
    ".gitignore",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.openwebui.yml",
    "docker-compose.cloud.yml",
    "package.json",
    "package-lock.json",
    "requirements.txt",
    "requirements-brain.txt",
    "vercel.json",
    "app.py",
    "brain_server.py",
    "ai_service.py",
    "agent_logic.py",
    "agent_tools.py",
    "Start_OpenHands.bat",
    "Start_OpenWebUI.bat",
    "一鍵同步至雲端.bat",
    "啟動完整跑.bat",
    "啟動_築未科技大腦_完整版.bat",
}

# Root directories we should never touch.
SKIP_DIRS = {
    ".git",
    ".cursor",
    ".agents",
    ".codebuddy",
    "Jarvis_Training",
    "brain_workspace",
    "scripts",
    "src",
    "api",
    "public",
    "static",
    "templates",
    "tools",
    "docs",
    "ops",
    "archive",
}


def ensure_dirs() -> dict[str, Path]:
    targets = {
        "docs_ops": ROOT / "docs" / "operations",
        "docs_deploy": ROOT / "docs" / "deployment",
        "docs_handover": ROOT / "docs" / "handover",
        "docs_misc": ROOT / "docs" / "misc",
        "legacy_launchers": ROOT / "ops" / "legacy_launchers",
        "archive_root_misc": ROOT / "archive" / "root_misc",
    }
    for p in targets.values():
        p.mkdir(parents=True, exist_ok=True)
    return targets


def choose_doc_target(name: str, dirs: dict[str, Path]) -> Path:
    low = name.lower()
    if any(k in low for k in ["deploy", "cloud", "railway", "tunnel", "network", "外網", "部屬", "部署"]):
        return dirs["docs_deploy"]
    if any(k in low for k in ["交接", "handover", "status", "狀態", "完成", "清單", "summary", "移交"]):
        return dirs["docs_handover"]
    if any(k in low for k in ["啟動", "操作", "how", "guide", "使用", "指令", "說明", "手冊"]):
        return dirs["docs_ops"]
    return dirs["docs_misc"]


def safe_move(src: Path, dst_dir: Path) -> Path:
    dst = dst_dir / src.name
    if dst.exists():
        stem = src.stem
        suffix = src.suffix
        i = 1
        while True:
            candidate = dst_dir / f"{stem}_{i}{suffix}"
            if not candidate.exists():
                dst = candidate
                break
            i += 1
    shutil.move(str(src), str(dst))
    return dst


def main() -> int:
    dirs = ensure_dirs()
    moved: list[tuple[Path, Path]] = []

    for item in sorted(ROOT.iterdir(), key=lambda p: p.name.lower()):
        if item.name in KEEP_AT_ROOT:
            continue
        if item.is_dir():
            if item.name in SKIP_DIRS:
                continue
            # Leave directories as-is; this script only organizes root files.
            continue
        if not item.is_file():
            continue
        if item.name.startswith("."):
            continue

        ext = item.suffix.lower()
        target: Path | None = None

        if ext in {".md", ".txt"}:
            target = choose_doc_target(item.name, dirs)
        elif ext in {".bat", ".ps1"}:
            target = dirs["legacy_launchers"]
        elif ext in {".log", ".tmp"}:
            target = dirs["archive_root_misc"]
        elif item.name.upper() == "URL":
            target = dirs["archive_root_misc"]

        if target is None:
            continue
        dst = safe_move(item, target)
        moved.append((item, dst))

    report = ROOT / "docs" / "ROOT_ORGANIZE_REPORT.md"
    lines = [
        "# Root Organization Report",
        "",
        f"- root: `{ROOT}`",
        f"- moved files: {len(moved)}",
        "",
        "## Moves",
    ]
    if moved:
        for src, dst in moved:
            lines.append(f"- `{src.name}` -> `{dst.relative_to(ROOT)}`")
    else:
        lines.append("- no file moved")
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] moved={len(moved)}")
    print(f"[OK] report={report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
HEALTH_URL = "http://127.0.0.1:8002/api/health/summary"
REQUIRED_CONTAINERS = [
    "zhewei_brain",
    "zhe-wei-tech-tunnel-1",
    "zhe-wei-ollama",
    "zhewei-qdrant",
]
BOT_HEARTBEAT = ROOT / "Jarvis_Training" / ".jarvis_discord_bot.heartbeat.json"
RUNTIME_MONITOR_LOG = ROOT / "reports" / "runtime_monitor.log"


def _run(cmd: list[str], timeout: int = 10) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout,
        )
        out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
        return int(p.returncode), out
    except Exception as e:
        return 1, str(e)


def _docker_ready() -> tuple[bool, str]:
    rc, out = _run(["docker", "info"], timeout=12)
    return rc == 0, out[-500:]


def _container_running(name: str) -> tuple[bool, str]:
    rc, out = _run(["docker", "inspect", "-f", "{{.State.Running}}", name], timeout=8)
    ok = (rc == 0) and (out.strip().lower() == "true")
    return ok, out.strip()


def _get_health() -> tuple[bool, dict | str]:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))
            return True, data if isinstance(data, dict) else {}
    except Exception as e:
        return False, str(e)


def _file_age_seconds(path: Path) -> float:
    if not path.exists():
        return 1e9
    try:
        return max(0.0, time.time() - path.stat().st_mtime)
    except Exception:
        return 1e9


def main() -> int:
    checks: list[dict] = []

    ok_docker, docker_msg = _docker_ready()
    checks.append({"name": "docker_ready", "ok": ok_docker, "detail": docker_msg})
    if not ok_docker:
        print(json.dumps({"ok": False, "checks": checks}, ensure_ascii=False, indent=2))
        return 2

    all_containers_ok = True
    for c in REQUIRED_CONTAINERS:
        ok, detail = _container_running(c)
        checks.append({"name": f"container:{c}", "ok": ok, "detail": detail})
        all_containers_ok = all_containers_ok and ok

    ok_health, health_payload = _get_health()
    if not ok_health:
        checks.append({"name": "health_api", "ok": False, "detail": str(health_payload)})
    else:
        h = health_payload if isinstance(health_payload, dict) else {}
        checks.append({"name": "health_api", "ok": True, "detail": "reachable"})
        checks.append({"name": "health_status", "ok": str(h.get("status", "")).lower() == "healthy", "detail": str(h.get("status", ""))})
        checks.append({"name": "health_ollama", "ok": bool(h.get("ollama", False)), "detail": str(h.get("ollama", False))})
        voice = h.get("voice", {}) if isinstance(h.get("voice"), dict) else {}
        checks.append({"name": "health_piper_model", "ok": bool(voice.get("piper_model_exists", False)), "detail": str(voice.get("piper_model_exists", False))})

    hb_age = _file_age_seconds(BOT_HEARTBEAT)
    checks.append({"name": "bot_heartbeat_fresh", "ok": hb_age <= 180, "detail": f"age={int(hb_age)}s"})

    mon_age = _file_age_seconds(RUNTIME_MONITOR_LOG)
    checks.append({"name": "runtime_monitor_fresh", "ok": mon_age <= 180, "detail": f"age={int(mon_age)}s"})

    overall = all(bool(x.get("ok", False)) for x in checks)
    print(json.dumps({"ok": overall, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if overall else 3


if __name__ == "__main__":
    raise SystemExit(main())


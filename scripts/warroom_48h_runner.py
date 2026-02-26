#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reports" / "warroom_48h"
REPORT_JSONL = REPORT_DIR / "events.jsonl"
REPORT_SUMMARY = REPORT_DIR / "latest_summary.json"
HEALTH_URL = "http://127.0.0.1:8002/api/health/summary"
PUBLIC_HEALTH_URL = "https://brain.zhe-wei.net/health"
GATE_SCRIPT = ROOT / "scripts" / "commercial_gate.py"
START_SCRIPT = ROOT / "Start_All_Stable.bat"
PY = ROOT / "Jarvis_Training" / ".venv312" / "Scripts" / "python.exe"
HEARTBEAT = ROOT / "Jarvis_Training" / ".jarvis_discord_bot.heartbeat.json"


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _read_env() -> None:
    for p in [ROOT / ".env", ROOT / "Jarvis_Training" / ".env"]:
        if not p.exists():
            continue
        try:
            for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                s = ln.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                if k and k not in os.environ:
                    os.environ[k] = v.strip().strip('"').strip("'")
        except Exception:
            pass


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
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


def _http_json(url: str, timeout: int = 12) -> tuple[bool, dict | str, int]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="ignore")
            obj = json.loads(body) if body.strip() else {}
            return True, obj if isinstance(obj, dict) else {}, int(r.status)
    except urllib.error.HTTPError as e:
        return False, f"http_error:{e.code}", int(e.code)
    except Exception as e:
        return False, str(e), 0


def _post_discord(content: str) -> bool:
    token = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    channel = (os.environ.get("DISCORD_CHANNEL_ID") or "").strip()
    if not token or not channel:
        return False
    payload = json.dumps({"content": content[:1800]}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel}/messages",
        data=payload,
        headers={"Authorization": f"Bot {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return 200 <= int(r.status) < 300
    except Exception:
        return False


def _append_event(event: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with REPORT_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _heartbeat_ok(max_age: int = 180) -> tuple[bool, str]:
    if not HEARTBEAT.exists():
        return False, "missing"
    age = max(0, int(time.time() - HEARTBEAT.stat().st_mtime))
    return age <= max_age, f"age={age}s"


def _run_gate() -> tuple[bool, str]:
    if not PY.exists() or not GATE_SCRIPT.exists():
        return False, "gate_script_missing"
    rc, out = _run([str(PY), str(GATE_SCRIPT)], timeout=25)
    return rc == 0, out[-1200:]


def _smoke_task() -> tuple[bool, str]:
    payload = {
        "objective": "warroom smoke test: reply with one-line status",
        "provider": "ollama",
        "context": "health validation run",
        "auto_run": True,
    }
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8002/api/agent/tasks",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12) as r:
            obj = json.loads(r.read().decode("utf-8", errors="ignore"))
        tid = str((obj or {}).get("task", {}).get("id", "")).strip()
        if not tid:
            return False, "task_create_no_id"
        for _ in range(18):
            time.sleep(2)
            with urllib.request.urlopen(f"http://127.0.0.1:8002/api/agent/tasks/{tid}", timeout=12) as r:
                d = json.loads(r.read().decode("utf-8", errors="ignore"))
            t = (d or {}).get("task", {}) if isinstance(d, dict) else {}
            st = str(t.get("status", "")).lower()
            if st in {"done", "error"}:
                return st == "done", f"task={tid} status={st}"
        return False, f"task={tid} timeout"
    except Exception as e:
        return False, str(e)


def _try_recover() -> tuple[bool, str]:
    if not START_SCRIPT.exists():
        return False, "start_script_missing"
    rc, out = _run(["cmd", "/c", str(START_SCRIPT)], timeout=90)
    return rc == 0, out[-400:]


def run_round(round_no: int) -> dict:
    gate_ok, gate_msg = _run_gate()
    local_ok, local_data, local_code = _http_json(HEALTH_URL)
    pub_ok, pub_data, pub_code = _http_json(PUBLIC_HEALTH_URL)
    hb_ok, hb_msg = _heartbeat_ok()
    smoke_ok, smoke_msg = _smoke_task()
    public_reachable = pub_ok or pub_code in {401, 403}

    checks = [
        {"name": "commercial_gate", "ok": gate_ok, "detail": gate_msg},
        {"name": "health_local", "ok": local_ok and local_code == 200, "detail": f"code={local_code}"},
        {"name": "health_public_reachable", "ok": public_reachable, "detail": f"code={pub_code} detail={pub_data}"},
        {"name": "bot_heartbeat", "ok": hb_ok, "detail": hb_msg},
        {"name": "agent_task_smoke", "ok": smoke_ok, "detail": smoke_msg},
    ]

    overall = all(bool(x["ok"]) for x in checks)
    recovered = {"attempted": False, "ok": True, "detail": ""}
    if not overall:
        recovered["attempted"] = True
        rok, rmsg = _try_recover()
        recovered["ok"] = rok
        recovered["detail"] = rmsg

    event = {
        "ts": _now(),
        "round": round_no,
        "ok": overall,
        "checks": checks,
        "recovery": recovered,
    }
    return event


def summarize() -> dict:
    if not REPORT_JSONL.exists():
        return {"ok_rate": 0.0, "rounds": 0}
    rows = []
    for ln in REPORT_JSONL.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict):
                rows.append(obj)
        except Exception:
            continue
    total = len(rows)
    ok = sum(1 for r in rows if r.get("ok") is True)
    rec = sum(1 for r in rows if isinstance(r.get("recovery"), dict) and r["recovery"].get("attempted"))
    return {
        "generated_at": _now(),
        "rounds": total,
        "ok_rounds": ok,
        "ok_rate": (ok / total) if total else 0.0,
        "recoveries": rec,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=48.0)
    ap.add_argument("--interval-seconds", type=int, default=300)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    _read_env()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    interval = max(30, int(args.interval_seconds))
    end_ts = time.time() + max(0.1, float(args.hours)) * 3600
    round_no = 0
    last_hour_notice = 0

    start_msg = f"[WARROOM] 48H started | interval={interval}s | hours={args.hours}"
    _post_discord(start_msg)
    print(start_msg)

    while True:
        round_no += 1
        ev = run_round(round_no)
        _append_event(ev)
        print(json.dumps(ev, ensure_ascii=False))

        if not ev.get("ok", False):
            _post_discord(f"[WARN] Warroom round #{round_no} failed, recovery={ev.get('recovery')}")

        now = int(time.time())
        if now - last_hour_notice >= 3600:
            s = summarize()
            REPORT_SUMMARY.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
            _post_discord(f"[SUMMARY] Warroom hourly | rounds={s['rounds']} ok_rate={s['ok_rate']:.2%} recoveries={s['recoveries']}")
            last_hour_notice = now

        if args.once:
            break
        if time.time() >= end_ts:
            break
        time.sleep(interval)

    s = summarize()
    REPORT_SUMMARY.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    _post_discord(f"[DONE] Warroom finished | rounds={s['rounds']} ok_rate={s['ok_rate']:.2%} recoveries={s['recoveries']}")
    print(json.dumps({"done": True, "summary": s}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


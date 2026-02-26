#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "Jarvis_Training"))
from env_loader import load_env_file  # type: ignore

STATE_FILE = ROOT / "reports" / "monitor_state.json"
LOG_TARGETS = [
    ROOT / "Jarvis_Training" / "discord_bot_runtime.log",
    ROOT / "brain_system.log",
]
ERROR_HINTS = [
    "traceback",
    "exception",
    "error",
    "failed",
    "fatal",
]
MODE_REQ_FILE = ROOT / "reports" / "mode_switch_request.json"
MODE_RES_FILE = ROOT / "reports" / "mode_switch_result.json"
HOST_JOB_QUEUE_FILE = ROOT / "reports" / "agent_host_jobs.json"
HOST_JOB_RESULT_DIR = ROOT / "reports" / "agent_host_results"

HOST_COMMAND_POLICY = ROOT / "configs" / "host_command_policy.json"
TASK_BUTLER_POLICY = ROOT / "configs" / "task_butler_risk_policy.json"

DENY_PATTERNS = [
    "shutdown",
    "restart-computer",
    "stop-computer",
    "poweroff",
    "reboot",
    "halt",
    "init 0",
    "init 6",
    "rm -rf /",
    "rd /s /q c:\\",
    "del /f /s /q c:\\",
    "format c:",
    "diskpart",
    "bcdedit /delete",
    "cipher /w",
    "sdelete",
    "self-destruct",
    "自我銷毀",
    "刪除自己",
]


def _read_tail(path: Path, line_limit: int = 160) -> str:
    if not path.exists():
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(lines[-line_limit:])
    except Exception:
        return ""


def _docker_status_lines() -> list[str]:
    try:
        p = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=12,
        )
        raw = (p.stdout or "").strip()
        return [ln.strip() for ln in raw.splitlines() if ln.strip()]
    except Exception:
        return []


def _collect_alerts() -> list[str]:
    alerts: list[str] = []

    for log_file in LOG_TARGETS:
        tail = _read_tail(log_file)
        if not tail:
            continue
        low = tail.lower()
        for hint in ERROR_HINTS:
            if hint in low:
                alerts.append(f"log_hit:{log_file.name}:{hint}")
                break

    for ln in _docker_status_lines():
        low = ln.lower()
        if ("exited" in low) or ("unhealthy" in low) or ("restarting" in low):
            alerts.append(f"docker:{ln}")

    return alerts


def _state_read() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}


def _state_write(data: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _post_discord(channel_id: str, token: str, content: str) -> bool:
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    payload = json.dumps({"content": content}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return 200 <= int(resp.status) < 300
    except urllib.error.HTTPError:
        return False
    except Exception:
        return False


def _handle_mode_switch_request(token: str, channel_id: str) -> None:
    if not MODE_REQ_FILE.exists():
        return
    try:
        req = json.loads(MODE_REQ_FILE.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return

    mode = str((req or {}).get("mode", "")).strip().lower()
    requested_at = int((req or {}).get("requested_at", 0) or 0)
    if mode not in {"daily", "dev"}:
        MODE_RES_FILE.parent.mkdir(parents=True, exist_ok=True)
        MODE_RES_FILE.write_text(
            json.dumps({"ok": False, "error": f"invalid mode: {mode}", "requested_at": requested_at, "handled_at": int(time.time())}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return

    # 若結果已更新且比 request 新，跳過重複執行
    if MODE_RES_FILE.exists():
        try:
            res = json.loads(MODE_RES_FILE.read_text(encoding="utf-8", errors="ignore"))
            if int(res.get("requested_at", 0) or 0) == requested_at:
                return
        except Exception:
            pass

    script = ROOT / "scripts" / "switch_stack_mode.ps1"
    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Mode", mode]
    ok = False
    out = ""
    code = 1
    try:
        p = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=180,
        )
        code = int(p.returncode)
        ok = code == 0
        out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()[-3000:]
    except Exception as e:
        out = str(e)

    payload = {
        "ok": ok,
        "mode": mode,
        "exit_code": code,
        "output": out,
        "requested_at": requested_at,
        "handled_at": int(time.time()),
    }
    MODE_RES_FILE.parent.mkdir(parents=True, exist_ok=True)
    MODE_RES_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 執行後移除 request，避免重複切換
    try:
        MODE_REQ_FILE.unlink(missing_ok=True)
    except Exception:
        pass

    if token and channel_id:
        status = "✅" if ok else "❌"
        _post_discord(channel_id, token, f"{status} 模式切換完成：{mode}\nexit={code}\n{out[:1200]}")


def _run_host_job(job_type: str, args: dict | None = None) -> tuple[bool, str, str]:
    py = ROOT / "Jarvis_Training" / ".venv312" / "Scripts" / "python.exe"
    if not py.exists():
        return False, "", f"python not found: {py}"
    job_args = args or {}
    if job_type == "pyautogui_demo":
        script = ROOT / "scripts" / "my_agent.py"
        if not script.exists():
            return False, "", f"script not found: {script}"
        try:
            p = subprocess.run(
                [str(py), str(script)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=120,
            )
            out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()[-2500:]
            return (p.returncode == 0), out, "" if p.returncode == 0 else f"exit={p.returncode}"
        except Exception as e:
            return False, "", str(e)
    if job_type in {"line_open", "line_read_ocr"}:
        script = ROOT / "scripts" / "line_agent.py"
        if not script.exists():
            return False, "", f"script not found: {script}"
        action = "open" if job_type == "line_open" else "read_ocr"
        try:
            p = subprocess.run(
                [str(py), str(script), "--action", action],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=120 if action == "open" else 180,
            )
            out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()[-3000:]
            try:
                # 優先吃最後一行 JSON
                lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
                payload = json.loads(lines[-1]) if lines else {}
                ok = bool(payload.get("ok", p.returncode == 0))
                result = str(payload.get("result") or out).strip()
                err = str(payload.get("error") or "")
                return ok, result[:2500], err[:800]
            except Exception:
                return (p.returncode == 0), out, "" if p.returncode == 0 else f"exit={p.returncode}"
        except Exception as e:
            return False, "", str(e)
    if job_type in {"line_read_vlm", "screen_vlm_query"}:
        script = ROOT / "scripts" / "vlm_vision_agent.py"
        if not script.exists():
            return False, "", f"script not found: {script}"
        mode = "line" if job_type == "line_read_vlm" else "screen"
        question = str((job_args or {}).get("question", "")).strip()
        if not question:
            question = "請摘要畫面重點並輸出 JSON。"
        keywords = (job_args or {}).get("keywords", [])
        if not isinstance(keywords, list):
            keywords = []
        try:
            p = subprocess.run(
                [
                    str(py),
                    str(script),
                    "--mode",
                    mode,
                    "--question",
                    question,
                    "--keywords",
                    ",".join([str(k) for k in keywords if str(k).strip()]),
                    "--provider",
                    "auto",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=180,
            )
            out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()[-3500:]
            try:
                lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
                payload = json.loads(lines[-1]) if lines else {}
                ok = bool(payload.get("ok", p.returncode == 0))
                result = payload.get("result")
                result_text = json.dumps(result, ensure_ascii=False) if isinstance(result, (dict, list)) else str(result or out)
                err = str(payload.get("error") or "")
                return ok, result_text[:2800], err[:800]
            except Exception:
                return (p.returncode == 0), out, "" if p.returncode == 0 else f"exit={p.returncode}"
        except Exception as e:
            return False, "", str(e)
    if job_type == "smart_gui_agent":
        script = ROOT / "scripts" / "smart_gui_agent.py"
        if not script.exists():
            return False, "", f"script not found: {script}"
        instruction = str((job_args or {}).get("instruction", "")).strip() or str((job_args or {}).get("objective", "")).strip()
        if not instruction:
            return False, "", "missing instruction"
        max_actions = int((job_args or {}).get("max_actions", 8) or 8)
        retry_count = int((job_args or {}).get("retry_count", 3) or 3)
        execute = bool((job_args or {}).get("execute", True))
        cmd = [
            str(py),
            str(script),
            "--instruction",
            instruction,
            "--max-actions",
            str(max(1, min(20, max_actions))),
            "--retry-count",
            str(max(1, min(5, retry_count))),
        ]
        if execute:
            cmd.append("--execute")
        try:
            p = subprocess.run(
                cmd,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=220,
            )
            out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()[-3800:]
            try:
                lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
                payload = json.loads(lines[-1]) if lines else {}
                ok = bool(payload.get("ok", p.returncode == 0))
                result_text = json.dumps(payload, ensure_ascii=False)
                err = str(payload.get("error") or "")
                return ok, result_text[:3000], err[:800]
            except Exception:
                return (p.returncode == 0), out, "" if p.returncode == 0 else f"exit={p.returncode}"
        except Exception as e:
            return False, "", str(e)
    if job_type == "host_command":
        command = str((job_args or {}).get("command", "")).strip()
        timeout_sec = int((job_args or {}).get("timeout", 180) or 180)
        if not command:
            return False, "", "missing command"
        low = command.lower()
        for p in DENY_PATTERNS:
            if p in low:
                return False, "", f"blocked by safety policy: {p}"
        # 白名單檢查：僅允許 allowed_builtins 或 allowed 路徑/可執行檔
        # 優先讀取 host_command_policy.json，其次 task_butler_risk_policy 的 command_whitelist
        policy = None
        if HOST_COMMAND_POLICY.exists():
            try:
                policy = json.loads(HOST_COMMAND_POLICY.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                pass
        if (policy is None or not policy.get("enabled")) and TASK_BUTLER_POLICY.exists():
            try:
                tb = json.loads(TASK_BUTLER_POLICY.read_text(encoding="utf-8", errors="ignore"))
                policy = tb.get("command_whitelist") or policy
            except Exception:
                pass
        if policy and policy.get("enabled") and command:
            try:
                tokens = [t.strip() for t in command.split() if t.strip()]
                first = tokens[0].lower() if tokens else ""
                buildins = [b.lower() for b in policy.get("allowed_builtins", [])]
                exes = [e.lower().replace(".exe", "") for e in policy.get("allowed_executables", [])]
                allowed_dirs = [d.lower() for d in policy.get("allowed_script_dirs", [])]
                allowed_ext = [e.lower() for e in policy.get("allowed_extensions", [])]
                if first in buildins:
                    pass
                elif first.replace(".exe", "") in exes:
                    pass
                else:
                    cmd_path = Path(first)
                    if not cmd_path.is_absolute():
                        cmd_path = (ROOT / first).resolve()
                    root_str = str(ROOT.resolve()).lower()
                    path_str = str(cmd_path.resolve()).lower()
                    if not path_str.startswith(root_str):
                        return False, "", "blocked by whitelist: path outside project root"
                    ok_path = any(d in [p.lower() for p in cmd_path.parts] for d in allowed_dirs) and any(
                        str(cmd_path).lower().endswith(e) for e in allowed_ext
                    )
                    if not ok_path:
                        return False, "", "blocked by whitelist: command not in allowed_builtins or allowed paths"
            except Exception:
                return False, "", "blocked by whitelist: policy parse error"
        try:
            p = subprocess.run(
                command,
                cwd=str(ROOT),
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=max(10, min(600, timeout_sec)),
            )
            out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()[-3000:]
            return (p.returncode == 0), out, "" if p.returncode == 0 else f"exit={p.returncode}"
        except Exception as e:
            return False, "", str(e)
    if job_type == "host_python":
        script = str((job_args or {}).get("script_path", "")).strip()
        script_args = (job_args or {}).get("script_args", [])
        timeout_sec = int((job_args or {}).get("timeout", 240) or 240)
        if not script:
            return False, "", "missing script_path"
        scan_text = f"{script} {' '.join([str(x) for x in (script_args or [])])}".lower()
        for p in DENY_PATTERNS:
            if p in scan_text:
                return False, "", f"blocked by safety policy: {p}"
        script_path = Path(script)
        if not script_path.is_absolute():
            script_path = (ROOT / script).resolve()
        if not script_path.exists():
            return False, "", f"script not found: {script_path}"
        cmd = [str(py), str(script_path)]
        if isinstance(script_args, list):
            cmd.extend([str(x) for x in script_args])
        try:
            p = subprocess.run(
                cmd,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=max(10, min(900, timeout_sec)),
            )
            out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()[-3000:]
            return (p.returncode == 0), out, "" if p.returncode == 0 else f"exit={p.returncode}"
        except Exception as e:
            return False, "", str(e)
    return False, "", f"unsupported job_type: {job_type}"


def _handle_agent_host_jobs(token: str, channel_id: str) -> None:
    if not HOST_JOB_QUEUE_FILE.exists():
        return
    try:
        raw = json.loads(HOST_JOB_QUEUE_FILE.read_text(encoding="utf-8", errors="ignore"))
        jobs = raw.get("jobs", [])
    except Exception:
        return
    if not isinstance(jobs, list) or not jobs:
        return

    remaining = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        status = str(job.get("status", "queued")).strip().lower()
        task_id = str(job.get("task_id", "")).strip()
        job_type = str(job.get("job_type", "")).strip().lower()
        if status != "queued" or not task_id:
            remaining.append(job)
            continue

        ok, output, error = _run_host_job(job_type, job.get("args") if isinstance(job.get("args"), dict) else {})
        result = {
            "task_id": task_id,
            "ok": ok,
            "job_type": job_type,
            "result": "host job executed" if ok else "",
            "output": output,
            "error": error,
            "handled_at": int(time.time()),
        }
        HOST_JOB_RESULT_DIR.mkdir(parents=True, exist_ok=True)
        (HOST_JOB_RESULT_DIR / f"{task_id}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if token and channel_id:
            icon = "✅" if ok else "❌"
            _post_discord(channel_id, token, f"{icon} Agent Host Job {task_id}\njob={job_type}\n{(output or error)[:1200]}")

    HOST_JOB_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    HOST_JOB_QUEUE_FILE.write_text(
        json.dumps({"jobs": remaining, "updated": int(time.time())}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    load_env_file(ROOT / ".env")
    load_env_file(ROOT / "Jarvis_Training" / ".env")

    token = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    channel_id = (os.environ.get("DISCORD_CHANNEL_ID") or "").strip()
    cooldown = int((os.environ.get("RUNTIME_ALERT_COOLDOWN_SECONDS") or "600").strip() or "600")
    _handle_mode_switch_request(token, channel_id)
    _handle_agent_host_jobs(token, channel_id)

    alerts = _collect_alerts()
    signature = "|".join(sorted(set(alerts)))
    now = int(time.time())
    st = _state_read()
    last_sig = str(st.get("last_signature") or "")
    last_ts = int(st.get("last_sent_ts") or 0)

    if not alerts:
        _state_write({"last_signature": "", "last_sent_ts": last_ts, "updated": now})
        print("OK: no alerts")
        return 0

    should_send = (signature != last_sig) or (now - last_ts >= max(60, cooldown))
    if should_send and token and channel_id:
        msg = (
            "⚠️ Runtime alert detected\n"
            f"- alerts: {len(alerts)}\n"
            f"- detail: {', '.join(alerts[:8])}\n"
            f"- host: {os.environ.get('COMPUTERNAME', 'unknown')}\n"
            "請檢查 logs 與 docker 狀態。"
        )
        sent = _post_discord(channel_id, token, msg[:1800])
        if sent:
            _state_write({"last_signature": signature, "last_sent_ts": now, "updated": now})
            print("ALERT_SENT")
            return 0

    _state_write({"last_signature": signature, "last_sent_ts": last_ts, "updated": now})
    print("ALERT_DETECTED_BUT_NOT_SENT")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

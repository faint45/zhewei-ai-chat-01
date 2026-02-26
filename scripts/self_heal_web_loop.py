#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "reports" / "self_heal_runs"
MEMORY_JSONL = ROOT / "reports" / "self_heal_memory.jsonl"
DEFAULT_MODEL = (os.environ.get("OLLAMA_MODEL") or "zhewei-brain:latest").strip()
DEFAULT_OLLAMA_BASE = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
MEMORY_DB_PATH = (os.environ.get("JARVIS_DB_PATH") or str(ROOT / "Jarvis_Training" / "chroma_db")).strip()
MEMORY_COLLECTION = (os.environ.get("JARVIS_SELF_HEAL_COLLECTION") or "jarvis_self_heal_memory").strip()


def _call_ollama(prompt: str, timeout: int = 120) -> str:
    body = {
        "model": DEFAULT_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    r = requests.post(f"{DEFAULT_OLLAMA_BASE}/api/generate", json=body, timeout=timeout)
    r.raise_for_status()
    return (r.json().get("response") or "").strip()


def _stable_embedding(text: str, dim: int = 64) -> list[float]:
    digest = hashlib.sha256((text or "").encode("utf-8", errors="ignore")).digest()
    return [((digest[i % len(digest)] / 255.0) * 2.0 - 1.0) for i in range(dim)]


def _append_memory_jsonl(entry: dict[str, Any]) -> None:
    MEMORY_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with MEMORY_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _chroma_add_memory(entry: dict[str, Any]) -> None:
    try:
        import chromadb
    except Exception:
        return
    try:
        client = chromadb.PersistentClient(path=MEMORY_DB_PATH)
        coll = client.get_or_create_collection(name=MEMORY_COLLECTION)
        content = (
            f"[error_signature] {entry.get('error_signature','')}\n"
            f"[goal] {entry.get('goal','')}\n"
            f"[changed_files] {entry.get('changed_files',[])}\n"
            f"[build] {entry.get('build_log_tail','')}\n"
            f"[test] {entry.get('test_log_tail','')}\n"
            f"[runtime] {entry.get('runtime_log_tail','')}\n"
        )
        doc_id = f"heal_{hashlib.sha1((content + str(entry.get('timestamp',''))).encode('utf-8', errors='ignore')).hexdigest()[:16]}"
        got = coll.get(ids=[doc_id], include=[])
        if got.get("ids"):
            return
        coll.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[
                {
                    "goal": str(entry.get("goal", ""))[:200],
                    "error_signature": str(entry.get("error_signature", ""))[:120],
                    "round": int(entry.get("round", 0)),
                    "final_ok": bool(entry.get("final_ok", False)),
                    "time": str(entry.get("timestamp", "")),
                }
            ],
            embeddings=[_stable_embedding(content)],
        )
    except Exception:
        return


def _classify_error_signature(build_log: str, test_log: str, runtime_log: str) -> str:
    text = "\n".join([build_log or "", test_log or "", runtime_log or ""]).lower()
    rules = [
        ("missing_module", r"no module named|modulenotfounderror"),
        ("docker_build_failed", r"error.*(pip install|failed to solve|docker build)"),
        ("pytest_failed", r"=+ fail|assert|pytest"),
        ("healthcheck_failed", r"http [45]\d\d|connection refused|timed out"),
        ("syntax_error", r"syntaxerror|indentationerror"),
        ("port_in_use", r"address already in use|port is already allocated"),
    ]
    for name, pattern in rules:
        if re.search(pattern, text):
            return name
    return "unknown_error"


def _load_recent_memory_context(goal: str, error_signature: str, limit: int = 3) -> str:
    rows: list[dict[str, Any]] = []
    if MEMORY_JSONL.exists():
        try:
            for ln in MEMORY_JSONL.read_text(encoding="utf-8", errors="ignore").splitlines()[-200:]:
                if not ln.strip():
                    continue
                obj = json.loads(ln)
                if not isinstance(obj, dict):
                    continue
                rows.append(obj)
        except Exception:
            rows = rows[-50:]

    # prioritize same signature successful memories
    rows = [r for r in rows if bool(r.get("final_ok", False))]
    rows.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
    same_sig = [r for r in rows if r.get("error_signature") == error_signature][:limit]
    if not same_sig:
        same_sig = rows[:limit]
    if not same_sig:
        return "（暫無歷史修復記憶）"
    lines = ["歷史修復記憶："]
    for i, r in enumerate(same_sig, start=1):
        lines.append(
            f"{i}) sig={r.get('error_signature','')} goal={str(r.get('goal',''))[:80]} "
            f"changed={r.get('changed_files',[])}"
        )
    return "\n".join(lines)


def _extract_first_json_object(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    start = raw.find("{")
    if start < 0:
        return {}
    depth = 0
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                chunk = raw[start : i + 1]
                try:
                    obj = json.loads(chunk)
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    return {}
                break
    return {}


def _infer_required_routes(goal: str) -> list[str]:
    q = (goal or "").strip()
    routes = re.findall(r"/[a-zA-Z0-9_\-]+", q)
    keep: list[str] = ["/health"]
    for r in routes:
        if r not in keep:
            keep.append(r)
    return keep


def _default_files(goal: str, required_routes: list[str]) -> dict[str, str]:
    extra_route_defs = []
    for r in required_routes:
        if r == "/health":
            continue
        fn_name = re.sub(r"[^a-zA-Z0-9_]", "_", r.strip("/")) or "root"
        extra_route_defs.append(
            f"""@app.get("{r}")
def {fn_name}():
    return jsonify({{"ok": True, "route": "{r}"}})
"""
        )
    extra_route_block = "\n\n".join(extra_route_defs)

    app_py = f"""from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify({{"ok": True, "goal": {json.dumps(goal, ensure_ascii=False)}}})


@app.get("/")
def index():
    return jsonify({{"message": "self-heal web mvp", "goal": {json.dumps(goal, ensure_ascii=False)}}})

{extra_route_block}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
"""
    test_lines = [
        "from app import app",
        "",
        "def test_health_ok():",
        "    c = app.test_client()",
        "    r = c.get('/health')",
        "    assert r.status_code == 200",
        "    data = r.get_json()",
        "    assert data.get('ok') is True",
        "",
    ]
    for r in required_routes:
        if r == "/health":
            continue
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", r.strip("/")) or "root"
        test_lines.extend(
            [
                f"def test_route_{safe}_ok():",
                "    c = app.test_client()",
                f"    r = c.get('{r}')",
                "    assert r.status_code == 200",
                "",
            ]
        )
    return {
        "app.py": app_py,
        "requirements.txt": "flask==3.1.0\npytest==8.3.4\n",
        "test_app.py": "\n".join(test_lines).rstrip() + "\n",
        "Dockerfile": (
            "FROM python:3.12-slim\n"
            "WORKDIR /app\n"
            "COPY requirements.txt /app/requirements.txt\n"
            "RUN pip install --no-cache-dir -r /app/requirements.txt\n"
            "COPY . /app\n"
            "EXPOSE 8000\n"
            'CMD ["python", "app.py"]\n'
        ),
    }


def _generate_initial_files(goal: str, required_routes: list[str]) -> dict[str, str]:
    prompt = (
        "你是資深 Python Web 工程師。請為需求產生最小可運作 Flask 專案。\n"
        "需求："
        + goal
        + f"\n必要路由：{required_routes}\n"
        + "\n請只輸出 JSON 物件，鍵只允許 app.py, requirements.txt, Dockerfile, test_app.py。\n"
        "要求：\n"
        f"- 必須包含這些路由：{required_routes}\n"
        "- 必須提供 pytest 測試檔 test_app.py，至少檢查 /health 回傳 200\n"
        "- Dockerfile 可直接 docker build/run\n"
        "- 不要加入 markdown 或說明文字。"
    )
    try:
        raw = _call_ollama(prompt, timeout=120)
        obj = _extract_first_json_object(raw)
        if not obj:
            return _default_files(goal, required_routes)
        out = _default_files(goal, required_routes)
        for k in ("app.py", "requirements.txt", "Dockerfile", "test_app.py"):
            if isinstance(obj.get(k), str) and obj.get(k).strip():
                out[k] = obj[k]
        return out
    except Exception:
        return _default_files(goal, required_routes)


def _write_files(workdir: Path, files: dict[str, str]) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (workdir / name).write_text(content, encoding="utf-8")


def _run(cmd: list[str], cwd: Path, timeout: int = 120) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
    return p.returncode, out


def _health_check(port: int, routes: list[str], retries: int = 12, sleep_sec: float = 2.0) -> tuple[bool, str]:
    route_list = ["/health"] + [r for r in routes if r != "/health"]
    last_err = ""
    for _ in range(retries):
        all_ok = True
        details: list[str] = []
        for route in route_list:
            url = f"http://127.0.0.1:{port}{route}"
            try:
                r = requests.get(url, timeout=3)
                if r.status_code == 200:
                    details.append(f"{route}:200")
                else:
                    all_ok = False
                    details.append(f"{route}:{r.status_code}")
            except Exception as e:
                all_ok = False
                details.append(f"{route}:ERR:{e}")
        if all_ok:
            return True, " | ".join(details)
        last_err = " | ".join(details)
        time.sleep(sleep_sec)
    return False, last_err


def _repair_files_with_ollama(
    goal: str,
    files: dict[str, str],
    build_log: str,
    test_log: str,
    runtime_log: str,
    required_routes: list[str],
) -> dict[str, str]:
    signature = _classify_error_signature(build_log, test_log, runtime_log)
    memory_ctx = _load_recent_memory_context(goal=goal, error_signature=signature, limit=3)
    prompt = (
        "你是 Python/Docker 除錯工程師。請根據錯誤修正專案檔案。\n"
        "需求：" + goal + "\n"
        f"必要路由：{required_routes}\n"
        f"錯誤特徵：{signature}\n"
        f"{memory_ctx}\n\n"
        "目前檔案如下：\n"
        f"[app.py]\n{files.get('app.py','')}\n\n"
        f"[requirements.txt]\n{files.get('requirements.txt','')}\n\n"
        f"[test_app.py]\n{files.get('test_app.py','')}\n\n"
        f"[Dockerfile]\n{files.get('Dockerfile','')}\n\n"
        "錯誤日誌：\n"
        f"[build_log]\n{build_log[:3000]}\n\n"
        f"[test_log]\n{test_log[:3000]}\n\n"
        f"[runtime_log]\n{runtime_log[:3000]}\n\n"
        "請只輸出 JSON 物件，鍵只允許 app.py, requirements.txt, Dockerfile, test_app.py。"
    )
    raw = _call_ollama(prompt, timeout=150)
    obj = _extract_first_json_object(raw)
    if not obj:
        return files
    patched = dict(files)
    for k in ("app.py", "requirements.txt", "Dockerfile", "test_app.py"):
        if isinstance(obj.get(k), str) and obj[k].strip():
            patched[k] = obj[k]
    return patched


def _build_and_run(workdir: Path, tag: str, container_name: str, port: int, required_routes: list[str]) -> tuple[bool, str, str, str]:
    code, build_out = _run(["docker", "build", "-t", tag, "."], cwd=workdir, timeout=420)
    if code != 0:
        return False, build_out, "", ""

    test_cmd = ["docker", "run", "--rm", "--entrypoint", "python", tag, "-m", "pytest", "-q"]
    tcode, test_out = _run(test_cmd, cwd=workdir, timeout=180)
    if tcode != 0:
        return False, build_out, test_out, ""

    code, run_out = _run(
        ["docker", "run", "-d", "--rm", "--name", container_name, "-p", f"{port}:8000", tag],
        cwd=workdir,
        timeout=60,
    )
    if code != 0:
        return False, build_out, test_out, run_out
    ok, health_msg = _health_check(port=port, routes=required_routes, retries=12, sleep_sec=2.0)
    log_code, logs = _run(["docker", "logs", container_name], cwd=workdir, timeout=60)
    _run(["docker", "rm", "-f", container_name], cwd=workdir, timeout=30)
    runtime_log = (health_msg + "\n\n" + (logs if log_code == 0 else "")).strip()
    return ok, build_out, test_out, runtime_log


def run_self_heal(goal: str, max_rounds: int = 3, skip_docker: bool = False) -> dict[str, Any]:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / f"run_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    required_routes = _infer_required_routes(goal)
    files = _generate_initial_files(goal, required_routes)
    rounds: list[dict[str, Any]] = []

    if skip_docker:
        _write_files(run_dir, files)
        report = {
            "ok": True,
            "mode": "skip_docker",
            "goal": goal,
            "required_routes": required_routes,
            "rounds": 0,
            "run_dir": str(run_dir),
        }
        (run_dir / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    ok = False
    final_build = ""
    final_test = ""
    final_runtime = ""
    learned_entries: list[dict[str, Any]] = []
    for i in range(1, max(1, max_rounds) + 1):
        _write_files(run_dir, files)
        tag = f"jarvis-self-heal:{ts}-{i}"
        name = f"jarvis_self_heal_{ts}_{i}"
        port = random.randint(18080, 18999)
        step = {"round": i, "tag": tag, "container": name, "port": port}
        try:
            ok, build_log, test_log, runtime_log = _build_and_run(run_dir, tag, name, port, required_routes=required_routes)
        except Exception as e:
            ok, build_log, test_log, runtime_log = False, "", "", f"Exception: {e}"
        final_build, final_test, final_runtime = build_log, test_log, runtime_log
        step["ok"] = ok
        step["build_log_tail"] = build_log[-1200:]
        step["test_log_tail"] = test_log[-1200:]
        step["runtime_log_tail"] = runtime_log[-1200:]
        rounds.append(step)
        if ok:
            break
        try:
            before = dict(files)
            files = _repair_files_with_ollama(goal, files, build_log, test_log, runtime_log, required_routes=required_routes)
            changed = [k for k in files.keys() if before.get(k, "") != files.get(k, "")]
            learned_entries.append(
                {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "goal": goal,
                    "round": i,
                    "error_signature": _classify_error_signature(build_log, test_log, runtime_log),
                    "changed_files": changed,
                    "build_log_tail": build_log[-800:],
                    "test_log_tail": test_log[-800:],
                    "runtime_log_tail": runtime_log[-800:],
                    "final_ok": False,  # filled after loop
                }
            )
        except Exception as e:
            step["repair_error"] = str(e)
            break

    # persist repair memory for future self-healing rounds
    for e in learned_entries:
        e["final_ok"] = bool(ok)
        try:
            _append_memory_jsonl(e)
            _chroma_add_memory(e)
        except Exception:
            pass

    report = {
        "ok": ok,
        "goal": goal,
        "required_routes": required_routes,
        "rounds": len(rounds),
        "run_dir": str(run_dir),
        "final_build_log_tail": final_build[-1500:],
        "final_test_log_tail": final_test[-1500:],
        "final_runtime_log_tail": final_runtime[-1500:],
        "memory_entries_written": len(learned_entries),
        "history": rounds,
    }
    (run_dir / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_lines = [
        "# Self-Heal Web Loop Report",
        "",
        f"- goal: {goal}",
        f"- ok: {ok}",
        f"- rounds: {len(rounds)}",
        f"- run_dir: {run_dir}",
        "",
    ]
    for r in rounds:
        md_lines.extend(
            [
                f"## Round {r.get('round')}",
                f"- ok: {r.get('ok')}",
                f"- port: {r.get('port')}",
                "",
                "### build log tail",
                "```",
                str(r.get("build_log_tail", "")),
                "```",
                "",
                "### test log tail",
                "```",
                str(r.get("test_log_tail", "")),
                "```",
                "",
                "### runtime log tail",
                "```",
                str(r.get("runtime_log_tail", "")),
                "```",
                "",
            ]
        )
    (run_dir / "report.md").write_text("\n".join(md_lines), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Jarvis Self-Heal Web Loop MVP")
    parser.add_argument("--goal", required=True, help="一句話需求，例如：做一個可上傳檔案的 Flask 網頁")
    parser.add_argument("--max-rounds", type=int, default=3, help="最大修復輪數")
    parser.add_argument("--skip-docker", action="store_true", help="跳過 docker build/run（僅產生檔案）")
    args = parser.parse_args()

    report = run_self_heal(goal=args.goal, max_rounds=args.max_rounds, skip_docker=args.skip_docker)
    # Windows cp950 console may fail on uncommon unicode; keep CLI output ASCII-safe.
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())


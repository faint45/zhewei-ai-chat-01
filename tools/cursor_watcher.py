"""
築未科技大腦 - Cursor 全軟體運行監聽
從 Cursor 的 state.vscdb 擷取 aiService.prompts（用戶提問）與 generations，
將「每個運行項目」轉為範本寫入知識庫。可排程或背景執行。
"""
import hashlib
import json
import os
import shutil
import sqlite3
import time
from pathlib import Path

from brain_data_config import CURSOR_WATCHER_STATE, LOG_DIR

CURSOR_STATE_PATH = Path(os.environ.get("APPDATA", "")) / "Cursor" / "User" / "workspaceStorage"
WATCHER_STATE = CURSOR_WATCHER_STATE
WATCH_LOG = LOG_DIR / "cursor_watcher.log"


def _log(msg: str):
    try:
        with open(WATCH_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass


def _load_last_state() -> dict:
    if not WATCHER_STATE.exists():
        return {"prompts_seen": [], "generations_seen": [], "workspaces": {}}
    try:
        with open(WATCHER_STATE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"prompts_seen": [], "generations_seen": [], "workspaces": {}}


def _save_state(state: dict):
    try:
        with open(WATCHER_STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=0)
    except Exception as e:
        _log(f"save_state err: {e}")


def _read_db_safe(db_path: Path):
    """讀取 state.vscdb，若被鎖則複製到 temp 再讀"""
    prompts, generations = [], []
    try:
        conn = sqlite3.connect(str(db_path), timeout=2)
        r = conn.execute("SELECT value FROM ItemTable WHERE key='aiService.prompts'").fetchone()
        if r:
            prompts = json.loads(r[0]) if r[0] else []
        r = conn.execute("SELECT value FROM ItemTable WHERE key='aiService.generations'").fetchone()
        if r:
            generations = json.loads(r[0]) if r[0] else []
        conn.close()
    except sqlite3.OperationalError:
        # 被 Cursor 鎖定，複製到 temp 再讀
        try:
            from brain_data_config import TEMP_DIR
            copy_path = TEMP_DIR / "cursor_state_copy.vscdb"
            shutil.copy2(db_path, copy_path)
            conn = sqlite3.connect(str(copy_path))
            r = conn.execute("SELECT value FROM ItemTable WHERE key='aiService.prompts'").fetchone()
            if r:
                prompts = json.loads(r[0]) if r[0] else []
            r = conn.execute("SELECT value FROM ItemTable WHERE key='aiService.generations'").fetchone()
            if r:
                generations = json.loads(r[0]) if r[0] else []
            conn.close()
            copy_path.unlink(missing_ok=True)
        except Exception as e:
            _log(f"read_db copy fallback err: {e}")
    except Exception as e:
        _log(f"read_db err: {e}")
    return prompts, generations


def _add_to_brain(text: str, source: str = "Cursor 運行"):
    try:
        from brain_knowledge import add
        add(text, source=source, metadata={"type": "cursor_run"})
    except Exception as e:
        _log(f"add_to_brain err: {e}")


def _hash_prompt(p: dict) -> str:
    t = p.get("text", "") or ""
    ct = str(p.get("commandType", ""))
    return hashlib.md5((t + "|" + ct).encode("utf-8")).hexdigest()


def _hash_gen(g: dict) -> str:
    uid = g.get("generationUUID", "") or ""
    ts = str(g.get("unixMs", ""))
    return hashlib.md5((uid + "|" + ts).encode("utf-8")).hexdigest()


def run_once() -> dict:
    """
    執行一輪：掃描所有 workspace 的 state.vscdb，擷取新增的 prompts 與 generations，
    寫入知識庫。回傳統計。
    """
    stats = {"prompts_added": 0, "generations_added": 0, "workspaces": 0}
    if not CURSOR_STATE_PATH.exists():
        _log("Cursor workspaceStorage not found")
        return stats

    state = _load_last_state()
    seen_prompts = set(state.get("prompts_seen", []))
    seen_gens = set(state.get("generations_seen", []))

    for ws_dir in CURSOR_STATE_PATH.iterdir():
        if not ws_dir.is_dir():
            continue
        db_path = ws_dir / "state.vscdb"
        if not db_path.exists():
            continue
        stats["workspaces"] += 1
        prompts, generations = _read_db_safe(db_path)
        for p in prompts if isinstance(prompts, list) else []:
            if not isinstance(p, dict):
                continue
            txt = (p.get("text") or "").strip()
            if len(txt) < 5:
                continue
            h = _hash_prompt(p)
            if h in seen_prompts:
                continue
            seen_prompts.add(h)
            template = f"【Cursor 運行】用戶需求: {txt[:800]}"
            _add_to_brain(template)
            stats["prompts_added"] += 1
            _log(f"new prompt: {txt[:60]}...")
        for g in generations if isinstance(generations, list) else []:
            if not isinstance(g, dict):
                continue
            h = _hash_gen(g)
            if h in seen_gens:
                continue
            seen_gens.add(h)
            desc = (g.get("textDescription") or "").strip()
            gtype = g.get("type", "")
            if desc or gtype:
                template = f"【Cursor 運行】AI 生成: type={gtype} | {desc[:500]}"
                if len(template) > 50:
                    _add_to_brain(template)
                    stats["generations_added"] += 1

    state["prompts_seen"] = list(seen_prompts)[-2000:]  # 只保留最近 2000
    state["generations_seen"] = list(seen_gens)[-2000:]
    _save_state(state)
    return stats


def run_daemon(interval_sec: int = 120):
    """背景持續監聽；錯誤時延長間隔避免緊密迴圈造成負載"""
    _log("cursor_watcher daemon started")
    while True:
        try:
            s = run_once()
            _log(f"run_once: {s}")
            time.sleep(interval_sec)
        except Exception as e:
            _log(f"run_once err: {e}")
            time.sleep(max(interval_sec, 60))


if __name__ == "__main__":
    import sys
    s = run_once()
    print(json.dumps(s, ensure_ascii=False))
    if "--daemon" in sys.argv:
        run_daemon(int(sys.argv[sys.argv.index("--daemon") + 1]) if len(sys.argv) > sys.argv.index("--daemon") + 1 else 120)

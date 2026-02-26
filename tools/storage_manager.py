"""
築未科技 - 儲存管理
不重要 → 外接 E:  |  重要 → Google 硬碟備份
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os

CONFIG_PATH = Path(__file__).parent / "storage_config.json"
DEFAULT_CONFIG = {
    "move_to_e": ["{home}/Downloads"],
    "backup_to_google": ["{home}/Documents", "{home}/Desktop"],
    "e_drive": "E:",
    "google_drive": "G:/My Drive",
    "google_drive_alt": ["{home}/Google Drive/My Drive", "{home}/OneDrive"],
}


def _user_home():
    return os.environ.get("USERPROFILE", os.path.expanduser("~"))


def _expand(p: str) -> Path:
    home = _user_home()
    return Path(p.replace("{user}", os.path.basename(home)).replace("{home}", home))


def _get_google_path() -> Path:
    cfg = _load_config()
    g = cfg.get("google_drive", "")
    if g:
        p = _expand(g)
        if p.exists():
            return p
    for alt in cfg.get("google_drive_alt", []):
        p = _expand(alt)
        if p.exists():
            return p
    return None


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    c = DEFAULT_CONFIG.copy()
    h = _user_home()
    c["google_drive_alt"] = [x.replace("{user}", os.path.basename(h)).replace("{home}", h) for x in DEFAULT_CONFIG["google_drive_alt"]]
    return c


def _exclude_dev():
    cfg = _load_config()
    exc = set(cfg.get("exclude_dev", []))
    exc |= {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build", ".next"}
    return exc


def _ignore_dev(dirname, names):
    exc = _exclude_dev()
    return [n for n in names if n in exc]


def move_to_e(dry_run: bool = True) -> list[str]:
    """將不重要資料移至 E:（排除開發相關）"""
    cfg = _load_config()
    e = Path(cfg.get("e_drive", "E:"))
    if not e.exists():
        return [f"E: 不存在: {e}"]
    exc = _exclude_dev()
    out = []
    stamp = datetime.now().strftime("%Y%m%d")
    dest_base = e / "moved"
    for src_raw in cfg.get("move_to_e", []):
        src = _expand(src_raw)
        if not src.exists():
            out.append(f"[略] 不存在: {src}")
            continue
        if src.name in exc:
            out.append(f"[略] 開發目錄不轉移: {src.name}")
            continue
        dest = dest_base / stamp / src.name
        if dry_run:
            out.append(f"[預覽] {src} -> {dest} (排除開發相關)")
        else:
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest))
                out.append(f"[完成] {src.name} -> {dest}")
            except Exception as ex:
                out.append(f"[失敗] {src}: {ex}")
    return out


def backup_to_google(dry_run: bool = True) -> list[str]:
    """將重要資料備份至 Google 硬碟（排除開發相關）"""
    g = _get_google_path()
    if not g:
        return ["找不到 Google 硬碟。請安裝 Google Drive 並設定 storage_config.json"]
    cfg = _load_config()
    exc = _exclude_dev()
    out = []
    stamp = datetime.now().strftime("%Y%m%d_backup")
    dest_base = g / "zhewei_backup" / stamp
    for src_raw in cfg.get("backup_to_google", []):
        src = _expand(src_raw)
        if not src.exists():
            out.append(f"[略] 不存在: {src}")
            continue
        if src.is_dir() and src.name in exc:
            out.append(f"[略] 開發目錄不備份: {src.name}")
            continue
        dest = dest_base / src.name
        if dry_run:
            out.append(f"[預覽] {src} -> {dest} (排除 node_modules .git 等)")
        else:
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                if src.is_dir():
                    shutil.copytree(src, dest, dirs_exist_ok=True, ignore=_ignore_dev)
                else:
                    shutil.copy2(src, dest)
                out.append(f"[完成] {src.name} -> {dest}")
            except Exception as ex:
                out.append(f"[失敗] {src}: {ex}")
    return out


def run(dry_run: bool = True):
    print("=== 移至 E: ===")
    for line in move_to_e(dry_run):
        print(line)
    print("\n=== 備份至 Google ===")
    for line in backup_to_google(dry_run):
        print(line)


if __name__ == "__main__":
    import sys
    dry = "--run" not in sys.argv
    if dry:
        print("(預覽模式，加 --run 執行)\n")
    run(dry_run=dry)

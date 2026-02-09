"""
築未科技大腦 - D 槽資料備份
備份 brain_knowledge、CSV、日誌等至 D:\\zhewei_brain_backup
"""
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

try:
    from brain_data_config import (
        BRAIN_DATA_DIR,
        KNOWLEDGE_FILE,
        COST_FILE,
        LEARN_FILE,
        REMOTE_CSV,
        LOG_DIR,
        SELF_LEARN_LOG,
        CHROMA_PATH,
        SESSIONS_FILE,
    )
except ImportError:
    BRAIN_DATA_DIR = Path(os.environ.get("ZHEWEI_BRAIN_DATA_DIR", "D:/zhewei_brain_data"))
    KNOWLEDGE_FILE = BRAIN_DATA_DIR / "brain_knowledge.ndjson"
    COST_FILE = BRAIN_DATA_DIR / "ai_cost_log.json"
    LEARN_FILE = BRAIN_DATA_DIR / "brain_learn.json"
    REMOTE_CSV = BRAIN_DATA_DIR / "zhewei_remote_master.csv"
    LOG_DIR = BRAIN_DATA_DIR / "logs"
    SELF_LEARN_LOG = BRAIN_DATA_DIR / "self_learn_log.ndjson"
    CHROMA_PATH = BRAIN_DATA_DIR / "brain_chroma_db"
    SESSIONS_FILE = BRAIN_DATA_DIR / "brain_sessions.json"

BACKUP_BASE = Path(os.environ.get("ZHEWEI_BACKUP_DIR", "D:/zhewei_brain_backup"))
FILES_TO_BACKUP = [
    KNOWLEDGE_FILE,
    COST_FILE,
    LEARN_FILE,
    REMOTE_CSV,
    SELF_LEARN_LOG,
    SESSIONS_FILE,
]


def backup():
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    dest_dir = BACKUP_BASE / stamp
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for src in FILES_TO_BACKUP:
        if not src.exists():
            continue
        try:
            shutil.copy2(src, dest_dir / src.name)
            copied.append(src.name)
        except Exception as e:
            print(f"備份失敗 {src.name}: {e}")
    if LOG_DIR.exists():
        log_dest = dest_dir / "logs"
        log_dest.mkdir(exist_ok=True)
        for f in LOG_DIR.glob("*"):
            if f.is_file():
                try:
                    shutil.copy2(f, log_dest / f.name)
                    copied.append(f"logs/{f.name}")
                except Exception:
                    pass
    if CHROMA_PATH.exists() and CHROMA_PATH.is_dir():
        chroma_dest = dest_dir / "brain_chroma_db"
        try:
            shutil.copytree(CHROMA_PATH, chroma_dest, dirs_exist_ok=True)
            copied.append("brain_chroma_db/")
        except Exception as e:
            print(f"備份 Chroma 失敗: {e}")
    print(f"備份完成：{dest_dir}，共 {len(copied)} 個項目")
    return dest_dir, copied


if __name__ == "__main__":
    backup()

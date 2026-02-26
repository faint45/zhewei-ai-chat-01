# 築未科技 — 預留最新版、其餘移入新資料夾（E 槽歸檔）
from pathlib import Path
import shutil

from zhewei_archive_config import E_DRIVE_ROOT, LATEST_ROOT, ARCHIVE_ROOT, FOLDERS_TO_ARCHIVE


def main():
    root = Path(E_DRIVE_ROOT)
    archive = Path(ARCHIVE_ROOT)
    latest = Path(LATEST_ROOT)

    if not root.exists():
        print("E 槽不存在，略過。")
        return

    archive.mkdir(parents=True, exist_ok=True)

    for name in FOLDERS_TO_ARCHIVE:
        src = root / name
        if not src.is_dir():
            continue
        if src.resolve() == latest.resolve():
            continue
        dst = archive / name
        if dst.exists():
            dst = archive / f"{name}_歸檔"
        try:
            shutil.move(str(src), str(dst))
            print("已移入歸檔:", name, "->", dst)
        except Exception as e:
            print("移入失敗:", name, e)


if __name__ == "__main__":
    main()

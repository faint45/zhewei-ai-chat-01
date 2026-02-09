# 築未科技 — LAS／點雲整理：同一筆分析所需檔案放一起
# 以整份資料夾移動，不拆開點雲、照片、GPS 軌跡等，一筆分析一資料夾。
from pathlib import Path
import shutil

from point_cloud_config import POINT_CLOUD_ROOT, SOURCES


def main():
    root = Path(POINT_CLOUD_ROOT)
    root.mkdir(parents=True, exist_ok=True)

    for src_path, subfolder_name in SOURCES:
        src = Path(src_path)
        if not src.is_dir():
            continue
        dst = root / subfolder_name
        if dst.exists():
            base, i = subfolder_name, 1
            while dst.exists():
                dst = root / f"{base}_{i}"
                i += 1
        try:
            shutil.move(str(src), str(dst))
            print("已集中（整份分析）:", src.name, "->", dst)
        except Exception as e:
            print("移入失敗:", src, e)


if __name__ == "__main__":
    main()

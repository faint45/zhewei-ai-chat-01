"""
CL3 代碼寫入與配置器 - 自動備份後覆蓋
"""
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class CL3Manager:
    def __init__(self, base_path: str = "D:/Messenger_Project"):
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.backup_dir = self.base_path / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, filename: str) -> Path:
        path = (self.base_path / filename).resolve()
        if not str(path).startswith(str(self.base_path)):
            raise ValueError(f"禁止寫入 base_path 之外: {filename}")
        return path

    def apply_update(self, filename: str, new_code: str) -> str:
        target_path = self._safe_path(filename)

        if target_path.exists():
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{target_path.name}_{ts}.bak"
            shutil.copy2(target_path, backup_path)

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(new_code, encoding="utf-8")
        return f"檔案 {filename} 已更新並備份。"

    def auto_setup(self, libraries: list[str]) -> list[str]:
        results = []
        for lib in libraries:
            print(f"正在配置環境: {lib}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
            results.append(f"{lib} OK")
        return results

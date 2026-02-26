"""
代碼寫入模組 - 將 AI 生成的代碼塊寫入檔案
"""
import os
from pathlib import Path


class CodeWriter:
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path).resolve()

    def _safe_path(self, filename: str) -> Path:
        path = (self.base_path / filename).resolve()
        if not str(path).startswith(str(self.base_path)):
            raise ValueError(f"禁止寫入 base_path 之外: {filename}")
        return path

    def write_to_file(
        self,
        filename: str,
        code_block: str,
        mode: str = "replace",
    ) -> str:
        path = self._safe_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not path.exists():
            path.write_text(code_block, encoding="utf-8")
            return f"已建立新檔案: {filename}"

        if mode == "replace":
            path.write_text(code_block, encoding="utf-8")
            return f"已覆蓋: {filename}"
        elif mode == "append":
            with path.open("a", encoding="utf-8") as f:
                f.write("\n" + code_block)
            return f"已追加至: {filename}"
        else:
            raise ValueError(f"未知模式: {mode}")

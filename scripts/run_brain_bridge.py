"""
啟動 Brain Bridge API（支援專案根目錄或 brain_core 子目錄）
確保 guard_core 等模組可被找到後再啟動 uvicorn。
"""
import os
import sys
from pathlib import Path

# 專案根目錄（本腳本在 scripts/ 下，parent.parent = 根目錄）
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(str(ROOT))

# 若 brain_bridge_fastapi 在 brain_core 子目錄，將 brain_core 加入 path（guard_core 在 ROOT 已可找到）
brain_core_dir = ROOT / "brain_core"
if (brain_core_dir / "brain_bridge_fastapi.py").exists():
    if str(brain_core_dir) not in sys.path:
        sys.path.insert(0, str(brain_core_dir))
app_spec = "brain_bridge_fastapi:app"

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("BRAIN_BRIDGE_PORT", "5100"))
    uvicorn.run(app_spec, host="0.0.0.0", port=port)

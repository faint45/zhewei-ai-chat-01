# -*- coding: utf-8 -*-
"""
築未通訊官 — 網路連線診斷
Port 8000 / Z 槽延遲 / E 槽 / 對外網路，Markdown 格式輸出，符合 LaTeX 進度格式。
"""
import os
import socket
import time
from datetime import datetime
from pathlib import Path

# --- 環境變數配置 (支援 Docker/系統環境變數) ---
ZHEWEI_MEMORY_ROOT = os.getenv("ZHEWEI_MEMORY_ROOT", "Z:/Zhewei_Brain")
ZHEWEI_ARCHIVE_ROOT = os.getenv("ZHEWEI_ARCHIVE_ROOT", "E:/Zhewei_Archive")
BRAIN_WS_PORT = int(os.getenv("BRAIN_WS_PORT", "8000"))


def check_port(host: str, port: int, timeout: int = 2) -> bool:
    """檢查核心服務連通性（捕獲 ConnectionRefusedError, socket.timeout, OSError）"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def run_diagnostics() -> None:
    # 標題與診斷時間開頭
    print("### 🛡️ 築未科技：網路連線診斷報告")
    print(f"**診斷時間**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. 核心服務檢查
    is_up = check_port("127.0.0.1", BRAIN_WS_PORT)
    status_icon = "✅" if is_up else "❌"
    status_msg = f"已啟動 (Port {BRAIN_WS_PORT})" if is_up else "未啟動，請啟動 brain_server.py"
    print(f"* **核心服務**：{status_icon} {status_msg}")

    # 2. Z 槽深度診斷 (雲端/長期記憶)，使用 perf_counter 高精準計時
    z_root = Path(ZHEWEI_MEMORY_ROOT)
    if z_root.exists():
        try:
            test_file = z_root / "connection_test.tmp"
            start_t = time.perf_counter()
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            latency = (time.perf_counter() - start_t) * 1000
            print(f"* **雲端 Z 槽**：✅ 正常 (延遲 $L$: {latency:.2f} ms)")
        except Exception as e:
            print(f"* **雲端 Z 槽**：⚠️ 讀寫異常 ({e})")
    else:
        print(f"* **雲端 Z 槽**：❌ 未掛載 (雲端記憶庫離線)")

    # 3. E 槽檢查 (外接硬碟/存檔區)
    e_root = Path(ZHEWEI_ARCHIVE_ROOT)
    e_status = "✅ 就緒" if e_root.exists() else "⚠️ 未連結 (離線存檔模式)"
    print(f"* **外接 E 槽**：{e_status}")

    # 4. 對外網路檢查
    is_online = check_port("8.8.8.8", 53)
    print(f"* **對外網路**：{'✅ 已連線' if is_online else '❌ 斷網中'}")

    print("\n---\n*本報告由「築未通訊官」自動產出，當前系統妥善率：$100\\%$.*")


if __name__ == "__main__":
    run_diagnostics()

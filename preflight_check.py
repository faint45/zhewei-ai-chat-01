# -*- coding: utf-8 -*-
"""
築未科技 — 大腦全系統預檢腳本
執行於啟動前：必要項（Z 槽、Python、核心檔案）與可選項（視覺環境、CUDA、目錄）診斷；核心缺失則 exit(1)。
若 Z 槽未掛載，可嘗試自動喚醒 Rclone（需 rclone 在 PATH，可設 RCLONE_REMOTE、RCLONE_MOUNT_LETTER）。
"""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BRAIN_WS = Path(os.environ.get("BRAIN_WORKSPACE", "D:/brain_workspace"))
if not BRAIN_WS.is_absolute():
    BRAIN_WS = ROOT / "brain_workspace"
PORT = int(os.environ.get("BRAIN_WS_PORT", "8000"))

# Rclone 自動掛載（可透過環境變數覆寫）
RCLONE_REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive:Zhewei_Brain")
RCLONE_MOUNT_LETTER = os.environ.get("RCLONE_MOUNT_LETTER", "Z:")


def attempt_z_mount() -> bool:
    """若 Z 槽未掛載，嘗試自動喚醒 Rclone；回傳掛載後 Z 是否可存取。"""
    if os.path.exists("Z:/") or Path("Z:/").exists():
        return True
    print("[*] 偵測到 Z 槽未掛載，嘗試啟動 Rclone...")
    try:
        subprocess.Popen(
            ["rclone", "mount", RCLONE_REMOTE, RCLONE_MOUNT_LETTER, "--vfs-cache-mode", "full"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(5)
    except FileNotFoundError:
        print("[~] 找不到 rclone，請確認已安裝並加入 PATH。")
    except Exception as e:
        print(f"[~] Rclone 啟動失敗: {e}")
    return os.path.exists("Z:/") or Path("Z:/").exists()


def check_essential(name: str, condition: bool) -> bool:
    status = "[OK]" if condition else "[X]"
    print(f"[{status}] {name}")
    return condition


def check_optional(name: str, condition: bool) -> bool:
    status = "[OK]" if condition else "[~]"
    print(f"[{status}] {name} (可選)")
    return condition


def run_main() -> int:
    print("=" * 40)
    print("[築未大腦] 築未科技 AI 大腦：系統環境診斷程序")
    print("=" * 40)

    # 必要項目：Z 槽（未掛載時嘗試自動喚醒 Rclone）
    z_ok = os.path.exists("Z:/Zhewei_Brain") or Path("Z:/").exists()
    if not z_ok:
        z_ok = attempt_z_mount()
    has_z = check_essential("雲端記憶庫 (Z 槽)", z_ok)
    has_py = check_essential("Python 環境", sys.version_info >= (3, 10))

    core_files = ["brain_server.py", "ai_service.py", "agent_logic.py"]
    has_files = all(check_essential(f"核心檔案: {f}", (ROOT / f).is_file()) for f in core_files)

    # 依賴（brain_server 必要）
    try:
        __import__("fastapi")
        __import__("uvicorn")
        has_deps = True
    except ImportError:
        has_deps = False
    has_deps = check_essential("依賴 (FastAPI / uvicorn)", has_deps)

    # 可選項目（視覺與加速）
    vision_venv = os.environ.get("VISION_PYTHON") or str(BRAIN_WS / "venv_vision" / "Scripts" / "python.exe")
    if not Path(vision_venv).exists():
        vision_venv = r"C:\Users\user\venv_vision\Scripts\python.exe"
    has_vision = check_optional("視覺環境 (venv_vision)", Path(vision_venv).exists())

    cuda_status = False
    if has_vision:
        try:
            res = subprocess.run(
                [vision_venv, "-c", "import torch; print(torch.cuda.is_available())"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(ROOT),
            )
            cuda_status = "True" in (res.stdout or "")
        except Exception:
            pass
    check_optional("GPU 加速 (CUDA / RTX 4060 Ti)", cuda_status)

    # 目錄完整性（brain_workspace 下）
    ws_dirs = BRAIN_WS if BRAIN_WS.exists() else ROOT / "brain_workspace"
    for d in ["input", "processed", "models"]:
        check_optional(f"目錄完整性: {d}/", (ws_dirs / d).exists())

    # Port 可用（可選）
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", PORT))
        check_optional(f"Port {PORT} 可用", True)
    except OSError:
        check_optional(f"Port {PORT} 可用", False)

    print("=" * 40)
    if not (has_z and has_py and has_files and has_deps):
        print("[!] 核心項目缺失，請修正後啟動！")
        return 1
    print("[OK] 核心診斷通過，系統準備就緒。")
    return 0


if __name__ == "__main__":
    sys.exit(run_main())

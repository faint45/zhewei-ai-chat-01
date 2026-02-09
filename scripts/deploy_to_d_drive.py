# -*- coding: utf-8 -*-
"""
築未科技 — D 槽一鍵部署（資料都放在 D 槽）
執行：於專案根目錄執行 python scripts/deploy_to_d_drive.py
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

D_ROOT = Path(r"D:\brain_workspace")
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DIRS = [
    "input", "processed", "models", "output", "cache",
    "Reports", "Rules", "Contract", "static"
]
CORE_FILES = ["brain_server.py", "agent_logic.py", "ai_service.py", "agent_tools.py", "report_generator.py"]


def main():
    print("築未科技 — D 槽部署")
    print(f"專案目錄: {PROJECT_ROOT}")
    print(f"目標目錄: {D_ROOT}")
    print()

    # 1. 建立 D 槽根目錄與子目錄
    for d in DIRS:
        p = D_ROOT / d
        p.mkdir(parents=True, exist_ok=True)
        print(f"[+] 建立 {p}")

    # 2. 複製 brain_workspace 內容到 D 槽
    src_bw = PROJECT_ROOT / "brain_workspace"
    if src_bw.exists():
        for f in src_bw.rglob("*"):
            if f.is_file():
                rel = f.relative_to(src_bw)
                dest = D_ROOT / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
        print(f"[+] 已同步 brain_workspace -> {D_ROOT}")
    else:
        print(f"[!] 未找到 {src_bw}")

    # 3. 複製主腦核心腳本到 D 槽
    for f in CORE_FILES:
        src = PROJECT_ROOT / f
        if src.exists():
            shutil.copy2(src, D_ROOT / f)
            print(f"[+] 複製 {f}")

    # 4. 建立 venv_vision（Python 3.12）
    venv = D_ROOT / "venv_vision"
    venv_py = venv / "Scripts" / "python.exe" if (venv / "Scripts").exists() else venv / "bin" / "python"
    if not venv_py.exists():
        print("[*] 建立 venv_vision (Python 3.12)...")
        try:
            for cmd in ["py -3.12", "py", "python"]:
                r = subprocess.run(
                    f"{cmd} -m venv {venv}".split(),
                    cwd=str(D_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if r.returncode == 0:
                    break
            pip = venv / "Scripts" / "pip.exe" if (venv / "Scripts").exists() else venv / "bin" / "pip"
            if pip.exists():
                subprocess.run([str(pip), "install", "-q", "ultralytics", "torch"], timeout=300, capture_output=True)
            print("[+] venv_vision 建立並安裝 ultralytics, torch")
        except Exception as e:
            print(f"[!] venv_vision 建立失敗: {e}")
    else:
        print("[+] venv_vision 已存在")

    # 5. 寫入 .env 至專案根目錄
    env_path = PROJECT_ROOT / ".env"
    env_block = "\n# D 槽資料（部署腳本寫入）\nBRAIN_WORKSPACE=" + str(D_ROOT) + "\nZHEWEI_MEMORY_ROOT=" + str(D_ROOT)
    if not env_path.exists():
        env_path.write_text("# 築未科技 - 資料都放在 D 槽\nBRAIN_WORKSPACE=" + str(D_ROOT) + "\nZHEWEI_MEMORY_ROOT=" + str(D_ROOT), encoding="utf-8")
        print("[+] 已建立 .env（BRAIN_WORKSPACE、ZHEWEI_MEMORY_ROOT 指向 D 槽）")
    else:
        content = env_path.read_text(encoding="utf-8", errors="replace")
        if "ZHEWEI_MEMORY_ROOT=" + str(D_ROOT) not in content:
            with open(env_path, "a", encoding="utf-8") as f:
                f.write(env_block)
            print("[+] 已追加 .env 之 D 槽設定")

    print()
    print("部署完成。資料目錄：", D_ROOT)
    print("  input, processed, models, output, cache, Reports, Rules, Contract 均已就緒。")
    print("啟動方式：")
    print(f"  cd {D_ROOT}")
    print("  .\\start_all.ps1")
    print("或從專案目錄：python brain_server.py（.env 已設 D 槽）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
築未科技 — 大腦守護服務（24/7）
每 10 分鐘檢查 Z 槽、brain_server、site_monitor、CUDA；服務停止則自動重啟；可選 AI 聯合修復寫入 Z 槽 Health_Report.md。
"""
import asyncio
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BRAIN_WS = Path(os.environ.get("BRAIN_WORKSPACE", "D:/brain_workspace"))
if not BRAIN_WS.is_absolute():
    BRAIN_WS = ROOT / "brain_workspace"
LOG_FILE = Path(os.environ.get("BRAIN_LOG_FILE", "D:/brain_workspace/brain_system.log"))
Z_ROOT = Path(os.environ.get("ZHEWEI_MEMORY_ROOT", "Z:/Zhewei_Brain"))
REPAIR_LOG = Z_ROOT / "Reports" / "Health_Report.md"

# 監控目標：(顯示名稱, 腳本名, 工作目錄)
WATCH_SERVICES = [
    ("BrainServer", "brain_server.py", ROOT),
    ("SiteMonitor", "site_monitor.py", BRAIN_WS if BRAIN_WS.exists() else ROOT / "brain_workspace"),
]
# 視覺環境 Python（優先環境變數，其次 BRAIN_WORKSPACE/venv_vision）
VISION_PYTHON = os.environ.get("VISION_PYTHON")
if not VISION_PYTHON:
    vp = BRAIN_WS / "venv_vision" / "Scripts" / "python.exe"
    if not vp.exists():
        vp = BRAIN_WS / "venv_vision" / "bin" / "python"
    VISION_PYTHON = str(vp) if vp.exists() else r"C:\Users\user\venv_vision\Scripts\python.exe"

# 日誌：寫入 D 槽並輸出主控台
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
logger.addHandler(logging.StreamHandler())
try:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
except Exception:
    pass


def log_event(msg: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    s = f"[{now}] {msg}"
    print(s)
    logger.info(msg)


def check_z_drive() -> bool:
    """檢查雲端 Z 槽是否掛載"""
    return Path("Z:/").exists() or Z_ROOT.exists()


def is_process_running(script_name: str) -> bool:
    """檢查該 Python 腳本是否在執行（依指令列是否含腳本名）"""
    try:
        out = subprocess.check_output(
            'wmic process where "name=\'python.exe\'" get commandline 2>nul',
            shell=True,
            encoding="utf-8",
            errors="replace",
        )
        return script_name in (out or "")
    except Exception:
        try:
            out = subprocess.check_output(
                'tasklist /FI "IMAGENAME eq python.exe" /V',
                shell=True,
                encoding="cp950",
                errors="replace",
            )
            return script_name in (out or "")
        except Exception:
            return False


def restart_service(script_name: str, cwd: Path) -> None:
    """於指定目錄重啟服務（新視窗）"""
    log_event(f"⚠️ 偵測到 {script_name} 停止，正在重啟...")
    script_path = cwd / script_name
    if not script_path.exists():
        log_event(f"❌ 找不到腳本: {script_path}")
        return
    try:
        subprocess.Popen(
            [sys.executable, script_name],
            cwd=str(cwd),
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
        )
        log_event(f"✅ 已啟動: {script_name}")
    except Exception as e:
        log_event(f"❌ 重啟失敗: {e}")


async def ai_joint_repair(error_msg: str, gemini_service) -> str:
    """AI 聯合修復：依日誌產出對策並寫入 Z 槽 Health_Report.md"""
    try:
        from ai_service import GeminiService
        prompt = f"系統偵測到以下故障：{error_msg}。請根據日誌內容提供簡短修復步驟（條列）。"
        log_tail = ""
        if LOG_FILE.exists():
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                log_tail = "".join(f.readlines()[-20:])
        repair_advice = await gemini_service.chat([{"role": "user", "content": f"{prompt}\n\n日誌內容：\n{log_tail}"}])
        REPAIR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(REPAIR_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n\n### 🛠️ AI 自動修復報告 - {datetime.now()}\n{repair_advice}\n---")
        log_event("✅ AI 修復報告已寫入 Z 槽 Health_Report.md")
        return repair_advice
    except Exception as e:
        log_event(f"❌ AI 修復失敗: {e}")
        return ""


def monitor_loop(enable_ai_repair: bool = False) -> None:
    """主迴圈：每 10 分鐘檢查 Z 槽、服務、CUDA；服務停止則重啟；可選觸發 AI 修復"""
    gemini = None
    if enable_ai_repair:
        try:
            from ai_service import GeminiService
            gemini = GeminiService()
        except Exception as e:
            log_event(f"⚠️ 無法載入 Gemini，AI 修復關閉: {e}")
            enable_ai_repair = False

    while True:
        log_event("🔍 開始每 10 分鐘系統健康檢查...")
        errors = []

        if not check_z_drive():
            log_event("❌ Z 槽斷線，請確認 Rclone 狀態。")
            errors.append("Z 槽未掛載")
        else:
            log_event("  ✅ Z 槽正常")

        for name, script, cwd in WATCH_SERVICES:
            if not (cwd / script).exists():
                continue
            if not is_process_running(script):
                restart_service(script, cwd)
                errors.append(f"{name}({script}) 已重啟")
        if not errors:
            log_event("  ✅ 核心服務運行中")

        try:
            r = subprocess.run(
                [VISION_PYTHON, "-c", "import torch; print(torch.cuda.is_available())"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if "True" not in (r.stdout or ""):
                log_event("❌ GPU 加速失效，必要時重啟顯卡驅動。")
                errors.append("CUDA 不可用")
        except FileNotFoundError:
            log_event("⚠️ 未找到視覺環境 Python，跳過 CUDA 檢查")
        except Exception as e:
            log_event(f"❌ 無法呼叫視覺環境: {e}")
            errors.append("視覺環境異常")

        if errors and enable_ai_repair and gemini:
            asyncio.run(ai_joint_repair("；".join(errors), gemini))

        log_event("✅ 檢查完成，下次 10 分鐘後執行。")
        time.sleep(600)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="築未大腦守護服務")
    p.add_argument("--ai-repair", action="store_true", help="啟用 AI 聯合修復（需 GEMINI_API_KEY）")
    args = p.parse_args()
    log_event("🛡️ 築未大腦守護服務啟動")
    monitor_loop(enable_ai_repair=args.ai_repair)

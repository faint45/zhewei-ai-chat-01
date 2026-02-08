# -*- coding: utf-8 -*-
import os
import subprocess
import sys
from pathlib import Path

def check_status(name, condition):
    """Check status and return result"""
    status = "[OK]" if condition else "[FAIL]"
    try:
        print(f"{status} {name}")
    except UnicodeEncodeError:
        print(f"{status} {name.encode('ascii', 'ignore').decode('ascii')}")
    return condition

def run_diagnostics():
    """Run system diagnostics"""
    print("="*50)
    print("Zhewei Brain: Startup Diagnostics")
    print("="*50)
    print()

    # 1. Check Z drive (Google Drive via Rclone)
    z_drive = check_status("Cloud Storage (Z: Drive)", os.path.exists("Z:/"))

    # 2. Check vision environment (Python 3.12)
    vision_venv = Path(r"C:\Users\user\venv_vision\Scripts\python.exe")
    venv_exists = check_status("Vision Environment (venv_vision)", vision_venv.exists())

    # 3. Check GPU acceleration
    cuda_status = False
    if venv_exists:
        try:
            cmd = [str(vision_venv), "-c", "import torch; print(torch.cuda.is_available())"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            cuda_status = check_status("GPU Acceleration (CUDA)", "True" in res.stdout)
        except Exception as e:
            print(f"[WARNING] CUDA check failed: {e}")
            check_status("GPU Acceleration (CUDA)", False)
    else:
        check_status("GPU Acceleration (CUDA)", False)

    # 4. Check Python environment
    python_exists = check_status("Python Environment", True)

    # 5. Check required files
    required_files = ["brain_server.py", "ai_service.py", "website_server.py"]
    files_exist = all([check_status(f"File Check: {f}", os.path.exists(f)) for f in required_files])

    # 6. Check directory integrity (optional)
    optional_paths = ["input", "processed", "models"]
    optional_paths_status = all([check_status(f"Directory Check: {p}", os.path.exists(p)) for p in optional_paths])

    print()
    print("-"*30)

    # Required items check
    if not (z_drive and python_exists and files_exist):
        print("[ERROR] Diagnostics failed: Please fix [FAIL] items above before starting.")
        print()
        print("Tips:")
        if not z_drive:
            print("  * Z: drive not mounted, please run Rclone mount script")
        if not files_exist:
            print("  * Required files missing, please check file existence")
        return False

    # Optional items check
    if not optional_paths_status:
        print("[WARNING] Some optional directories missing, but core functions not affected")

    # GPU check (optional)
    if not cuda_status and venv_exists:
        print("[WARNING] CUDA not enabled, AI vision features will be limited")

    print()
    print("[SUCCESS] All systems ready, starting brain...")
    print("="*50)
    return True

if __name__ == "__main__":
    try:
        if not run_diagnostics():
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error during diagnostics: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

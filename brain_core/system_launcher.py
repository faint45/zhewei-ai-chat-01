"""
系統啟動器 - Ollama + 戰情看板初始化
"""
import os
import subprocess
import sys
import time

OLLAMA_OK = True


def initialize_system():
    global OLLAMA_OK
    print("[系統] CL3 初始化...")

    os.system("taskkill /F /IM ollama.exe /T >nul 2>&1")
    os.system('taskkill /F /IM "ollama runner.exe" /T >nul 2>&1')
    time.sleep(1)

    os.environ["OLLAMA_GPU_OVERHEAD"] = "512"
    os.environ["OLLAMA_NUM_PARALLEL"] = "1"
    os.environ["OLLAMA_CONTEXT_LENGTH"] = "4096"

    print("[系統] 啟動 Ollama...")
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)
    except FileNotFoundError:
        OLLAMA_OK = False
        print("[警告] 找不到 ollama，請確認已安裝並加入 PATH")
        print("  下載: https://ollama.com")

    print("[系統] 啟動戰情看板...")
    try:
        subprocess.Popen(
            [sys.executable, "messenger_dashboard.py"],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
    except Exception as e:
        print(f"[警告] 戰情看板啟動失敗: {e}")

    print("[系統] 啟動 Discord 傳令兵...")
    try:
        subprocess.Popen(
            [sys.executable, "zhewei_guard.py"],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
    except Exception as e:
        print(f"[警告] Discord 傳令兵啟動失敗（需設定 DISCORD_BOT_TOKEN）: {e}")


def start_commander():
    initialize_system()
    print("\n" + "=" * 50)
    print(" 智慧管理中樞 - 系統已啟動")
    print(" 模式: 本地對話 / 數據觀測")
    print("=" * 50)
    if OLLAMA_OK:
        subprocess.run(["ollama", "run", "gemma3:4b"])
    else:
        print("Ollama 未就緒，請手動執行: ollama run gemma3:4b")
        try:
            input("按 Enter 結束...")
        except EOFError:
            pass


if __name__ == "__main__":
    try:
        start_commander()
    except KeyboardInterrupt:
        print("\n[系統] 關閉中...")

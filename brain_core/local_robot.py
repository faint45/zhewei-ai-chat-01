"""
築未科技大腦 — 本地機器人入口
預設開啟圖形介面（chat_gui）；加 --cli 則為命令列對話，一律使用 guard_core 完整大腦邏輯。
"""
import os
import sys
from pathlib import Path

BASE = Path(__file__).parent.resolve()
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
os.chdir(BASE)

# 讀取環境變數：專案 .env + 使用者 ~/.openclaw/.env
try:
    from dotenv import load_dotenv
    load_dotenv()
    user_env = Path.home() / ".openclaw" / ".env"
    if user_env.exists():
        load_dotenv(user_env, override=True)
except ImportError:
    pass

# 確保本地機器人模式開啟（圖形介面會讀此變數）
os.environ.setdefault("ZHEWEI_LOCAL_ROBOT", "1")


def cli_loop():
    from guard_core import process_message
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
    user_id = "local"
    print("\n築未科技大腦 — 本地機器人（CLI）")
    print("輸入 exit 或 quit 結束\n")
    while True:
        try:
            line = input("你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line.lower() in ("exit", "quit", ""):
            break
        result, msg_type = process_message(line, user_id, base_url, model)
        print(f"築未 > {result}\n  └ {msg_type}\n")
    print("已結束。")


def main():
    if "--cli" in sys.argv or "-c" in sys.argv:
        cli_loop()
        return
    from chat_gui import ChatGUI
    app = ChatGUI()
    app.run()


if __name__ == "__main__":
    main()

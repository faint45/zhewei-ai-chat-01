"""
築未科技 - 萬能助理 Discord 傳令兵
與大腦橋接功能一致：天氣、時間、授權、Agent、開發：協議
"""
import os
import csv
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import discord
except ImportError:
    print("請安裝: pip install discord.py requests python-dotenv")
    sys.exit(1)

BASE_DIR = Path(__file__).parent.resolve()
from brain_data_config import REMOTE_CSV as CSV_FILE
IDLE_EXIT_MINUTES = int(os.environ.get("IDLE_EXIT_MINUTES", "0") or "0")

# 共用邏輯（與大腦橋接一致）
from guard_core import (
    process_message,
    is_agent_task as _is_agent_task,
    run_agent as _run_agent,
    test_execution,
    call_premium_strategist,
    STRATEGIST_CONFIG,
)

_last_activity: float = 0


def _log_csv(user_id: str, cmd: str, result: str, status: str):
    exists = CSV_FILE.exists()
    with open(CSV_FILE, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["時間", "用戶ID", "指令", "結果摘要", "狀態"])
        w.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_id,
            (cmd or "")[:100],
            (result or "")[:200],
            status,
        ])


class ZheWeiGuard(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.environ.get("OLLAMA_MODEL", "gemma3:4b")

    async def on_ready(self):
        global _last_activity
        _last_activity = datetime.now().timestamp()
        print("【築未萬能助理】已連線 Discord")
        print(f"  大腦: {self.base_url} / {self.model}")
        if IDLE_EXIT_MINUTES > 0:
            print(f"  閒置 {IDLE_EXIT_MINUTES} 分鐘後自動關閉以省資源")
            self.loop.create_task(self._idle_checker())

    async def _idle_checker(self):
        import asyncio
        while not self.is_closed():
            await asyncio.sleep(300)
            if IDLE_EXIT_MINUTES <= 0 or self.is_closed():
                break
            idle = (datetime.now().timestamp() - _last_activity) / 60
            if idle >= IDLE_EXIT_MINUTES:
                print(f"[省資源] 已閒置 {idle:.0f} 分鐘，自動關閉。需要時請重新啟動。")
                await self.close()
                return

    async def on_message(self, message):
        global _last_activity
        _last_activity = datetime.now().timestamp()
        if message.author.bot:
            return
        content = (message.content or "").strip()
        if not content:
            return

        user_id = str(message.author.id)
        status_msg = await message.channel.send("【萬能助理分析中】請稍候...")

        # 與大腦橋接邏輯一致（含 開發：、授權、Agent、天氣、AI 對話）
        result, msg_type = process_message(content, user_id, self.base_url, self.model)

        try:
            if len(result) > 1900:
                await status_msg.edit(content=f"【萬能助理】\n{result[:1900]}\n…(省略)")
                await message.channel.send(f"```\n{result[1900:3800]}\n```")
            else:
                await status_msg.edit(content=f"【萬能助理】\n{result}")
        except Exception:
            await message.channel.send(f"【萬能助理】\n{result}")

        _log_csv(user_id, content, result[:100], "完成")


def main():
    import time
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not token or token == "your-discord-bot-token":
        print("請在 .env 設定 DISCORD_BOT_TOKEN")
        sys.exit(1)

    os.chdir(BASE_DIR)
    intents = discord.Intents.default()
    intents.message_content = True

    # 未取得授權前不可離線：斷線自動重連，持續運行（指數退避減輕持續失敗時的負載）
    base_delay = int(os.environ.get("DISCORD_RETRY_DELAY", "30"))
    max_delay = int(os.environ.get("DISCORD_RETRY_MAX_DELAY", "300"))
    retry_count = 0
    while True:
        try:
            client = ZheWeiGuard(intents=intents)
            client.run(token)
        except discord.LoginFailure as e:
            print(f"[嚴重] Token 無效，請檢查 .env：{e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("使用者中斷，結束。")
            break
        except Exception as e:
            retry_count += 1
            delay = min(max_delay, base_delay * (2 ** min(retry_count - 1, 5)))
            print(f"[斷線] {e}")
            print(f"  {delay} 秒後自動重連（第 {retry_count} 次）...")
            time.sleep(delay)
            continue
        # 正常關閉（如 IDLE_EXIT）則結束
        break


if __name__ == "__main__":
    main()

import discord
import os, subprocess, sys

# 憑證配置
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
AUTHORIZED_USER_ID = "962679936978657280"
BASE_DIR = r"C:\Users\user\Desktop\zhe-wei-tech"

class ShadowCommander(discord.Client):
    async def on_ready(self):
        print(f"✅ 【影子指揮部】已成功連線！")
        print(f"🤖 機器人：{self.user}")
        print(f"📍 節點：民雄主機 (4060 Ti)")

    async def on_message(self, message):
        if str(message.author.id) != AUTHORIZED_USER_ID: return
        if message.author.bot: return

        cmd = message.content.lower()
        if cmd == "/start":
            await message.channel.send("🚀 **[影子啟動]** 正在執行流水線...")
            subprocess.Popen(["python", "cl3_shadow_pipeline.py"], cwd=BASE_DIR)
        elif cmd == "/cleanup":
            os.system("taskkill /F /IM ollama.exe /T >nul 2>&1")
            await message.channel.send("✅ 4060 Ti 資源已釋放。")

if __name__ == "__main__":
    os.makedirs(BASE_DIR, exist_ok=True)
    os.chdir(BASE_DIR)
    intents = discord.Intents.all()
    client = ShadowCommander(intents=intents)
    try:
        client.run(TOKEN)
    except Exception as e:
        print(f"❌ 啟動失敗：{e}")

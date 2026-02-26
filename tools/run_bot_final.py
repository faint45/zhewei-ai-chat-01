import discord
import os, subprocess, asyncio

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
AUTHORIZED_USER_ID = "962679936978657280"
BASE_DIR = r"C:\Users\user\Desktop\zhe-wei-tech"
OUTPUT_PATH = "D:/Messenger_Assets"

class ShadowMaster(discord.Client):
    async def on_ready(self):
        print(f"✅ 【影子指揮部】實戰模式已就緒。")

    async def on_message(self, message):
        if str(message.author.id) != AUTHORIZED_USER_ID: return
        if message.author.bot: return

        cmd = message.content.strip().lower()

        # 1. 啟動穿透任務
        if cmd.startswith("/start"):
            target_url = message.content.split(" ")[1] if len(message.content.split(" ")) > 1 else "未提供網址"
            await message.channel.send(f"🚀 **[啟動穿透]** 目標：`{target_url}`\n正在喚醒 4060 Ti 流水線並準備預覽...")
            subprocess.Popen(["python", "cl3_shadow_pipeline.py"], cwd=BASE_DIR)
            asyncio.create_task(self.auto_preview(message.channel))

        # 2. 物理釋放資源
        elif cmd == "/cleanup":
            os.system("taskkill /F /IM python.exe /T >nul 2>&1")
            await message.channel.send("🧹 **[清理完畢]** 4060 Ti 顯存已物理釋放。")

    async def auto_preview(self, channel):
        await asyncio.sleep(20) # 等待數據落地
        preview = os.path.join(OUTPUT_PATH, "preview.mp4")
        if os.path.exists(preview):
            await channel.send("🎞️ **預覽回傳**：解密成功，畫質確認中：", file=discord.File(preview))
        else:
            await channel.send("⚠️ 預覽生成超時，請檢查 D:/Messenger_Assets 狀態。")

os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(OUTPUT_PATH, exist_ok=True)
client = ShadowMaster(intents=discord.Intents.all())
client.run(TOKEN)

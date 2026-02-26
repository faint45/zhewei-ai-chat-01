import discord
import os, subprocess, asyncio, glob

# ================= 最終實戰配置 =================
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
AUTHORIZED_USER_ID = "962679936978657280"
OUTPUT_DIR = "D:/Messenger_Assets"
# ===============================================

class LiveViewCommander(discord.Client):
    async def on_ready(self):
        print(f"✅ 【影子指揮部】直連觀看模式已上線。")
        print(f"📍 民雄 4060 Ti 節點待命中...")

    async def on_message(self, message):
        if str(message.author.id) != AUTHORIZED_USER_ID: return
        if message.author.bot: return

        cmd = message.content.strip().lower()

        if cmd.startswith("/start"):
            await message.channel.send("📡 **[啟動穿透]** 正在解密串流，稍後將自動回傳預覽影片...")
            # 觸發物理流水線
            subprocess.Popen(["python", "cl3_shadow_pipeline.py"], cwd=r"C:\Users\user\Desktop\zhe-wei-tech")
            # 開啟檔案監聽
            asyncio.create_task(self.watch_for_video(message.channel))

    async def watch_for_video(self, channel):
        # 循環檢查是否有新影片生成
        for _ in range(30): # 最多等待 60 秒
            await asyncio.sleep(2)
            files = glob.glob(os.path.join(OUTPUT_DIR, "*.mp4"))
            if files:
                latest_file = max(files, key=os.path.getctime)
                await channel.send(f"🎞️ **[直連預覽]** 穿透成功！", file=discord.File(latest_file))
                return
        await channel.send("⚠️ 預覽超時，請確認民雄主機 D 槽落地狀態。")

# 確保目錄存在
os.makedirs(OUTPUT_DIR, exist_ok=True)
client = LiveViewCommander(intents=discord.Intents.all())
client.run(TOKEN)

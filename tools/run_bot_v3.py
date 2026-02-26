import discord
import os, subprocess, asyncio, time

# ================= 核心憑證 (2026-01-31 最終整合版) =================
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
AUTHORIZED_USER_ID = "962679936978657280"
BASE_DIR = r"C:\Users\user\Desktop\zhe-wei-tech"
OUTPUT_PATH = "D:/Messenger_Assets"
# =================================================================

class UltraCommander(discord.Client):
    async def on_ready(self):
        print(f"✅ 【影子指揮部】行動預覽模式已啟動。")
        print(f"📍 節點：民雄主機 (4060 Ti)")

    async def on_message(self, message):
        if str(message.author.id) != AUTHORIZED_USER_ID: return
        if message.author.bot: return

        cmd = message.content.lower()

        if cmd == "/start":
            status_msg = await message.channel.send("📡 **[任務啟動]** 正在啟動穿透流水線並準備預覽...")
            # 觸發物理流水線執行
            subprocess.Popen(["python", "cl3_shadow_pipeline.py"], cwd=BASE_DIR)
            
            # 啟動非同步監聽預覽回傳
            asyncio.create_task(self.check_and_send_preview(message.channel))

        elif cmd == "/cleanup":
            os.system("taskkill /F /IM python.exe /T >nul 2>&1")
            await message.channel.send("🧹 物理清理完成，4060 Ti 資源已釋放。")

    async def check_and_send_preview(self, channel):
        # 等待數據落地與剪輯時間
        await asyncio.sleep(15) 
        preview_file = os.path.join(OUTPUT_PATH, "preview.mp4")
        
        if os.path.exists(preview_file):
            await channel.send(content=f"🎞️ **預覽回傳**：穿透成功，畫質確認：", file=discord.File(preview_file))
        else:
            await channel.send("⚠️ 尚未偵測到預覽檔案，請確認穿透腳本是否正常運作。")

if __name__ == "__main__":
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    os.chdir(BASE_DIR)
    intents = discord.Intents.all()
    client = UltraCommander(intents=intents)
    client.run(TOKEN)

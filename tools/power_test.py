import discord
import os

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
AUTHORIZED_USER_ID = "962679936978657280"

class PowerCommander(discord.Client):
    async def on_ready(self):
        print(f"✅ 影子指揮部通訊測試中...")

    async def on_message(self, message):
        # 測試：對任何人說的話都回覆，確認權限是否成功
        if message.author == self.user: return
        
        print(f"📩 收到內容: {message.content} (來自 {message.author.id})")
        
        if str(message.author.id) == AUTHORIZED_USER_ID:
            await message.channel.send(f"✅ 身分驗證成功！收到指令：{message.content}")
        else:
            await message.channel.send("⚠️ 偵測到未授權存取。")

client = PowerCommander(intents=discord.Intents.all())
client.run(TOKEN)

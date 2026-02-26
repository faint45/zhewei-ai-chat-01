import discord
import os, time

# 核心憑證
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
AUTHORIZED_USER_ID = "962679936978657280"

class SecureCommander(discord.Client):
    async def on_ready(self):
        print(f"✅ 【影子守衛】已啟動，正在監視未授權存取...")

    async def on_message(self, message):
        if message.author == self.user: return

        # 核心監控日誌：記錄誰在輸入指令
        print(f"🔍 [監控] 收到來自 {message.author} (ID: {message.author.id}) 的內容: {message.content}")

        if str(message.author.id) != AUTHORIZED_USER_ID:
            # 針對未授權者的刺探進行記錄與回報
            if message.content.startswith("/"):
                await message.channel.send(f"⚠️ 偵測到未授權存取！用戶: {message.author}，身分已記錄。")
            return

        # 你的合法指令執行區
        if message.content.startswith("/start"):
            await message.channel.send("🚀 指令確認，啟動民雄節點流水線...")
            # 觸發物理流水線 logic...

# 啟動連線
client = SecureCommander(intents=discord.Intents.all())
client.run(TOKEN)

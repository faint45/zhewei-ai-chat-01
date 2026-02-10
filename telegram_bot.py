#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技Telegram机器人
集成远程控制功能到Telegram
"""

import os
import json
import logging
import requests
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ZhuWeiTechTelegramBot:
    def __init__(self, token: str, server_url: str):
        self.token = token
        self.server_url = server_url
        self.application = None
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        welcome_text = """
🤖 *築未科技AI助手*

欢迎使用築未科技远程控制机器人！

*可用命令：*
/start - 显示此帮助信息
/status - 检查服务器状态
/ai <问题> - 向AI提问
/sys <命令> - 执行系统命令
/help - 显示帮助信息

*示例：*
/ai 解释什么是机器学习
/sys python --version
/sys ping google.com
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /help 命令"""
        help_text = """
💡 *使用说明*

*AI指令（以 /ai 开头）*
- /ai <问题> - 向本地AI模型提问
- 示例：/ai 帮我分析这个Python代码

*系统指令（以 /sys 开头）*
- /sys <命令> - 执行系统命令
- 示例：/sys python --version

*其他命令*
- /status - 检查服务器状态
- /start - 显示欢迎信息
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /status 命令"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                status_text = f"""
✅ *服务器状态正常*

📊 连接数: {data.get('connectionCount', 0)}
⏰ 启动时间: {data.get('timestamp', '未知')}
🔧 服务类型: 远程控制服务器
                """
            else:
                status_text = "❌ *服务器连接失败*"
        except Exception as e:
            status_text = f"❌ *服务器状态检查失败*\n\n错误: {str(e)}"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def ai_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /ai 命令"""
        if not context.args:
            await update.message.reply_text("请提供要询问的问题，例如：/ai 解释什么是机器学习")
            return
        
        command = ' '.join(context.args)
        await self._execute_command(update, 'ai', command)
    
    async def sys_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /sys 命令"""
        if not context.args:
            await update.message.reply_text("请提供要执行的系统命令，例如：/sys python --version")
            return
        
        command = ' '.join(context.args)
        await self._execute_command(update, 'sys', command)
    
    async def _execute_command(self, update: Update, command_type: str, command: str):
        """执行远程命令 - 使用Unified API"""
        # 显示正在处理的消息
        processing_msg = await update.message.reply_text("🔄 正在执行命令...")
        
        try:
            # 生成用户ID（基于Telegram用户ID）
            user_id = f"telegram_{update.effective_user.id}"
            
            # 构建完整命令（包含类型前缀）
            if command_type == 'ai':
                full_command = f"ai:{command}"
            else:
                full_command = f"sys:{command}"
            
            # 使用Unified API发送命令
            payload = {
                "source": "telegram",
                "user_id": user_id,
                "command": full_command,
                "context_id": f"telegram_{update.effective_user.id}"
            }
            
            response = requests.post(
                f"{self.server_url}/v1/execute",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result["status"] == "success":
                    # 格式化回复
                    if command_type == 'ai':
                        reply_text = f"""
🤖 *AI回复* (跨平台連續性 ✅)

💬 *问题:* {command}

📝 *回答:* {result.get('result', '无回复')}

⏰ *执行时间:* {result.get('execution_time', 0):.2f}秒
🔗 *上下文ID:* {result.get('context_id', '新會話')}
                        """
                    else:
                        reply_text = f"""
⚙️ *系统命令结果*

💻 *命令:* {command}

📋 *输出:* {result.get('result', '无输出')}

⏰ *执行时间:* {result.get('execution_time', 0):.2f}秒
                        """
                    
                    # 如果回复太长，分多次发送
                    if len(reply_text) > 4000:
                        chunks = [reply_text[i:i+4000] for i in range(0, len(reply_text), 4000)]
                        for chunk in chunks:
                            await update.message.reply_text(chunk, parse_mode='Markdown')
                    else:
                        await update.message.reply_text(reply_text, parse_mode='Markdown')
                    
                    # 删除处理中的消息
                    await processing_msg.delete()
                else:
                    await processing_msg.edit_text(f"❌ 命令执行失败: {result.get('error', '未知错误')}")
                
            else:
                await processing_msg.edit_text("❌ 服务器连接失败")
                
        except requests.exceptions.Timeout:
            await processing_msg.edit_text("⏰ 命令执行超时，请稍后重试")
        except Exception as e:
            await processing_msg.edit_text(f"❌ 命令执行失败: {str(e)}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理普通消息"""
        message_text = update.message.text
        
        # 如果不是以命令开头，当作AI对话处理
        if not message_text.startswith('/'):
            await self._execute_command(update, 'ai', message_text)
        else:
            await update.message.reply_text("请使用正确的命令格式，输入 /help 查看帮助")
    
    async def setup_commands(self, application: Application):
        """设置机器人命令菜单"""
        commands = [
            BotCommand("start", "开始使用机器人"),
            BotCommand("help", "显示帮助信息"),
            BotCommand("status", "检查服务器状态"),
            BotCommand("ai", "向AI提问"),
            BotCommand("sys", "执行系统命令")
        ]
        await application.bot.set_my_commands(commands)
    
    def run(self):
        """启动机器人"""
        # 创建应用
        self.application = Application.builder().token(self.token).build()
        
        # 添加命令处理器
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("ai", self.ai_command))
        self.application.add_handler(CommandHandler("sys", self.sys_command))
        
        # 添加消息处理器
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # 设置命令菜单
        self.application.post_init = self.setup_commands
        
        # 启动机器人
        logger.info("🤖 築未科技Telegram机器人启动中...")
        logger.info(f"🌐 服务器地址: {self.server_url}")
        
        self.application.run_polling()

def main():
    """主函数"""
    # 从环境变量获取配置
    token = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
    server_url = os.getenv('SERVER_URL', 'http://localhost:8003')
    
    if token == 'YOUR_BOT_TOKEN_HERE':
        print("❌ 请设置TELEGRAM_BOT_TOKEN环境变量")
        print("💡 使用方法:")
        print("1. 在BotFather创建机器人获取token")
        print("2. 设置环境变量: set TELEGRAM_BOT_TOKEN=你的token")
        print("3. 运行: python telegram_bot.py")
        return
    
    # 创建并启动机器人
    bot = ZhuWeiTechTelegramBot(token, server_url)
    bot.run()

if __name__ == "__main__":
    main()
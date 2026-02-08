#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技Discord机器人
集成远程控制功能到Discord
"""

import os
import json
import logging
import requests
import discord
from discord.ext import commands
from discord import app_commands

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ZhuWeiTechDiscordBot:
    def __init__(self, token: str, server_url: str):
        self.token = token
        self.server_url = server_url
        
        # 创建机器人实例
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        
        # 注册事件处理器
        self.bot.event(self.on_ready)
        self.bot.event(self.on_message)
        
        # 注册斜杠命令
        self.tree = self.bot.tree
        
    async def on_ready(self):
        """机器人准备就绪时调用"""
        logger.info(f'🤖 築未科技Discord机器人已登录: {self.bot.user}')
        logger.info(f'🌐 服务器地址: {self.server_url}')
        
        # 同步斜杠命令
        try:
            synced = await self.tree.sync()
            logger.info(f'✅ 已同步 {len(synced)} 个斜杠命令')
        except Exception as e:
            logger.error(f'❌ 同步命令失败: {e}')
        
        # 设置机器人状态
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="築未科技AI助手 | !help"
            )
        )
    
    async def on_message(self, message):
        """处理普通消息"""
        # 忽略机器人自己的消息
        if message.author == self.bot.user:
            return
        
        # 处理以!开头的命令
        if message.content.startswith('!'):
            await self.bot.process_commands(message)
        else:
            # 如果不是命令，当作AI对话处理
            await self._handle_ai_conversation(message)
    
    async def _handle_ai_conversation(self, message):
        """处理AI对话"""
        # 只在特定频道或私信时响应
        if isinstance(message.channel, discord.DMChannel) or 'ai' in message.channel.name.lower():
            async with message.channel.typing():
                try:
                    user_id = f"discord_{message.author.id}"
                    response = await self._execute_command('ai', message.content, user_id)
                    
                    # 创建嵌入消息
                    embed = discord.Embed(
                        title="🤖 AI回复 (跨平台連續性 ✅)",
                        description=response.get('result', '无回复'),
                        color=0x00ff00
                    )
                    embed.add_field(name="💬 问题", value=message.content, inline=False)
                    embed.add_field(name="⏰ 执行时间", value=f"{response.get('execution_time', 0):.2f}秒", inline=True)
                    embed.add_field(name="🔗 上下文ID", value=response.get('context_id', '新會話'), inline=True)
                    
                    await message.reply(embed=embed)
                    
                except Exception as e:
                    await message.reply(f"❌ 处理失败: {str(e)}")
    
    @commands.command(name='help')
    async def help_command(self, ctx):
        """显示帮助信息"""
        embed = discord.Embed(
            title="🤖 築未科技AI助手帮助",
            description="使用以下命令与本地AI模型交互",
            color=0x0099ff
        )
        
        embed.add_field(
            name="💬 前缀命令",
            value="""
`!help` - 显示此帮助信息
`!status` - 检查服务器状态
`!ai <问题>` - 向AI提问
`!sys <命令>` - 执行系统命令
            """,
            inline=False
        )
        
        embed.add_field(
            name="⚡ 斜杠命令",
            value="""
`/ai` - 向AI提问
`/sys` - 执行系统命令
`/status` - 检查服务器状态
            """,
            inline=False
        )
        
        embed.add_field(
            name="📋 示例",
            value="""
`!ai 解释什么是机器学习`
`!sys python --version`
`/ai 帮我写一个Python函数`
            """,
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='status')
    async def status_command(self, ctx):
        """检查服务器状态"""
        async with ctx.channel.typing():
            try:
                response = requests.get(f"{self.server_url}/health", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    embed = discord.Embed(
                        title="✅ 服务器状态正常",
                        color=0x00ff00
                    )
                    embed.add_field(name="📊 连接数", value=data.get('connectionCount', 0), inline=True)
                    embed.add_field(name="⏰ 启动时间", value=data.get('timestamp', '未知'), inline=True)
                    embed.add_field(name="🔧 服务类型", value="远程控制服务器", inline=True)
                    
                else:
                    embed = discord.Embed(
                        title="❌ 服务器连接失败",
                        color=0xff0000
                    )
                    
            except Exception as e:
                embed = discord.Embed(
                    title="❌ 服务器状态检查失败",
                    description=f"错误: {str(e)}",
                    color=0xff0000
                )
            
            await ctx.send(embed=embed)
    
    @commands.command(name='ai')
    async def ai_command(self, ctx, *, question):
        """AI对话命令"""
        async with ctx.channel.typing():
            try:
                response = await self._execute_command('ai', question)
                
                embed = discord.Embed(
                    title="🤖 AI回复",
                    description=response.get('result', '无回复'),
                    color=0x00ff00
                )
                embed.add_field(name="💬 问题", value=question, inline=False)
                embed.add_field(name="⏰ 执行时间", value=f"{response.get('execution_time', '未知')}秒", inline=True)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"❌ AI对话失败: {str(e)}")
    
    @commands.command(name='sys')
    async def sys_command(self, ctx, *, command):
        """系统命令"""
        async with ctx.channel.typing():
            try:
                response = await self._execute_command('sys', command)
                
                embed = discord.Embed(
                    title="⚙️ 系统命令结果",
                    description=response.get('result', '无输出'),
                    color=0x0099ff
                )
                embed.add_field(name="💻 命令", value=command, inline=False)
                embed.add_field(name="⏰ 执行时间", value=f"{response.get('execution_time', '未知')}秒", inline=True)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"❌ 系统命令执行失败: {str(e)}")
    
    # 斜杠命令
    @app_commands.command(name="ai", description="向AI提问")
    @app_commands.describe(question="要询问的问题")
    async def slash_ai(self, interaction: discord.Interaction, question: str):
        """斜杠命令 - AI对话"""
        await interaction.response.defer()
        
        try:
            response = await self._execute_command('ai', question)
            
            embed = discord.Embed(
                title="🤖 AI回复",
                description=response.get('result', '无回复'),
                color=0x00ff00
            )
            embed.add_field(name="💬 问题", value=question, inline=False)
            embed.add_field(name="⏰ 执行时间", value=f"{response.get('execution_time', '未知')}秒", inline=True)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ AI对话失败: {str(e)}")
    
    @app_commands.command(name="sys", description="执行系统命令")
    @app_commands.describe(command="要执行的系统命令")
    async def slash_sys(self, interaction: discord.Interaction, command: str):
        """斜杠命令 - 系统命令"""
        await interaction.response.defer()
        
        try:
            response = await self._execute_command('sys', command)
            
            embed = discord.Embed(
                title="⚙️ 系统命令结果",
                description=response.get('result', '无输出'),
                color=0x0099ff
            )
            embed.add_field(name="💻 命令", value=command, inline=False)
            embed.add_field(name="⏰ 执行时间", value=f"{response.get('execution_time', '未知')}秒", inline=True)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ 系统命令执行失败: {str(e)}")
    
    @app_commands.command(name="status", description="检查服务器状态")
    async def slash_status(self, interaction: discord.Interaction):
        """斜杠命令 - 状态检查"""
        await interaction.response.defer()
        
        try:
            response = requests.get(f"{self.server_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                embed = discord.Embed(
                    title="✅ 服务器状态正常",
                    color=0x00ff00
                )
                embed.add_field(name="📊 连接数", value=data.get('connectionCount', 0), inline=True)
                embed.add_field(name="⏰ 启动时间", value=data.get('timestamp', '未知'), inline=True)
                embed.add_field(name="🔧 服务类型", value="远程控制服务器", inline=True)
                
            else:
                embed = discord.Embed(
                    title="❌ 服务器连接失败",
                    color=0xff0000
                )
                
        except Exception as e:
            embed = discord.Embed(
                title="❌ 服务器状态检查失败",
                description=f"错误: {str(e)}",
                color=0xff0000
            )
        
        await interaction.followup.send(embed=embed)
    
    async def _execute_command(self, command_type: str, command: str, user_id: str = None):
        """执行远程命令 - 使用Unified API"""
        if user_id is None:
            user_id = "discord_anonymous"
            
        # 构建完整命令（包含类型前缀）
        if command_type == 'ai':
            full_command = f"ai:{command}"
        else:
            full_command = f"sys:{command}"
        
        # 使用Unified API发送命令
        payload = {
            "source": "discord",
            "user_id": user_id,
            "command": full_command,
            "context_id": user_id
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
                return result
            else:
                raise Exception(result.get('error', '执行失败'))
        else:
            raise Exception(f"服务器返回错误: {response.status_code}")
    
    def run(self):
        """启动机器人"""
        logger.info("🤖 築未科技Discord机器人启动中...")
        self.bot.run(self.token)

def main():
    """主函数"""
    # 从环境变量获取配置
    token = os.getenv('DISCORD_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
    server_url = os.getenv('SERVER_URL', 'http://localhost:8003')
    
    if token == 'YOUR_BOT_TOKEN_HERE':
        print("❌ 请设置DISCORD_BOT_TOKEN环境变量")
        print("💡 使用方法:")
        print("1. 在Discord开发者门户创建应用获取token")
        print("2. 设置环境变量: set DISCORD_BOT_TOKEN=你的token")
        print("3. 运行: python discord_bot.py")
        return
    
    # 创建并启动机器人
    bot = ZhuWeiTechDiscordBot(token, server_url)
    bot.run()

if __name__ == "__main__":
    main()
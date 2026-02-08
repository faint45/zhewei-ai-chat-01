#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 API 监控服务
"""

import asyncio
import random
from datetime import datetime
import httpx

# API 端点
BASE_URL = "http://localhost:8001"


async def simulate_request(source: str, command: str):
    """模拟 API 请求"""
    start_time = datetime.now()
    
    # 模拟执行时间
    execution_time = random.uniform(0.1, 2.0)
    await asyncio.sleep(execution_time)
    
    # 模拟成功/失败
    status = "success" if random.random() > 0.05 else "error"
    
    # 模拟 token 使用
    tokens_used = random.randint(50, 500) if status == "success" else 0
    
    # 模拟费用（每1000 tokens $0.002）
    cost = (tokens_used / 1000) * 0.002
    
    request_data = {
        "request_id": f"req_{int(datetime.now().timestamp() * 1000)}",
        "source": source,
        "user_id": f"user_{random.randint(1, 100)}",
        "command": command,
        "status": status,
        "execution_time": execution_time,
        "tokens_used": tokens_used,
        "cost": cost
    }
    
    # 发送到监控服务
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/api/log-request", json=request_data)
        
        if response.status_code == 200:
            print(f"✓ {source}: {command[:30]}... - {status} - {execution_time:.3f}s")
        else:
            print(f"✗ 记录失败: {response.status_code}")


async def run_test():
    """运行测试"""
    print("=" * 60)
    print("API 监控服务测试")
    print("=" * 60)
    print()
    
    sources = ["telegram", "discord", "wechat", "web"]
    commands = [
        "ai:你好",
        "ai:解释机器学习",
        "ai:写一首诗",
        "ai:分析数据",
        "ai:生成代码",
        "sys:ping www.google.com",
        "sys:dir",
        "sys:tasklist",
        "sys:netstat",
        "sys:ipconfig"
    ]
    
    print("模拟 50 个 API 请求...")
    print()
    
    tasks = []
    for _ in range(50):
        source = random.choice(sources)
        command = random.choice(commands)
        task = simulate_request(source, command)
        tasks.append(task)
        await asyncio.sleep(random.uniform(0.1, 0.5))  # 随机间隔
    
    await asyncio.gather(*tasks)
    
    print()
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)
    print()
    print("访问监控面板查看结果:")
    print(f"  📊 http://{BASE_URL}")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        print("\n测试已取消")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

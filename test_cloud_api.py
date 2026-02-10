#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技 - 云端API连接测试
"""

import requests
import json
import sys

def test_cloud_api(base_url):
    """测试云端API连接"""

    print("=" * 50)
    print("築未科技 - 云端API连接测试")
    print("=" * 50)
    print()

    # 移除末尾斜杠
    base_url = base_url.rstrip('/')
    print(f"测试地址：{base_url}")
    print()

    # 测试1：健康检查
    print("测试1：健康检查...")
    try:
        health_url = f"{base_url}/health"
        print(f"请求：{health_url}")
        response = requests.get(health_url, timeout=10)

        if response.status_code == 200:
            print(f"✅ 健康检查成功")
            print(f"响应：{response.json()}")
        else:
            print(f"❌ 健康检查失败，状态码：{response.status_code}")
    except Exception as e:
        print(f"❌ 健康检查失败：{str(e)}")
    print()

    # 测试2：统一API - AI命令
    print("测试2：统一API - AI命令...")
    try:
        execute_url = f"{base_url}/v1/execute"
        payload = {
            "source": "test",
            "user_id": "test_user",
            "command": "ai:你好"
        }
        print(f"请求：{execute_url}")
        print(f"参数：{json.dumps(payload, ensure_ascii=False)}")

        response = requests.post(
            execute_url,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ API调用成功")
            print(f"状态：{result.get('status')}")
            print(f"执行时间：{result.get('execution_time', 0):.2f}秒")
            print(f"响应：{result.get('result', 'N/A')}")
        else:
            print(f"❌ API调用失败，状态码：{response.status_code}")
            print(f"响应：{response.text}")
    except Exception as e:
        print(f"❌ API调用失败：{str(e)}")
    print()

    # 测试3：API文档
    print("测试3：API文档...")
    try:
        docs_url = f"{base_url}/docs"
        print(f"请求：{docs_url}")
        response = requests.get(docs_url, timeout=10)

        if response.status_code == 200:
            print(f"✅ API文档可访问")
        else:
            print(f"❌ API文档访问失败，状态码：{response.status_code}")
    except Exception as e:
        print(f"❌ API文档访问失败：{str(e)}")
    print()

    print("=" * 50)
    print("测试完成")
    print("=" * 50)

def main():
    """主函数"""
    if len(sys.argv) > 1:
        cloud_url = sys.argv[1]
    else:
        # 交互式输入
        print("请输入您的云端API地址")
        print("示例：https://zhewei-api-xxx.service.tcloudbase.com")
        print()
        cloud_url = input("访问地址：").strip()

    if not cloud_url:
        print("❌ 访问地址不能为空")
        return

    test_cloud_api(cloud_url)

if __name__ == "__main__":
    main()
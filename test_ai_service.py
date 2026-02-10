#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試 AI 服務功能
"""

import asyncio
import sys
import os

# 添加當前目錄到 Python 路徑
sys.path.append(os.path.dirname(__file__))

async def test_ai_service():
    """測試 AI 服務"""
    try:
        from app import ai_service
        print("=" * 60)
        print("測試築未科技 AI 對話系統")
        print("=" * 60)
        
        print(f"當前 AI 模型: {ai_service.config.MODEL_TYPE.value}")
        print(f"模型名稱: {ai_service.config.get_model_name()}")
        
        # 測試簡單對話
        test_messages = [
            "你好",
            "現在時間",
            "系統狀態"
        ]
        
        for message in test_messages:
            print(f"\n發送消息: {message}")
            try:
                response = await ai_service.generate_response(message)
                print(f"AI 回應: {response[:100]}..." if len(response) > 100 else f"AI 回應: {response}")
            except Exception as e:
                print(f"錯誤: {e}")
        
        print("\n" + "=" * 60)
        print("測試完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"初始化錯誤: {e}")

if __name__ == "__main__":
    asyncio.run(test_ai_service())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Qwen API"""
import sys
import io

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from qwen_client import QwenClient

try:
    client = QwenClient()
    print("SUCCESS: Qwen API connected")

    result = client.generate("Hello")
    print("Response:", result[:100] + "..." if len(result) > 100 else result)

except Exception as e:
    print("ERROR:", str(e))

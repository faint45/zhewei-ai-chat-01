#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Ollama connection"""

import asyncio
import requests
from openai import OpenAI

print("=" * 60)
print("Testing Ollama Service Connection")
print("=" * 60)

# Test 1: Check Ollama service status
print("\n[Test 1] Checking Ollama service status...")
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    if response.status_code == 200:
        print("OK: Ollama service is running")
        models = response.json().get('models', [])
        print(f"   Available models: {len(models)}")
        for model in models:
            print(f"   - {model['name']}")
    else:
        print(f"ERROR: Ollama service returned HTTP {response.status_code}")
except Exception as e:
    print(f"ERROR: Cannot connect to Ollama: {e}")

# Test 2: Use OpenAI SDK to connect to Ollama
print("\n[Test 2] Connecting via OpenAI SDK...")
try:
    client = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama"  # Ollama doesn't need real API key
    )

    print("Testing chat...")
    response = client.chat.completions.create(
        model="gemma3:4b",
        messages=[
            {"role": "user", "content": "Hello, introduce yourself in one sentence"}
        ],
        max_tokens=100,
        temperature=0.7
    )

    print("OK: API call successful")
    print(f"   Response: {response.choices[0].message.content}")
    print(f"   Model used: {response.model}")
except Exception as e:
    print(f"ERROR: API call failed: {e}")

print("\n" + "=" * 60)
print("Test completed")
print("=" * 60)

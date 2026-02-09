#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
築未科技大腦 - AI 配置文件
支持 OpenAI 和 Ollama 兩種模型
"""

import os
from typing import Optional
from enum import Enum

class AIModelType(Enum):
    """AI 模型類型"""
    OPENAI = "openai"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    QWEN = "qwen"
    DEMO = "demo"

class AIConfig:
    """AI 模型配置類"""
    
    # AI 模型類型配置
    MODEL_TYPE: AIModelType = AIModelType.DEMO  # 默認使用演示模式
    
    # OpenAI 配置
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Ollama 配置
    OLLAMA_API_BASE: str = "http://localhost:11461/v1"
    OLLAMA_MODEL: str = "llama3.1"  # 默認使用 llama3.1 模型
    
    # Gemini 配置
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-pro"
    
    # 通義千問配置
    DASHSCOPE_API_KEY: Optional[str] = None
    QWEN_MODEL: str = "qwen-plus"
    
    # 通用模型參數
    MAX_TOKENS: int = 1000
    TEMPERATURE: float = 0.7
    TOP_P: float = 0.9
    
    # 上下文配置
    CONTEXT_MESSAGES: int = 10  # 保留最近幾條對話記錄
    
    # 成本控制（僅適用於 OpenAI）
    ENABLE_COST_TRACKING: bool = True
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def load_from_env(cls):
        """從環境變量加載配置"""
        # 檢測模型類型
        model_type_str = os.getenv("AI_MODEL_TYPE", "demo").lower()
        if model_type_str == "openai" and os.getenv("OPENAI_API_KEY"):
            model_type = AIModelType.OPENAI
        elif model_type_str == "ollama":
            model_type = AIModelType.OLLAMA
        elif model_type_str == "gemini" and os.getenv("GEMINI_API_KEY"):
            model_type = AIModelType.GEMINI
        elif model_type_str == "qwen" and os.getenv("DASHSCOPE_API_KEY"):
            model_type = AIModelType.QWEN
        else:
            model_type = AIModelType.DEMO
        
        return cls(
            MODEL_TYPE=model_type,
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
            OPENAI_MODEL=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            OLLAMA_API_BASE=os.getenv("OLLAMA_API_BASE", "http://localhost:11461/v1"),
            OLLAMA_MODEL=os.getenv("OLLAMA_MODEL", "llama3.1"),
            GEMINI_API_KEY=os.getenv("GEMINI_API_KEY"),
            GEMINI_MODEL=os.getenv("GEMINI_MODEL", "gemini-pro"),
            DASHSCOPE_API_KEY=os.getenv("DASHSCOPE_API_KEY"),
            QWEN_MODEL=os.getenv("QWEN_MODEL", "qwen-plus"),
            MAX_TOKENS=int(os.getenv("AI_MAX_TOKENS", "1000")),
            TEMPERATURE=float(os.getenv("AI_TEMPERATURE", "0.7"))
        )
    
    @classmethod
    def validate(cls, config: 'AIConfig') -> bool:
        """驗證配置是否有效"""
        if config.MODEL_TYPE == AIModelType.OPENAI:
            if not config.OPENAI_API_KEY:
                print("⚠️  警告：未設置 OPENAI_API_KEY")
                print("💡 提示：您需要設置 API 密鑰才能使用 OpenAI 功能")
                print("📋 獲取方式：https://platform.openai.com/api-keys")
                return False
            print("[AI] 使用 OpenAI 模型")
            print(f"  模型: {config.OPENAI_MODEL}")
        elif config.MODEL_TYPE == AIModelType.OLLAMA:
            print("[AI] 使用 Ollama 本地模型")
            print(f"  模型: {config.OLLAMA_MODEL}")
            print(f"  API 地址: {config.OLLAMA_API_BASE}")
            print("[提示] 請確保 Ollama 服務正在運行")
        elif config.MODEL_TYPE == AIModelType.GEMINI:
            if not config.GEMINI_API_KEY:
                print("⚠️  警告：未設置 GEMINI_API_KEY")
                print("💡 提示：您需要設置 API 密鑰才能使用 Gemini 功能")
                print("📋 獲取方式：https://aistudio.google.com/app/apikey")
                return False
            print("[AI] 使用 Google Gemini 模型")
            print(f"  模型: {config.GEMINI_MODEL}")
        elif config.MODEL_TYPE == AIModelType.QWEN:
            if not config.DASHSCOPE_API_KEY:
                print("⚠️  警告：未設置 DASHSCOPE_API_KEY")
                print("💡 提示：您需要設置 API 密鑰才能使用通義千問功能")
                print("📋 獲取方式：https://dashscope.aliyun.com/")
                return False
            print("[AI] 使用通義千問模型")
            print(f"  模型: {config.QWEN_MODEL}")
        else:
            print("[模式] 使用演示模式")
            print("[提示] 可以設置環境變量切換到 OpenAI、Ollama、Gemini 或 Qwen")
        
        return True
    
    def get_api_base(self) -> str:
        """獲取當前 API 基礎地址"""
        if self.MODEL_TYPE == AIModelType.OPENAI:
            return self.OPENAI_API_BASE
        elif self.MODEL_TYPE == AIModelType.OLLAMA:
            return self.OLLAMA_API_BASE
        elif self.MODEL_TYPE == AIModelType.GEMINI:
            return "https://generativelanguage.googleapis.com/v1"
        elif self.MODEL_TYPE == AIModelType.QWEN:
            return "https://dashscope.aliyuncs.com/api/v1"
        return ""
    
    def get_api_key(self) -> Optional[str]:
        """獲取當前 API 密鑰"""
        if self.MODEL_TYPE == AIModelType.OPENAI:
            return self.OPENAI_API_KEY
        elif self.MODEL_TYPE == AIModelType.GEMINI:
            return self.GEMINI_API_KEY
        elif self.MODEL_TYPE == AIModelType.QWEN:
            return self.DASHSCOPE_API_KEY
        return "not-needed"  # Ollama 不需要 API 密鑰
    
    def get_model_name(self) -> str:
        """獲取當前模型名稱"""
        if self.MODEL_TYPE == AIModelType.OPENAI:
            return self.OPENAI_MODEL
        elif self.MODEL_TYPE == AIModelType.OLLAMA:
            return self.OLLAMA_MODEL
        elif self.MODEL_TYPE == AIModelType.GEMINI:
            return self.GEMINI_MODEL
        elif self.MODEL_TYPE == AIModelType.QWEN:
            return self.QWEN_MODEL
        return "demo"

# 全局配置實例
ai_config = AIConfig.load_from_env()

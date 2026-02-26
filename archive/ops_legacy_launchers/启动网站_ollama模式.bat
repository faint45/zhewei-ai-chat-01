@echo off
chcp 65001 >nul
title 筑未科技 - 启动网站服务器 (Ollama 模式)

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║     筑未科技 - Ollama 本地 AI 模式启动                   ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM 设置环境变量
set AI_MODEL_TYPE=ollama
set OLLAMA_MODEL=gemma3:4b
set OLLAMA_API_BASE=http://localhost:11434/v1

echo 📊 配置信息：
echo    AI 模式: %AI_MODEL_TYPE%
echo    模型名称: %OLLAMA_MODEL%
echo    API 地址: %OLLAMA_API_BASE%
echo.

echo 🤖 Ollama 服务已经在运行中...
echo.

echo 🚀 启动网站服务器...
echo.

python website_server.py

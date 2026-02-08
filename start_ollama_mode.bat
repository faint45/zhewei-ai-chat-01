@echo off
chcp 65001 >nul
title 筑未科技 - 启动 Ollama 模式

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║     筑未科技 - Ollama 本地 AI 模式启动                   ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM 设置环境变量
set AI_MODEL_TYPE=ollama
set OLLAMA_MODEL=gemma3:4b
set OLLAMA_API_BASE=http://localhost:11434/v1

echo [1/2] 启动 Ollama 服务...
echo 💡 Ollama 将在独立窗口中运行
echo.

start "Ollama 服务" cmd /k "title Ollama 服务 && ollama serve"

echo ✅ Ollama 服务正在启动...
echo.

echo [2/2] 等待 5 秒后启动网站服务器...
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   启动网站服务器 (Ollama 模式)
echo ========================================
echo.
echo AI 模式: %AI_MODEL_TYPE%
echo 模型名称: %OLLAMA_MODEL%
echo API 地址: %OLLAMA_API_BASE%
echo.

python website_server.py

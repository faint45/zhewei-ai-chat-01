@echo off
chcp 65001 >nul
title Ollama 服务启动器

echo.
echo ========================================
echo    Ollama 服务启动器
echo ========================================
echo.
echo 🤖 正在启动 Ollama 服务...
echo.
echo 💡 提示：
echo    - 此窗口需要保持打开状态
echo    - Ollama 将在后台运行
echo    - 按 Ctrl+C 可停止服务
echo.
echo ========================================
echo.

ollama serve

echo.
echo ❌ Ollama 服务已停止
echo.
pause

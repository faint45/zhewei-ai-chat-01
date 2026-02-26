@echo off
chcp 65001 >nul
title 筑未科技 - API 监控面板

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║     筑未科技 - API 监控面板启动器                         ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误：未检测到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
echo ✅ Python 已安装
python --version
echo.

echo [2/3] 检查依赖...
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装依赖...
    pip install -r requirements_ai.txt
)
echo ✅ 依赖检查完成
echo.

echo [3/3] 启动监控面板...
echo.
echo 📊 监控面板: http://localhost:8001
echo 📄 API 文档: http://localhost:8001/docs
echo.
echo 💡 按 Ctrl+C 可停止服务
echo.

python monitoring_dashboard.py

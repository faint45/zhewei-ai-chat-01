@echo off
chcp 65001 >nul
title 筑未科技 - SSH 服务状态检查

echo ============================================================
echo 筑未科技 - SSH 服务状态检查
echo ============================================================
echo.

echo [检查 1/3] 检查 SSH 服务状态...
echo.
sc query sshd 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [✅] SSH 服务已找到
    sc query sshd | find "STATE"
) else (
    echo [❌] SSH 服务未找到
    echo.
    echo 这表示 OpenSSH 服务器还没有安装
)
echo.

echo [检查 2/3] 检查端口 22 监听状态...
echo.
netstat -ano | findstr ":22 " | findstr "LISTENING"
if %ERRORLEVEL% EQU 0 (
    echo [✅] 端口 22 正在监听
) else (
    echo [❌] 端口 22 未监听
)
echo.

echo [检查 3/3] 检查所有 SSH 相关服务...
echo.
sc query | findstr -i ssh
echo.

echo ============================================================
echo 当前状态
echo ============================================================
echo.
echo 如果 SSH 服务未找到，请使用以下方法之一安装：
echo.
echo 方法 1: 通过 Windows 设置（推荐）
echo   1. Win + I 打开设置
echo   2. 应用 > 可选功能 > 添加功能
echo   3. 搜索 "OpenSSH Server"
echo   4. 安装
echo   5. Win + R > 输入 services.msc
echo   6. 启动 OpenSSH SSH Server
echo.
echo 方法 2: 运行自动安装脚本
echo   右键以管理员身份运行：运行_OpenSSH_安装.bat
echo.
echo 详细说明：OPENSSH_安装步骤.md
echo.
pause

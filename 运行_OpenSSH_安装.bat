@echo off
chcp 65001 >nul
title 筑未科技 - OpenSSH 服务器安装

echo ============================================================
echo 筑未科技 - OpenSSH 服务器安装
echo ============================================================
echo.

REM 检查管理员权限
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 需要管理员权限！
    echo.
    echo 请右键点击此文件，选择"以管理员身份运行"
    echo.
    pause
    exit /b 1
)

echo [准备] 检查 PowerShell 脚本执行策略...
echo.

REM 设置 PowerShell 执行策略
powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [警告] 无法设置 PowerShell 执行策略
    echo.
    echo 可能的原因：
    echo   - 组策略限制
    echo   - 杀毒软件阻止
    echo.
    echo 但这通常不会影响脚本运行
    echo.
)

echo.
echo [启动] 运行 OpenSSH 安装脚本...
echo.

REM 运行 PowerShell 安装脚本
powershell -ExecutionPolicy Bypass -File "%~dp0install_openssh.ps1"

pause

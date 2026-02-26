@echo off
chcp 65001 >nul
title 筑未科技 - 基础设施配置检查

echo ============================================================
echo 筑未科技 - 基础设施配置检查工具
echo ============================================================
echo.

echo [检查 1/4] 检查 Tailscale 安装状态...
echo.
echo 请确认您已完成以下操作：
echo   1. 访问 https://tailscale.com/download/windows
echo   2. 下载并安装 Tailscale
echo   3. 使用账号登录
echo.
pause

echo.
echo 检查 Tailscale 服务状态...
where tailscale >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [✅] Tailscale 已安装
    echo.
    echo 获取 Tailscale 状态:
    tailscale status
    echo.
    echo 如果看到设备列表，说明 Tailscale 工作正常！
) else (
    echo [❌] 未找到 Tailscale
    echo.
    echo 请先安装 Tailscale：
    echo   1. 访问 https://tailscale.com/download/windows
    echo   2. 下载并安装 .msi 文件
    echo   3. 使用 Google/Microsoft/GitHub 账号登录
)
echo.
pause

echo.
echo [检查 2/4] 检查 OpenSSH 安装状态...
echo.
powershell -Command "Get-WindowsCapability -Online | Where-Object {$_.Name -like 'OpenSSH*'} | Select-Object Name, State"
echo.
echo 注意：上面的命令可能会失败，这是正常的（需要管理员权限）
echo.
pause

echo.
echo [检查 3/4] 检查 SSH 服务状态...
echo.
sc query sshd | find "RUNNING"
if %ERRORLEVEL% EQU 0 (
    echo [✅] SSH 服务正在运行
) else (
    echo [❌] SSH 服务未运行
    echo.
    echo 请执行以下步骤启动 SSH 服务：
    echo   1. 以管理员身份打开 PowerShell
    echo   2. 运行：Start-Service sshd
    echo   3. 运行：Set-Service -Name sshd -StartupType 'Automatic'
)
echo.
pause

echo.
echo [检查 4/4] 测试 SSH 本地连接...
echo.
ssh localhost -o ConnectTimeout=3
if %ERRORLEVEL% EQU 0 (
    echo [✅] SSH 本地连接成功
) else (
    echo [❌] 无法连接到 SSH 服务
    echo.
    echo 可能的原因：
    echo   1. SSH 服务未启动
    echo   2. 防火墙阻止连接
    echo   3. SSH 配置有问题
)
echo.
pause

echo.
echo ============================================================
echo 检查完成
echo ============================================================
echo.
echo 📋 配置检查清单：
echo.
echo Tailscale:
echo   [ ] 已在 PC 上安装并登录
echo   [ ] 已在手机上安装并登录
echo   [ ] 已在笔电上安装并登录
echo   [ ] 所有设备显示为 "Online"
echo   [ ] 已获取 Tailscale IP
echo   [ ] 可以从笔电 ping 通 Tailscale IP
echo.
echo OpenSSH:
echo   [ ] OpenSSH 服务器已安装
echo   [ ] SSH 服务正在运行
echo   [ ] 防火墙规则已配置
echo   [ ] 可以通过 ssh localhost 本地连接
echo   [ ] 可以从笔电远程连接
echo   [ ] VS Code Remote SSH 已安装
echo.
echo 详细配置指南：
echo   - 基础设施配置指南.md（快速开始）
echo   - TAILSCALE_SETUP.md（详细指南）
echo   - OPENSSH_SETUP.md（详细指南）
echo.
echo 需要帮助？
echo   查看 "基础设施配置指南.md" 获取详细的分步说明
echo.
pause

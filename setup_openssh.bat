@echo off
chcp 65001 >nul
title 筑未科技 - OpenSSH 配置

echo ============================================================
echo 筑未科技 - OpenSSH 配置工具
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

echo [1/6] 检查 OpenSSH 安装状态...
echo.
echo 正在检查 Windows 功能...
powershell -Command "Get-WindowsCapability -Online | Where-Object {$_.Name -like 'OpenSSH*'} | Select-Object Name, State" 2>nul

echo.
echo.
echo 如果上面显示错误，请手动检查：
echo   1. 打开"设置" > "应用" > "可选功能"
echo   2. 搜索 "OpenSSH"
echo   3. 检查是否已安装"OpenSSH 服务器"
echo.
pause

echo.
echo [2/6] 启动 SSH 服务...
echo.
net start sshd 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [✅] SSH 服务启动成功
) else (
    echo [⚠️] SSH 服务启动失败或已在运行
)
echo.

echo 设置为开机自动启动...
sc config sshd start= auto
echo [✅] 已设置为自动启动
echo.

pause

echo.
echo [3/6] 配置防火墙规则...
echo.
netsh advfirewall firewall show rule name="OpenSSH-Server-In-TCP" | findstr "找不到" >nul
if %ERRORLEVEL% EQU 0 (
    echo 添加防火墙规则...
    netsh advfirewall firewall add rule name="OpenSSH-Server-In-TCP" dir=in action=allow protocol=TCP localport=22
    if %ERRORLEVEL% EQU 0 (
        echo [✅] 防火墙规则添加成功
    ) else (
        echo [❌] 防火墙规则添加失败
    )
) else (
    echo [✅] 防火墙规则已存在
)
echo.

pause

echo.
echo [4/6] 配置 SSH 服务...
echo.
echo 设置 SSH 配置文件路径...
if not exist "C:\ProgramData\ssh" mkdir "C:\ProgramData\ssh"

echo.
echo 配置 sshd_config...
if exist "C:\ProgramData\ssh\sshd_config_default" (
    copy "C:\ProgramData\ssh\sshd_config_default" "C:\ProgramData\ssh\sshd_config" /Y >nul
)
echo [✅] SSH 配置完成
echo.

pause

echo.
echo [5/6] 重启 SSH 服务...
echo.
net stop sshd >nul 2>&1
timeout /t 2 /nobreak >nul
net start sshd
if %ERRORLEVEL% EQU 0 (
    echo [✅] SSH 服务重启成功
) else (
    echo [❌] SSH 服务重启失败
)
echo.

pause

echo.
echo [6/6] 测试 SSH 连接...
echo.
echo 尝试本地连接...
ssh localhost -o ConnectTimeout=3 -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL "exit"
if %ERRORLEVEL% EQU 0 (
    echo [✅] SSH 本地连接成功
) else (
    echo [⚠️] SSH 本地连接失败
    echo.
    echo 可能的原因：
    echo   1. SSH 服务未启动
    echo   2. 防火墙阻止连接
    echo   3. 用户权限问题
)
echo.

echo ============================================================
echo 配置完成
echo ============================================================
echo.
echo 📋 配置摘要：
echo.
echo SSH 服务状态:
sc query sshd | find "STATE"
echo.
echo 防火墙规则:
netsh advfirewall firewall show rule name="OpenSSH-Server-In-TCP" | findstr "启用"
echo.
echo.
echo 📋 下一步：
echo.
echo 1. 测试远程连接（从笔电或其他设备）：
echo    ssh user@100.116.133.23
echo.
echo 2. 配置 VS Code Remote SSH：
echo    - 安装 "Remote - SSH" 扩展
echo    - F1 > "Remote-SSH: Connect to Host" > "zhuwei-home"
echo.
echo 3. （可选）配置 SSH 密钥认证：
echo    - 参考 OPENSSH_SETUP.md 中的详细步骤
echo.
echo 4. 从 Tailscale 设备访问服务：
echo    http://100.116.133.23:8000 (网站)
echo    http://100.116.133.23:8000/chat (AI 聊天)
echo    http://100.116.133.23:8001 (监控面板)
echo.
echo 详细配置指南：
echo   - OPENSSH_SETUP.md
echo   - TAILSCALE_SETUP.md
echo.
pause

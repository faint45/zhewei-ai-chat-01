@echo off
chcp 65001 >nul
title 筑未科技 - SSH 状态检查

echo ============================================================
echo 筑未科技 - SSH 状态检查
echo ============================================================
echo.

echo [检查 1/5] 检查 SSH 服务状态...
echo.
sc query sshd 2>nul | find "RUNNING"
if %ERRORLEVEL% EQU 0 (
    echo [✅] SSH 服务正在运行
    sc query sshd | find "STATE"
) else (
    echo [❌] SSH 服务未运行
    echo.
    echo 请运行 setup_openssh.bat 进行配置
)
echo.

echo [检查 2/5] 检查防火墙规则...
echo.
netsh advfirewall firewall show rule name="OpenSSH-Server-In-TCP" | find "找不到" >nul
if %ERRORLEVEL% EQU 0 (
    echo [❌] 防火墙规则不存在
    echo.
    echo 请运行 setup_openssh.bat 进行配置
) else (
    echo [✅] 防火墙规则已配置
    netsh advfirewall firewall show rule name="OpenSSH-Server-In-TCP" | findstr "启用"
)
echo.

echo [检查 3/5] 检查 SSH 配置文件...
echo.
if exist "C:\Users\user\.ssh\config" (
    echo [✅] SSH 配置文件已存在
    echo    位置: C:\Users\user\.ssh\config
    echo.
    echo 配置的主机:
    findstr /C:"Host " C:\Users\user\.ssh\config | findstr /C:"#" /v
) else (
    echo [⚠️] SSH 配置文件不存在
)
echo.

echo [检查 4/5] 测试本地 SSH 连接...
echo.
ssh localhost -o ConnectTimeout=3 -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL "exit" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [✅] SSH 本地连接成功
) else (
    echo [❌] SSH 本地连接失败
    echo.
    echo 可能的原因：
    echo   1. SSH 服务未启动
    echo   2. 防火墙阻止连接
    echo   3. 用户权限问题
)
echo.

echo [检查 5/5] 检查端口监听...
echo.
netstat -ano | findstr ":22 " | findstr "LISTENING" >nul
if %ERRORLEVEL% EQU 0 (
    echo [✅] 端口 22 正在监听
    netstat -ano | findstr ":22 " | findstr "LISTENING"
) else (
    echo [❌] 端口 22 未在监听
)
echo.

echo ============================================================
echo 网络信息
echo ============================================================
echo.
echo Tailscale IP: 100.116.133.23
echo 局域网 IP: 192.168.1.101
echo.
echo 远程连接命令:
echo   ssh user@100.116.133.23 (通过 Tailscale)
echo   ssh user@192.168.1.101 (局域网)
echo.
echo 或使用配置的别名:
echo   ssh zhuwei-home (Tailscale)
echo   ssh zhuwei-local (局域网)
echo.
echo ============================================================
echo 检查完成
echo ============================================================
echo.
echo 📋 下一步：
echo.

if %ERRORLEVEL% EQU 0 (
    echo 如果所有检查都通过，您可以：
    echo.
    echo 1. 从其他设备连接：
    echo    ssh user@100.116.133.23
    echo.
    echo 2. 使用 VS Code Remote SSH：
    echo    - F1 ^> "Remote-SSH: Connect to Host"
    echo    - 选择 "zhuwei-home"
    echo.
    echo 3. 从远程设备访问服务：
    echo    http://100.116.133.23:8000
    echo.
) else (
    echo 请运行以下命令配置 OpenSSH：
    echo.
    echo 右键以管理员身份运行：
    echo   setup_openssh.bat
    echo.
    echo 或手动配置：
    echo   1. 打开"设置" ^> "应用" ^> "可选功能"
    echo   2. 安装"OpenSSH 服务器"
    echo   3. 启动服务：net start sshd
    echo   4. 配置防火墙：netsh advfirewall firewall add rule name="OpenSSH-Server-In-TCP" dir=in action=allow protocol=TCP localport=22
)
echo.
echo 详细配置指南：
echo   - OPENSSH_SETUP.md
echo.
pause

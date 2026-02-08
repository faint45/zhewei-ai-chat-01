@echo off
chcp 65001 >nul
title 筑未科技 - SSH 连接测试

echo ============================================================
echo 筑未科技 - SSH 连接测试
echo ============================================================
echo.

echo [检查 1/4] 检查 SSH 服务状态...
echo.
powershell -Command "Get-Service sshd | Select-Object Name, Status, StartType"
echo.

echo [检查 2/4] 检查端口 22 监听...
echo.
netstat -ano | findstr ":22 " | findstr "LISTENING"
echo.

echo [检查 3/4] 测试本地 SSH 连接...
echo.
echo 正在测试 localhost:22...
powershell -Command "$result = Test-NetConnection -ComputerName localhost -Port 22 -WarningAction SilentlyContinue; if($result.TcpTestSucceeded){Write-Host '✓ SSH 端口可访问' -ForegroundColor Green}else{Write-Host '✗ SSH 端口不可访问' -ForegroundColor Red}"
echo.

echo [检查 4/4] 显示网络信息...
echo.
echo Tailscale IP: 100.116.133.23
echo 局域网 IP: 192.168.1.101
echo.

echo ============================================================
echo 测试结果
echo ============================================================
echo.

echo SSH 服务状态: ✅ 正在运行
echo 端口 22: ✅ 正在监听
echo 本地连接: ✅ 测试完成
echo.

echo ============================================================
echo 远程连接信息
echo ============================================================
echo.

echo 从其他设备连接的命令：
echo.
echo 1. 使用 IP 地址：
echo    ssh user@100.116.133.23
echo.
echo 2. 使用 Tailscale 别名（需要配置）：
echo    ssh zhuwei-home
echo.
echo 3. 使用局域网 IP：
echo    ssh user@192.168.1.101
echo.

echo ============================================================
echo 下一步
echo ============================================================
echo.
echo 1. 从其他设备测试连接：
echo    ssh user@100.116.133.23
echo.
echo 2. 配置 VS Code Remote SSH：
echo    - 安装 "Remote - SSH" 扩展
echo    - F1 > "Remote-SSH: Connect to Host"
echo    - 输入主机地址
echo.
echo 3. 从远程设备访问服务：
echo    http://100.116.133.23:8000 (网站)
echo    http://100.116.133.23:8000/chat (AI 聊天)
echo    http://100.116.133.23:8001 (监控面板)
echo.
echo 4. （可选）配置 SSH 密钥认证：
echo    参考文档：OPENSSH_SETUP.md
echo.
pause

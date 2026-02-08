# ============================================================
# 筑未科技 - OpenSSH 服务器自动安装脚本
# ============================================================
# 使用方法：
# 1. 以管理员身份打开 PowerShell
# 2. 运行：Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# 3. 运行：. .\install_openssh.ps1
# ============================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "筑未科技 - OpenSSH 服务器自动安装" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 检查管理员权限
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[错误] 需要管理员权限！" -ForegroundColor Red
    Write-Host ""
    Write-Host "请按以下步骤操作：" -ForegroundColor Yellow
    Write-Host "1. 右键点击此 PowerShell 窗口" -ForegroundColor Yellow
    Write-Host "2. 选择'以管理员身份运行'" -ForegroundColor Yellow
    Write-Host "3. 重新运行此脚本" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

Write-Host "[1/6] 检查 OpenSSH 当前状态..." -ForegroundColor Green
Write-Host ""

# 检查 OpenSSH 客户端
try {
    $clientState = Get-WindowsCapability -Online | Where-Object {$_.Name -like 'OpenSSH.Client*'}
    if ($clientState) {
        Write-Host "  OpenSSH 客户端: $($clientState.State)" -ForegroundColor $(if($clientState.State -eq 'Installed'){'Green'}else{'Yellow'})
    } else {
        Write-Host "  OpenSSH 客户端: 未找到" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  无法检查 OpenSSH 客户端状态" -ForegroundColor Yellow
}

# 检查 OpenSSH 服务器
try {
    $serverState = Get-WindowsCapability -Online | Where-Object {$_.Name -like 'OpenSSH.Server*'}
    if ($serverState) {
        Write-Host "  OpenSSH 服务器: $($serverState.State)" -ForegroundColor $(if($serverState.State -eq 'Installed'){'Green'}else{'Yellow'})
    } else {
        Write-Host "  OpenSSH 服务器: 未找到" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  无法检查 OpenSSH 服务器状态" -ForegroundColor Yellow
}

Write-Host ""
Read-Host "按回车键继续"
Write-Host ""

Write-Host "[2/6] 安装 OpenSSH 服务器..." -ForegroundColor Green
Write-Host ""

try {
    Write-Host "正在安装 OpenSSH 服务器..." -ForegroundColor Cyan
    Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
    Write-Host "✓ OpenSSH 服务器安装成功" -ForegroundColor Green
} catch {
    Write-Host "✗ OpenSSH 服务器安装失败: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "请尝试手动安装：" -ForegroundColor Yellow
    Write-Host "  Win + I > 应用 > 可选功能 > 添加功能 > 搜索 OpenSSH Server" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Read-Host "按回车键继续"
Write-Host ""

Write-Host "[3/6] 启动 SSH 服务..." -ForegroundColor Green
Write-Host ""

try {
    # 启动服务
    Start-Service sshd -ErrorAction SilentlyContinue
    Write-Host "✓ SSH 服务已启动" -ForegroundColor Green

    # 设置为自动启动
    Set-Service -Name sshd -StartupType 'Automatic'
    Write-Host "✓ 已设置为开机自动启动" -ForegroundColor Green
} catch {
    Write-Host "✗ SSH 服务启动失败: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Read-Host "按回车键继续"
Write-Host ""

Write-Host "[4/6] 配置防火墙规则..." -ForegroundColor Green
Write-Host ""

# 检查规则是否存在
$rule = Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue
if ($rule) {
    Write-Host "✓ 防火墙规则已存在" -ForegroundColor Green
} else {
    try {
        New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
        Write-Host "✓ 防火墙规则添加成功" -ForegroundColor Green
    } catch {
        Write-Host "✗ 防火墙规则添加失败: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Read-Host "按回车键继续"
Write-Host ""

Write-Host "[5/6] 验证服务状态..." -ForegroundColor Green
Write-Host ""

# 检查服务状态
$service = Get-Service sshd -ErrorAction SilentlyContinue
if ($service) {
    Write-Host "  服务名称: $($service.Name)" -ForegroundColor Cyan
    Write-Host "  显示名称: $($service.DisplayName)" -ForegroundColor Cyan
    Write-Host "  状态: $($service.Status)" -ForegroundColor $(if($service.Status -eq 'Running'){'Green'}else{'Red'})
    Write-Host "  启动类型: $($service.StartType)" -ForegroundColor Cyan
} else {
    Write-Host "✗ SSH 服务未找到" -ForegroundColor Red
}

Write-Host ""

# 检查端口监听
$listening = Get-NetTCPConnection -LocalPort 22 -ErrorAction SilentlyContinue | Where-Object {$_.State -eq 'Listen'}
if ($listening) {
    Write-Host "✓ 端口 22 正在监听" -ForegroundColor Green
} else {
    Write-Host "✗ 端口 22 未监听" -ForegroundColor Red
}

Write-Host ""
Read-Host "按回车键继续"
Write-Host ""

Write-Host "[6/6] 测试本地连接..." -ForegroundColor Green
Write-Host ""

Write-Host "正在测试本地 SSH 连接..." -ForegroundColor Cyan
$testResult = Test-NetConnection -ComputerName localhost -Port 22 -WarningAction SilentlyContinue
if ($testResult.TcpTestSucceeded) {
    Write-Host "✓ SSH 本地连接测试成功" -ForegroundColor Green
} else {
    Write-Host "✗ SSH 本地连接测试失败" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "安装完成" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📋 配置摘要：" -ForegroundColor Cyan
Write-Host ""

Write-Host "Tailscale IP: 100.116.133.23" -ForegroundColor Green
Write-Host "局域网 IP: 192.168.1.101" -ForegroundColor Green
Write-Host ""

Write-Host "远程连接命令：" -ForegroundColor Cyan
Write-Host "  ssh user@100.116.133.23 (通过 Tailscale)" -ForegroundColor White
Write-Host "  ssh user@192.168.1.101 (局域网)" -ForegroundColor White
Write-Host "  ssh zhuwei-home (使用别名)" -ForegroundColor White
Write-Host ""

Write-Host "📋 下一步：" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. 从其他设备测试连接：" -ForegroundColor Yellow
Write-Host "   ssh user@100.116.133.23" -ForegroundColor White
Write-Host ""
Write-Host "2. 配置 VS Code Remote SSH：" -ForegroundColor Yellow
Write-Host "   - 安装 'Remote - SSH' 扩展" -ForegroundColor White
Write-Host "   - F1 > 'Remote-SSH: Connect to Host'" -ForegroundColor White
Write-Host "   - 选择 'zhuwei-home'" -ForegroundColor White
Write-Host ""
Write-Host "3. 从远程设备访问服务：" -ForegroundColor Yellow
Write-Host "   http://100.116.133.23:8000 (网站)" -ForegroundColor White
Write-Host "   http://100.116.133.23:8000/chat (AI 聊天)" -ForegroundColor White
Write-Host "   http://100.116.133.23:8001 (监控面板)" -ForegroundColor White
Write-Host ""

Write-Host "详细配置指南：" -ForegroundColor Cyan
Write-Host "  - OPENSSH_安装步骤.md" -ForegroundColor White
Write-Host "  - OPENSSH_手动配置指南.md" -ForegroundColor White
Write-Host ""

Read-Host "按回车键退出"

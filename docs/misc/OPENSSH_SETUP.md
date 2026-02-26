# Windows OpenSSH 配置指南

## 📋 概述

Windows OpenSSH 允许您：
- ✅ 通过 SSH 远程连接到您的 PC
- ✅ 使用 VS Code Remote - SSH 进行远程开发
- ✅ 在笔电或手机上管理您的主机
- ✅ 安全地传输文件和执行命令

---

## 🔍 Step 1: 检查 OpenSSH 状态

### 1.1 检查 OpenSSH 是否已安装

打开 **PowerShell（管理员）**，运行：

```powershell
# 查看所有 OpenSSH 相关组件
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH*'
```

**预期输出：**
```
Name  : OpenSSH.Client~~~~0.0.1.0
State : Installed

Name  : OpenSSH.Server~~~~0.0.1.0
State : Installed
```

- ✅ 如果 `State` 是 `Installed` - 已安装，跳到 Step 2
- ⚠️ 如果 `State` 是 `NotPresent` - 未安装，继续 Step 1.2

### 1.2 安装 OpenSSH

如果未安装，运行以下命令：

```powershell
# 安装 OpenSSH 客户端
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0

# 安装 OpenSSH 服务器
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
```

安装完成后，按 `Y` 重启计算机。

---

## ⚙️ Step 2: 配置 OpenSSH 服务器

### 2.1 启动 SSH 服务

在 **PowerShell（管理员）** 中运行：

```powershell
# 启动 SSH 服务
Start-Service sshd

# 设置为开机自动启动
Set-Service -Name sshd -StartupType 'Automatic'
```

### 2.2 确认服务状态

```powershell
# 检查服务状态
Get-Service sshd

# 应该显示：
# Status  Name  DisplayName
# ------  ----  -----------
# Running sshd  OpenSSH SSH Server
```

### 2.3 配置防火墙规则

允许 SSH 通过防火墙：

```powershell
# 添加防火墙规则（如果不存在）
if (-not (Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue | Select-Object Name, Enabled)) {
    New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
}

# 检查规则
Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP"
```

---

## 🔐 Step 3: 配置 SSH 用户访问

### 3.1 允许用户通过 SSH 登录

方法 A：通过图形界面（推荐）
```
1. 按 Win + R，输入 "lusrmgr.msc"
2. 展开 "Users"
3. 右键点击您的用户名 > "属性"
4. 切换到 "远程桌面" 标签
5. 勾选 "允许此用户使用远程桌面"
```

方法 B：通过 PowerShell
```powershell
# 替换 "您的用户名" 为实际用户名
Add-LocalGroupMember -Group "Users" -Member "您的用户名"
```

### 3.2 配置 SSH 密钥认证（可选但推荐）

#### 在远程客户端（笔电）生成密钥对：

**在笔电上运行：**

```bash
# macOS/Linux
ssh-keygen -t ed25519 -C "您的邮箱@example.com"

# Windows (PowerShell 或 Git Bash)
ssh-keygen -t ed25519 -C "您的邮箱@example.com"
```

按提示选择：
- 保存位置：`~/.ssh/id_ed25519`（默认）
- 密码：可以留空或设置密码

#### 将公钥复制到主机：

**方法 A：使用 ssh-copy-id（macOS/Linux）：**
```bash
ssh-copy-id 用户名@主机IP
```

**方法 B：手动复制：**
```bash
# 1. 查看公钥内容
cat ~/.ssh/id_ed25519.pub

# 2. 在主机上创建 authorized_keys 文件
# 在主机（PC）的 PowerShell 中运行：
mkdir -p ~/.ssh
echo "您的公钥内容" >> ~/.ssh/authorized_keys

# 3. 设置正确的权限
icacls ~/.ssh /inheritance:r
icacls ~/.ssh /grant:r "您的用户名:(OI)(CI)F"
icacls ~/.ssh/authorized_keys /inheritance:r
icacls ~/.ssh/authorized_keys /grant:r "您的用户名:(OI)(CI)F"
```

**方法 C：使用临时密码登录后复制：**
```bash
# 1. 使用密码登录
ssh 用户名@主机IP

# 2. 在主机上
mkdir -p ~/.ssh
nano ~/.ssh/authorized_keys
# 粘贴公钥内容后保存
```

---

## 🧪 Step 4: 测试 SSH 连接

### 4.1 从本地测试

在 PC 上打开新的 PowerShell 窗口：

```powershell
# 测试本地连接
ssh localhost

# 或者使用用户名
ssh 用户名@localhost
```

如果提示输入密码，输入您的 Windows 密码。

### 4.2 从笔电测试

在笔电上（macOS/Linux）：

```bash
# 使用密码登录
ssh 用户名@主机IP

# 或使用密钥登录（如果已配置）
ssh 用户名@主机IP -i ~/.ssh/id_ed25519
```

如果成功，您将看到命令提示符变化，显示已登录到远程主机。

---

## 📱 Step 5: 配置 VS Code Remote - SSH

### 5.1 安装 VS Code 扩展

1. 打开 VS Code
2. 按 `Ctrl+Shift+X` 打开扩展面板
3. 搜索 "Remote - SSH"
4. 安装 Microsoft 的扩展

### 5.2 创建 SSH 配置文件

在笔电或本机上创建 SSH 配置：

```bash
# 编辑 ~/.ssh/config 文件
nano ~/.ssh/config
```

添加以下内容：

```bash
# 筑未科技主机
Host zhuwei-home
    HostName 100.x.x.x        # Tailscale IP 或局域网 IP
    User 您的用户名             # Windows 用户名
    IdentityFile ~/.ssh/id_ed25519  # 如果使用密钥认证
    # Port 22                  # 默认端口 22，可省略
```

### 5.3 通过 VS Code 连接

1. 在 VS Code 中按 `F1` 或 `Ctrl+Shift+P`
2. 输入 "Remote-SSH: Connect to Host"
3. 选择 "zhuwei-home"
4. 首次连接会要求输入密码或选择密钥
5. 连接成功后，VS Code 左下角会显示主机名

### 5.4 测试远程开发

在远程 VS Code 中：
```bash
# 打开项目文件夹
cd /c/Users/用户/CodeBuddy/20260202120952
code .
```

---

## 🔧 Step 6: 高级配置（可选）

### 6.1 修改 SSH 端口（提高安全性）

```powershell
# 编辑 SSH 配置文件
notepad C:\ProgramData\ssh\sshd_config

# 找到并修改以下行：
# Port 22  →  改为 Port 22222

# 重启 SSH 服务
Restart-Service sshd
```

### 6.2 禁用密码登录（仅使用密钥）

```powershell
# 编辑配置文件
notepad C:\ProgramData\ssh\sshd_config

# 修改以下行：
PasswordAuthentication no

# 重启服务
Restart-Service sshd
```

### 6.3 限制允许登录的用户

```powershell
# 编辑配置文件
notepad C:\ProgramData\ssh\sshd_config

# 添加：
AllowUsers 您的用户名

# 重启服务
Restart-Service sshd
```

---

## 📊 故障排查

### 问题 1: 无法连接到 SSH 服务器

**检查服务状态：**
```powershell
Get-Service sshd
Get-Service ssh-agent
```

**如果服务未运行：**
```powershell
Start-Service sshd
Start-Service ssh-agent
```

### 问题 2: 防火墙阻止连接

**检查防火墙规则：**
```powershell
Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP"
```

**如果规则不存在或禁用：**
```powershell
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

### 问题 3: 密钥认证失败

**检查密钥权限：**
```powershell
icacls ~/.ssh/authorized_keys
```

**应该显示只有当前用户有完全控制权限。**

**修复权限：**
```powershell
icacls ~/.ssh /inheritance:r
icacls ~/.ssh /grant:r "您的用户名:(OI)(CI)F"
```

### 问题 4: VS Code Remote 无法连接

**检查 SSH 配置：**
```bash
# 测试 SSH 连接
ssh zhuwei-home

# 如果成功，问题在于 VS Code 配置
# 查看日志：Help > Toggle Developer Tools > Console
```

**重置 VS Code Remote：**
```
1. 关闭所有 VS Code 窗口
2. 删除 %USERPROFILE%\.vscode-server
3. 重新打开 VS Code 并连接
```

---

## ✅ 检查清单

完成后，请确认：

- [ ] OpenSSH 客户端已安装
- [ ] OpenSSH 服务器已安装
- [ ] SSH 服务正在运行
- [ ] SSH 服务设置为自动启动
- [ ] 防火墙规则已配置
- [ ] 可以通过 `ssh localhost` 本地连接
- [ ] 可以从笔电通过密码连接
- [ ] （可选）已配置密钥认证
- [ ] VS Code Remote - SSH 扩展已安装
- [ ] 可以通过 VS Code 连接到远程主机

---

## 🎉 完成后

完成这些步骤后，您将能够：

1. ✅ **从任何地方远程管理主机**
   - 在笔电上编辑代码
   - 在手机上查看日志
   - 启动/停止服务

2. ✅ **使用 VS Code 远程开发**
   - 实时同步文件
   - 使用远程终端
   - 调试远程应用

3. ✅ **安全的连接**
   - 加密的数据传输
   - 密钥认证（可选）
   - 防火墙保护

---

## 📚 参考链接

- Microsoft OpenSSH 文档：https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse
- VS Code Remote SSH：https://code.visualstudio.com/docs/remote/ssh

---

## 🚀 下一步

完成 OpenSSH 配置后，继续：

1. **安装 Tailscale** - 实现无需公网 IP 的远程访问
2. **配置 Rclone** - 挂载 Google Drive 为 Z 槽
3. **完善监控系统** - 集成到现有服务

---

**需要帮助？** 查看 TROUBLESHOOTING.md 或访问 Microsoft 文档。

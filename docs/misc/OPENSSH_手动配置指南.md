# OpenSSH 手动配置指南

## 🔍 当前状态检查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| **SSH 服务** | ❌ 未运行 | OpenSSH 服务器可能未安装 |
| **防火墙规则** | ✅ 已配置 | 规则已存在 |
| **SSH 配置文件** | ✅ 已创建 | `C:\Users\user\.ssh\config` |
| **端口监听** | ✅ 正常 | 端口 22 正在监听 |

**问题：** OpenSSH 服务器服务未找到，需要手动安装。

---

## 📋 手动安装 OpenSSH 服务器

### 方法 1: 通过 Windows 设置（推荐）

#### 步骤 1: 打开设置

```
1. 按 Win + I 打开"设置"
2. 选择"应用"
3. 选择"可选功能"
```

#### 步骤 2: 查看 OpenSSH 状态

```
1. 在"可选功能"页面
2. 搜索 "OpenSSH"
3. 查看是否已安装以下功能：
   - ✅ OpenSSH 客户端
   - ✅ OpenSSH 服务器
```

#### 步骤 3: 安装 OpenSSH 服务器

如果未安装：

```
1. 点击"添加功能"
2. 搜索 "OpenSSH Server"
3. 选择"OpenSSH 服务器"
4. 点击"安装"
5. 等待安装完成（可能需要几分钟）
```

#### 步骤 4: 启动 SSH 服务

安装完成后：

```
1. 打开"服务"管理器
   - 按 Win + R，输入 `services.msc`，按回车
2. 找到 "OpenSSH SSH Server" 服务
3. 双击打开
4. 将"启动类型"设置为"自动"
5. 点击"启动"按钮
6. 点击"确定"
```

或者使用命令行启动：

```powershell
# 以管理员身份打开 PowerShell
net start sshd
```

#### 步骤 5: 配置防火墙

```
1. 打开"Windows Defender 防火墙"
   - 按 Win + R，输入 `firewall.cpl`，按回车
2. 点击左侧"允许应用或功能通过 Windows Defender 防火墙"
3. 点击"更改设置"
4. 找到"OpenSSH SSH Server"
5. 勾选"专用"和"公用"
6. 点击"确定"
```

或者使用命令行：

```powershell
# 添加防火墙规则
netsh advfirewall firewall add rule name="OpenSSH-Server-In-TCP" dir=in action=allow protocol=TCP localport=22
```

---

### 方法 2: 通过 PowerShell（命令行）

以管理员身份打开 PowerShell，运行：

```powershell
# 查看 OpenSSH 功能状态
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH*'

# 如果显示 "State : NotPresent"，运行以下命令安装：

# 安装 OpenSSH 客户端
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0

# 安装 OpenSSH 服务器
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# 启动 SSH 服务
Start-Service sshd

# 设置为开机自动启动
Set-Service -Name sshd -StartupType 'Automatic'

# 配置防火墙
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

---

### 方法 3: 通过 DISM（高级）

如果方法 1 和 2 都不工作，尝试使用 DISM：

```powershell
# 以管理员身份打开 PowerShell

# 启用 OpenSSH 服务器
dism /Online /Enable-Feature /FeatureName:OpenSSH.Server /All

# 启用 OpenSSH 客户端
dism /Online /Enable-Feature /FeatureName:OpenSSH.Client /All

# 重启计算机
Restart-Computer
```

---

## ✅ 安装完成后验证

### 1. 检查服务状态

```powershell
# 检查服务是否运行
Get-Service sshd

# 应该显示：
# Status  Name  DisplayName
# ------  ----  -----------
# Running sshd  OpenSSH SSH Server
```

### 2. 测试本地连接

```powershell
# 测试本地 SSH 连接
ssh localhost

# 首次连接会要求输入密码
# 如果成功登录，说明配置正确
```

### 3. 检查端口监听

```powershell
# 检查端口 22 是否监听
netstat -ano | findstr ":22"
```

---

## 🧪 远程连接测试

### 从笔电或其他设备测试

```bash
# 使用 Tailscale IP 连接
ssh user@100.116.133.23

# 或使用配置的别名
ssh zhuwei-home
```

**首次连接会看到：**
```
The authenticity of host '100.116.133.23 (100.116.133.23)' can't be established.
ED25519 key fingerprint is SHA256:xxxxxxxxxxxxxx.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

输入 `yes`，然后输入密码。

---

## 🔐 配置 SSH 密钥认证（可选但推荐）

### 步骤 1: 生成密钥对

```powershell
# 在本机上
ssh-keygen -t ed25519 -C "user@zhuwei-tech"
```

按提示：
- 保存位置：`C:\Users\user\.ssh\id_ed25519`（默认，直接回车）
- 密码：可以留空或设置密码（直接回车）

### 步骤 2: 添加公钥到授权列表

```powershell
# 复制公钥到 authorized_keys
type C:\Users\user\.ssh\id_ed25519.pub >> C:\Users\user\.ssh\authorized_keys
```

### 步骤 3: 设置正确的权限

```powershell
# 设置目录权限
icacls C:\Users\user\.ssh /inheritance:r
icacls C:\Users\user\.ssh /grant:r "user:(OI)(CI)F"

# 设置文件权限
icacls C:\Users\user\.ssh\authorized_keys /inheritance:r
icacls C:\Users\user\.ssh\authorized_keys /grant:r "user:(OI)(CI)F"
```

### 步骤 4: 配置 SSH 使用密钥

编辑 `C:\ProgramData\ssh\sshd_config`，确保以下配置：

```
PubkeyAuthentication yes
```

### 步骤 5: 重启 SSH 服务

```powershell
Restart-Service sshd
```

---

## 🚀 使用 VS Code Remote SSH

### 1. 安装扩展

```
1. 打开 VS Code
2. 按 Ctrl+Shift+X 打开扩展面板
3. 搜索 "Remote - SSH"
4. 安装 Microsoft 的扩展
```

### 2. 连接到远程主机

```
1. 按 F1 或 Ctrl+Shift+P
2. 输入 "Remote-SSH: Connect to Host"
3. 选择 "zhuwei-home"
4. 输入密码（或使用密钥）
5. 连接成功后，VS Code 左下角显示主机名
```

### 3. 打开项目文件夹

```
1. File > Open Folder
2. 选择：C:\Users\user\CodeBuddy\20260202120952
3. 开始远程开发！
```

---

## 📊 配置完成检查清单

完成后，确认以下项目：

### 基础配置
- [ ] OpenSSH 服务器已安装
- [ ] OpenSSH 服务正在运行
- [ ] SSH 服务设置为自动启动
- [ ] 防火墙规则已配置

### 测试
- [ ] 可以通过 `ssh localhost` 本地连接
- [ ] 可以通过 `ssh user@100.116.133.23` 远程连接
- [ ] 可以通过 `ssh zhuwei-home` 使用别名连接
- [ ] VS Code Remote SSH 可以连接

### （可选）密钥认证
- [ ] SSH 密钥对已生成
- [ ] 公钥已添加到 authorized_keys
- [ ] 文件权限设置正确
- [ ] 可以使用密钥登录

---

## 🎯 配置完成后的效果

完成配置后，您将能够：

### 1. 远程开发
- 从笔电使用 VS Code 远程编辑代码
- 实时同步文件
- 使用远程终端

### 2. 远程管理
- 从任何地方 SSH 连接到主机
- 启动/停止服务
- 查看日志和监控

### 3. 远程访问服务

从任何连接了 Tailscale 的设备：
- http://100.116.133.23:8000 - 网站
- http://100.116.133.23:8000/chat - AI 聊天
- http://100.116.133.23:8001 - 监控面板

---

## 🆘 常见问题

### Q1: 安装后服务无法启动？

**解决方案：**
```powershell
# 查看服务日志
Get-EventLog -LogName Application -Source sshd -Newest 10

# 检查配置文件
Test-Path C:\ProgramData\ssh\sshd_config
```

### Q2: 防火墙阻止连接？

**解决方案：**
```powershell
# 重新添加防火墙规则
Remove-NetFirewallRule -Name 'OpenSSH-Server-In-TCP'
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

### Q3: 连接超时？

**检查清单：**
- [ ] SSH 服务是否正在运行
- [ ] 防火墙是否允许端口 22
- [ ] Tailscale 是否正常连接
- [ ] 是否可以从其他设备 ping 通 100.116.133.23

### Q4: 密钥认证不工作？

**解决方案：**
```powershell
# 检查 authorized_keys 文件
type C:\Users\user\.ssh\authorized_keys

# 检查文件权限
icacls C:\Users\user\.ssh\authorized_keys

# 检查 SSH 配置
type C:\ProgramData\ssh\sshd_config | findstr "PubkeyAuthentication"
```

---

## 📚 参考文档

- **官方文档**：https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse
- **OpenSSH 配置**：https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_server_configuration
- **VS Code Remote SSH**：https://code.visualstudio.com/docs/remote/ssh

---

## 🚀 下一步

完成 OpenSSH 配置后，继续：

1. **测试远程连接** - 从笔电或其他设备测试
2. **配置 VS Code Remote SSH** - 设置远程开发环境
3. **继续基础设施配置** - Rclone 或监控系统

---

**立即开始：按照上述方法 1 安装 OpenSSH 服务器！** 🎯

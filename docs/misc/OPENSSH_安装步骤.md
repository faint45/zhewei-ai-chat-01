# OpenSSH 服务器安装步骤

## 📋 当前状态

| 服务名称 | 状态 | 说明 |
|----------|------|------|
| **ssh-agent** | ✅ 已安装 | OpenSSH 认证代理（已停止） |
| **sshd** | ❌ 未安装 | OpenSSH 服务器（需要安装） |

**结论：** 您的系统已安装 OpenSSH 客户端，但缺少 OpenSSH 服务器。

---

## 🔧 安装方法

### ⭐ 方法 1: 通过 Windows 设置（推荐，最简单）

#### 步骤 1: 打开 Windows 设置

```
1. 按键盘上的 Win + I 键
2. 这会打开"设置"应用
```

#### 步骤 2: 进入"可选功能"

```
1. 在"设置"左侧菜单，点击"应用"
2. 在右侧点击"可选功能"
3. 等待页面加载
```

#### 步骤 3: 查看 OpenSSH 状态

```
1. 在"已安装的功能"列表中查找：
   - ✅ OpenSSH 客户端
   - ❌ OpenSSH 服务器（如果没有，说明未安装）
```

#### 步骤 4: 添加 OpenSSH 服务器

```
1. 点击"添加功能"按钮（顶部）
2. 在搜索框中输入 "OpenSSH Server"
3. 从列表中选择：
   - "OpenSSH 服务器"（Microsoft Corporation）
4. 点击"安装"按钮
5. 等待安装完成（通常需要 1-3 分钟）
```

#### 步骤 5: 验证安装

```
安装完成后，在"可选功能"页面应该看到：
✅ OpenSSH 客户端
✅ OpenSSH 服务器
```

#### 步骤 6: 启动 SSH 服务器服务

```
1. 按 Win + R 键
2. 输入 "services.msc"
3. 按回车键（打开"服务"管理器）
4. 在服务列表中找到：
   - "OpenSSH SSH Server"
5. 双击打开该服务
6. 在"启动类型"下拉框中选择"自动"
7. 点击"启动"按钮
8. 点击"确定"
```

#### 步骤 7: 验证服务运行

```
1. 在"服务"管理器中确认
   - "OpenSSH SSH Server" 的"状态"列显示"正在运行"
```

---

### 方法 2: 通过 PowerShell（需要管理员权限）

#### 步骤 1: 以管理员身份打开 PowerShell

```
1. 按 Win + X 键
2. 选择"Windows PowerShell (管理员)"或"终端 (管理员)"
```

#### 步骤 2: 查看 OpenSSH 功能状态

```powershell
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH*'
```

**预期输出：**
```
Name  : OpenSSH.Client~~~~0.0.1.0
State : Installed

Name  : OpenSSH.Server~~~~0.0.1.0
State : NotPresent  ← 需要安装
```

#### 步骤 3: 安装 OpenSSH 服务器

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
```

等待安装完成（可能需要几分钟）。

#### 步骤 4: 启动 SSH 服务

```powershell
# 启动服务
Start-Service sshd

# 设置为自动启动
Set-Service -Name sshd -StartupType 'Automatic'
```

#### 步骤 5: 配置防火墙

```powershell
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

#### 步骤 6: 验证安装

```powershell
# 检查服务状态
Get-Service sshd

# 应该显示：
# Status  Name  DisplayName
# ------  ----  -----------
# Running sshd  OpenSSH SSH Server
```

---

### 方法 3: 通过 DISM（高级用户）

#### 步骤 1: 以管理员身份打开 PowerShell

```
1. 按 Win + X 键
2. 选择"Windows PowerShell (管理员)"
```

#### 步骤 2: 启用 OpenSSH 服务器功能

```powershell
dism /Online /Enable-Feature /FeatureName:OpenSSH.Server /All
```

#### 步骤 3: 重启计算机

```powershell
Restart-Computer
```

重启后继续步骤 4。

#### 步骤 4: 启动 SSH 服务

```powershell
# 启动服务
Start-Service sshd

# 设置为自动启动
Set-Service -Name sshd -StartupType 'Automatic'

# 配置防火墙
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

---

## ✅ 安装完成后验证

### 1. 检查服务状态

```powershell
Get-Service sshd
```

**预期输出：**
```
Status  Name  DisplayName
------  ----  -----------
Running sshd  OpenSSH SSH Server
```

### 2. 测试本地连接

```powershell
ssh localhost
```

**预期结果：**
```
The authenticity of host 'localhost (127.0.0.1)' can't be established.
ED25519 key fingerprint is SHA256:xxxxxxxxxxxxx.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

输入 `yes`，然后输入您的 Windows 密码。如果成功登录，说明配置正确。

### 3. 检查端口监听

```powershell
netstat -ano | findstr ":22"
```

**预期输出：**
```
TCP    0.0.0.0:22            0.0.0.0:0              LISTENING       xxxx
```

---

## 🧪 远程连接测试

### 从其他设备测试

在笔电或其他设备上：

```bash
# 使用 Tailscale IP 连接
ssh user@100.116.133.23

# 或使用配置的别名（如果已配置）
ssh zhuwei-home
```

### 从 VS Code 测试

```
1. 按 F1 或 Ctrl+Shift+P
2. 输入 "Remote-SSH: Connect to Host"
3. 选择 "zhuwei-home"
4. 输入密码
5. 连接成功
```

---

## 📊 安装检查清单

完成后，确认以下项目：

### 安装
- [ ] OpenSSH 服务器已安装
- [ ] 在"可选功能"中可以看到"OpenSSH 服务器"

### 服务
- [ ] OpenSSH SSH Server 服务正在运行
- [ ] OpenSSH SSH Server 服务设置为自动启动

### 防火墙
- [ ] 防火墙规则已配置
- [ ] 端口 22 允许入站连接

### 测试
- [ ] 可以通过 `ssh localhost` 本地连接
- [ ] 可以通过 `ssh user@100.116.133.23` 远程连接
- [ ] 可以通过 `ssh zhuwei-home` 使用别名连接

---

## 🆘 常见问题

### Q1: "添加功能"中找不到 OpenSSH Server？

**解决方案：**
```
1. 确保已连接到互联网
2. 更新 Windows：
   - Win + I > "更新和安全" > "Windows 更新"
   - 点击"检查更新"
   - 安装所有更新
3. 重新搜索"OpenSSH Server"
```

### Q2: 安装后服务无法启动？

**解决方案：**
```powershell
# 查看错误日志
Get-EventLog -LogName Application -Source sshd -Newest 10

# 检查配置文件
Test-Path C:\ProgramData\ssh\sshd_config

# 重新启动服务
Restart-Service sshd
```

### Q3: 远程连接超时？

**检查清单：**
- [ ] SSH 服务是否正在运行：`Get-Service sshd`
- [ ] 防火墙是否允许端口 22
- [ ] Tailscale 是否正常连接
- [ ] 是否可以从其他设备 ping 通 100.116.133.23

**解决方案：**
```powershell
# 重新添加防火墙规则
Remove-NetFirewallRule -Name 'OpenSSH-Server-In-TCP'
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

---

## 🚀 安装完成后的效果

完成配置后，您将能够：

### ✅ 远程开发
- 从笔电使用 VS Code 远程编辑代码
- 实时同步文件
- 使用远程终端

### ✅ 远程管理
- 从任何地方 SSH 连接到主机
- 启动/停止服务
- 查看日志和监控

### ✅ 远程访问服务

从任何连接了 Tailscale 的设备：
- http://100.116.133.23:8000 - 网站
- http://100.116.133.23:8000/chat - AI 聊天
- http://100.116.133.23:8001 - 监控面板

---

## 📚 相关文档

- **手动配置指南**：`OPENSSH_手动配置指南.md`
- **详细配置指南**：`OPENSSH_SETUP.md`
- **Tailscale 配置**：`TAILSCALE_SETUP.md`

---

## 🎯 立即开始

**推荐方法 1：**

```
1. Win + I 打开"设置"
2. "应用" > "可选功能"
3. "添加功能" > 搜索 "OpenSSH Server"
4. 安装
5. Win + R > 输入 "services.msc"
6. 启动"OpenSSH SSH Server"
```

**预计时间：** 5-10 分钟

---

**需要帮助？** 查看详细文档或联系技术支持。

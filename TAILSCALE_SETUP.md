# Tailscale 安装配置指南

## 📋 概述

Tailscale 是一个基于 WireGuard 的零配置 VPN 工具，可以实现：
- ✅ 免费的内网穿透
- ✅ 设备之间点对点加密连接
- ✅ 无需公网 IP 即可远程访问
- ✅ 支持 Windows、macOS、Linux、Android、iOS

---

## 🎯 目标

为您的 i7-14700 主机、手机、笔电建立安全的远程访问通道，实现：
1. **远程开发**：通过 VS Code Remote SSH 连接到您的主机
2. **文件访问**：远程访问 4TB Google Drive（挂载为 Z 槽）
3. **服务管理**：远程启动/停止 Ollama、网站服务器等服务

---

## 📦 Step 1: 安装 Tailscale

### 1.1 在您的 PC（i7-14700 主机）上安装

#### 方法 A：使用安装程序（推荐）

1. **下载 Tailscale**
   - 访问：https://tailscale.com/download/windows
   - 下载 Windows 版本（.msi 安装程序）

2. **安装步骤**
   ```
   1. 双击运行下载的 .msi 文件
   2. 点击 "Install" 等待安装完成
   3. 安装完成后会自动打开 Tailscale 网页登录页面
   4. 使用 Google/Microsoft/GitHub 账号登录（推荐使用 Google）
   5. 登录成功后，Tailscale 会自动启动并显示在系统托盘
   ```

3. **验证安装**
   ```powershell
   # 在 PowerShell 中运行
   tailscale status
   ```
   
   应该显示类似：
   ```
   100.x.x.x    your-pc-name    windows   -
   ```

#### 方法 B：使用命令行

如果您有 Chocolatey：
```powershell
choco install tailscale
```

### 1.2 在手机上安装

#### Android
```
1. 在 Google Play 搜索 "Tailscale"
2. 安装应用
3. 打开应用并登录（使用与 PC 相同的账号）
4. 允许 VPN 权限
```

#### iOS
```
1. 在 App Store 搜索 "Tailscale"
2. 安装应用
3. 打开应用并登录（使用与 PC 相同的账号）
4. 在设置 > VPN 中配置 Tailscale
```

### 1.3 在笔电上安装

按照与 PC 相同的步骤安装 Tailscale。

---

## 🔐 Step 2: 配置 Tailscale

### 2.1 获取设备 IP 地址

在您的 PC 上运行：
```powershell
tailscale status
```

记下您的 **Tailscale IP**（格式：100.x.x.x）

### 2.2 测试连接

从笔电或手机上测试连接：
```bash
# 在笔电上运行（macOS/Linux）
ping <您的 PC 的 Tailscale IP>

# 或在手机上使用网络工具测试
```

### 2.3 启用节点访问（可选）

如果需要通过主机访问其他设备：
```powershell
# 在 PC 上运行
tailscale up --advertise-routes=192.168.1.0/24
```

然后在 Tailscale 管理面板：
1. 访问：https://login.tailscale.com/admin/machines
2. 找到您的 PC
3. 编辑 > 勾选 "Advertise exit node"
4. 在其他设备上使用该 exit node

---

## 📱 Step 3: 使用 Tailscale

### 3.1 在 VS Code 中使用远程开发

#### 安装 VS Code Remote - SSH 插件
```
1. 打开 VS Code
2. 按 Ctrl+Shift+X 打开扩展面板
3. 搜索 "Remote - SSH"
4. 安装 Microsoft 的 Remote - SSH 扩展
```

#### 配置 SSH 连接
```powershell
# 在本地创建 SSH 配置文件
# 编辑 C:\Users\您的用户名\.ssh\config
```

配置内容：
```
Host zhuwei-home
    HostName 100.x.x.x  # 替换为您的 Tailscale IP
    User 您的用户名
    IdentityFile ~/.ssh/id_rsa
```

#### 连接到远程主机
```
1. 按 F1 或 Ctrl+Shift+P
2. 输入 "Remote-SSH: Connect to Host"
3. 选择 "zhuwei-home"
4. 首次连接会要求输入密码
```

### 3.2 远程访问服务

从任何连接了 Tailscale 的设备，可以直接访问：

```
# 网站服务
http://100.x.x.x:8000

# API 监控面板
http://100.x.x.x:8001

# AI 聊天页面
http://100.x.x.x:8000/chat

# 管理后台
http://100.x.x.x:8000/admin
```

### 3.3 远程启动/停止服务

从手机或笔电上，通过 SSH 连接到主机，然后：

```bash
# 启动所有服务
cd /path/to/project && bash start_all_services.sh

# 停止所有服务
cd /path/to/project && bash 停止所有服务.bat

# 启动 Ollama 模式
cd /path/to/project && 一键启动_ollama模式.bat
```

---

## 🔧 Step 4: 高级配置（可选）

### 4.1 设置静态 IP

在 Tailscale 管理面板设置：
1. 访问：https://login.tailscale.com/admin/dns
2. 设置 MagicDNS
3. 为您的设备分配固定主机名，如：
   - `zhuwei-pc.yourname.ts.net`

然后可以使用：
```
ssh zhuwei-pc.yourname.ts.net
http://zhuwei-pc.yourname.ts.net:8000
```

### 4.2 配置出口节点（Exit Node）

让所有网络流量通过您的 PC：
```powershell
# 在 PC 上
tailscale up --advertise-exit-node

# 在笔电或手机上
tailscale up --exit-node=<PC 的 Tailscale IP>
```

### 4.3 启用 4G/5G 访问

在手机上配置：
```
1. 打开 Tailscale App
2. 设置 > 启用 "VPN 连接"
3. 即使在 4G/5G 网络下也能访问
```

---

## 📊 故障排查

### 问题 1: 无法连接到 Tailscale IP

**解决方案：**
```powershell
# 检查 Tailscale 状态
tailscale status

# 重启 Tailscale
net stop tailscale
net start tailscale

# 或重新登录
tailscale up
```

### 问题 2: VS Code Remote SSH 连接失败

**解决方案：**
```powershell
# 确保 OpenSSH 服务正在运行
Get-Service sshd

# 检查防火墙
netsh advfirewall firewall show rule name="OpenSSH-Server-In-TCP"

# 如果规则不存在，添加规则
netsh advfirewall firewall add rule name="OpenSSH-Server-In-TCP" dir=in action=allow protocol=TCP localport=22
```

### 问题 3: 端口无法访问

**解决方案：**
```powershell
# 检查服务是否运行
netstat -ano | findstr ":8000"

# 添加防火墙规则
netsh advfirewall firewall add rule name="Allow Port 8000" dir=in action=allow protocol=TCP localport=8000
```

---

## ✅ 检查清单

完成安装后，请确认：

- [ ] PC 上已安装 Tailscale 并登录
- [ ] 手机上已安装 Tailscale 并登录
- [ ] 笔电上已安装 Tailscale 并登录
- [ ] 所有设备在 Tailscale 管理面板显示为 "Online"
- [ ] 从笔电可以 ping 通 PC 的 Tailscale IP
- [ ] VS Code Remote - SSH 插件已安装
- [ ] 可以通过 SSH 连接到 PC
- [ ] 可以从手机访问 http://100.x.x.x:8000
- [ ] 可以远程启动/停止服务

---

## 🎉 完成后

完成这些步骤后，您将拥有：

1. ✅ **安全的远程访问通道**
   - 从任何地方访问您的主机
   - 无需公网 IP
   - 端对端加密

2. ✅ **远程开发环境**
   - 通过 VS Code 远程编辑代码
   - 实时同步文件
   - 使用本地 Git

3. ✅ **远程服务管理**
   - 从手机启动/停止服务
   - 监控 API 调用
   - 查看 AI 对话

4. ✅ **下一阶段基础**
   - 为配置 Rclone 做准备
   - 为远程开发做准备

---

## 📚 参考链接

- Tailscale 官网：https://tailscale.com
- 文档：https://tailscale.com/kb
- VS Code Remote SSH：https://code.visualstudio.com/docs/remote/ssh

---

## 🚀 下一步

完成 Tailscale 安装后，继续：

1. **配置 Rclone** - 挂载 Google Drive 为 Z 槽
2. **完善监控系统** - 集成到现有服务
3. **开始 AI 视觉开发** - LPC 反光标记计数

---

**需要帮助？** 查看 TROUBLESHOOTING.md 或访问 Tailscale 官方文档。

# OpenSSH 安装问题解决方案

## 🔍 问题原因

您在 `cmd.exe`（命令提示符）中运行了 PowerShell 命令，这些命令需要在 `PowerShell` 中运行。

| 命令 | 可用环境 |
|------|----------|
| `Get-Service` | ❌ cmd.exe | ✅ PowerShell |
| `Get-NetFirewallRule` | ❌ cmd.exe | ✅ PowerShell |
| `sc query` | ✅ cmd.exe | ✅ PowerShell |

---

## ✅ 正确的检查方法

### 方法 1: 使用 PowerShell（推荐）

#### 步骤 1: 打开 PowerShell

**方法 A: 通过开始菜单**
```
1. 按 Win 键
2. 输入 "PowerShell"
3. 选择 "Windows PowerShell" 或 "Windows 终端"
```

**方法 B: 通过快捷键**
```
1. 按 Win + X 键
2. 选择 "Windows PowerShell" 或 "终端"
```

#### 步骤 2: 运行检查命令

```powershell
Get-Service sshd
```

### 方法 2: 使用 cmd + PowerShell 命令

在 cmd 中，可以使用 `powershell -Command` 来运行 PowerShell 命令：

```cmd
powershell -Command "Get-Service sshd"
```

### 方法 3: 使用批处理脚本

我已为您创建了检查脚本，直接运行：

```batch
检查_SSH_服务.bat
```

---

## 🔧 如何安装 OpenSSH 服务器

### 方法 1: 通过 Windows 设置（最简单，强烈推荐）

这是不需要任何命令行操作的图形界面方法。

#### 详细步骤：

**第 1 步：打开 Windows 设置**

```
1. 按 Win + I 键
2. 等待"设置"应用打开
```

**第 2 步：进入"可选功能"**

```
1. 在"设置"左侧菜单，点击"应用"
2. 在右侧页面，找到并点击"可选功能"
3. 等待页面加载完成
```

**第 3 步：添加 OpenSSH 服务器**

```
1. 在"可选功能"页面顶部，点击"添加功能"按钮
2. 等待 Microsoft Store 加载功能列表（可能需要 5-10 秒）
3. 在搜索框中输入：OpenSSH Server
4. 从列表中选择：
   - "OpenSSH 服务器"
   - 发布者：Microsoft Corporation
5. 点击该条目
6. 点击"安装"按钮
7. 等待安装完成（通常需要 1-3 分钟）
```

**第 4 步：确认安装**

```
1. 安装完成后，返回"已安装的功能"页面
2. 确认同时显示：
   ✅ OpenSSH 客户端
   ✅ OpenSSH 服务器
```

**第 5 步：启动 SSH 服务**

```
1. 按 Win + R 键
2. 输入：services.msc
3. 按回车键（打开"服务"管理器）
4. 在服务列表中向下滚动
5. 找到："OpenSSH SSH Server"
6. 双击该服务
7. 在"启动类型"下拉框中选择"自动"
8. 点击"启动"按钮
9. 等待几秒
10. 确认"状态"显示"正在运行"
11. 点击"确定"
```

**第 6 步：配置防火墙（如果需要）**

```
1. 按 Win + R 键
2. 输入：control firewall.cpl
3. 按回车键（打开防火墙设置）
4. 点击左侧"允许应用或功能通过 Windows Defender 防火墙"
5. 点击"更改设置"
6. 找到"OpenSSH SSH Server"
7. 勾选"专用"和"公用"
8. 点击"确定"
```

---

### 方法 2: 使用批处理文件自动安装

如果 Windows 设置方法不工作，可以尝试使用我创建的自动安装脚本。

#### 步骤：

```
1. 找到文件：运行_OpenSSH_安装.bat
2. 右键点击该文件
3. 选择"以管理员身份运行"
4. 按照提示完成安装
```

---

### 方法 3: 在 PowerShell 中手动安装

#### 步骤：

**第 1 步：以管理员身份打开 PowerShell**

```
1. 按 Win + X 键
2. 选择"Windows PowerShell (管理员)"
3. 如果提示"是否允许此应用对设备进行更改"，点击"是"
```

**第 2 步：检查当前状态**

```powershell
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH*'
```

**第 3 步：安装 OpenSSH 服务器**

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
```

**第 4 步：启动服务**

```powershell
# 启动 SSH 服务
Start-Service sshd

# 设置为自动启动
Set-Service -Name sshd -StartupType 'Automatic'
```

**第 5 步：配置防火墙**

```powershell
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

**第 6 步：验证安装**

```powershell
Get-Service sshd
```

---

## ✅ 安装完成后的验证

### 1. 检查服务（PowerShell）

```powershell
Get-Service sshd
```

**预期输出：**
```
Status  Name  DisplayName
------  ----  -----------
Running sshd  OpenSSH SSH Server
```

### 2. 检查端口

```powershell
netstat -ano | findstr ":22 "
```

**预期输出：**
```
TCP    0.0.0.0:22            0.0.0.0:0              LISTENING       xxxx
```

### 3. 测试本地连接

```powershell
ssh localhost
```

**预期结果：**
- 提示输入用户名和密码
- 成功登录

---

## 📋 快速参考：命令对应关系

| 操作 | cmd 命令 | PowerShell 命令 |
|------|-----------|----------------|
| 检查服务 | `sc query sshd` | `Get-Service sshd` |
| 启动服务 | `net start sshd` | `Start-Service sshd` |
| 停止服务 | `net stop sshd` | `Stop-Service sshd` |
| 查看端口 | `netstat -ano \| findstr ":22"` | `netstat -ano \| Select-String ":22"` |
| 查看防火墙规则 | - | `Get-NetFirewallRule` |

---

## 🚀 立即开始

### 推荐：使用 Windows 设置（图形界面）

这是最简单可靠的方法，不需要任何命令行。

**只需 8 个简单步骤：**

1. Win + I 打开设置
2. 应用 > 可选功能
3. 添加功能
4. 搜索 "OpenSSH Server"
5. 安装
6. Win + R > services.msc
7. 启动 "OpenSSH SSH Server"
8. 完成！

**预计时间：** 5-10 分钟

---

## 📁 相关文档

- **OPENSSH_安装步骤.md** - 详细安装步骤
- **OPENSSH_手动配置指南.md** - 完整配置指南
- **OPENSSH_SETUP.md** - OpenSSH 详细说明
- **检查_SSH_服务.bat** - 快速检查脚本

---

## 💡 提示

1. **使用正确的命令行环境**
   - PowerShell 命令必须在 PowerShell 中运行
   - cmd 命令可以在 cmd 或 PowerShell 中运行

2. **保持管理员权限**
   - 安装和配置需要管理员权限
   - 右键"以管理员身份运行"

3. **耐心等待**
   - OpenSSH 安装可能需要 1-3 分钟
   - 不要中断安装过程

---

**立即开始：按照上述方法 1 的步骤操作！** 🎯

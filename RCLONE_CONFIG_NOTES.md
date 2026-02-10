<<<<<<< HEAD
# Rclone 配置注意事項（給 Cursor 的說明）

## 📋 專案目標

將 4TB Google Drive 掛載為 Windows 本地的 **Z 槽**，實現：
- 本地檔案存取（如 `Z:\` 磁碟代號）
- 自動同步檔案到雲端
- 遠端存取 4TB 儲存空間

---

## ⚠️ 關鍵注意事項（必讀）

### 🔴 1. 不要重複安裝依賴

- 專案可能已有 `winfsp` 與 `rclone` 相關工具
- 不要重新下載這些工具，優先使用系統既有 rclone

**檢查方式：**
```powershell
rclone version
```

### 🔴 2. Google Drive 授權

- Rclone 會透過瀏覽器完成 Google OAuth 授權
- **務必使用與 4TB Google Drive 相同的帳號**

**授權後產生：**
- 設定檔：`C:\Users\<使用者名稱>\.config\rclone\rclone.conf`
- **勿將此檔提交至 Git**

### 🔴 3. 掛載權限

- 掛載 Z 槽需**管理員權限**
- 掛載腳本需「以系統管理員身分執行」

### 🔴 4. 效能參數（本專案已採用）

| 參數 | 說明 |
|------|------|
| `--vfs-cache-mode full` | 完整快取，避免檔案損壞，**必須** |
| `--no-modtime` | 關閉修改時間檢查，提升效能 |
| `--dir-cache-time 1h` | 目錄快取 1 小時 |
| `--vfs-cache-max-size 10G` | 本機快取上限 10GB |

### 🔴 5. 不破壞現有服務

- 不修改：`website_server.py`、`ai_service.py`、`monitoring_service.py`、`brain_server.py`
- 不變更埠：8000、8001、11434

---

## 📝 本專案已建立的檔案

| 檔案 | 用途 |
|------|------|
| `挂载 Google Drive 为 Z 槽.bat` | 以管理員掛載 gdrive 為 Z: |
| `卸载 Google Drive.bat` | 卸載 Z 槽（net use / taskkill） |
| `test_rclone_mount.bat` | 測試 rclone、gdrive、Z 槽讀寫與同步 |
| `RCLONE_USAGE.md` | 使用指南（快速開始、操作、排錯） |
| `安装 Rclone 服务.bat` | 使用 NSSM 建立開機自動掛載服務 |
| `卸载 Rclone 服务.bat` | 移除 RcloneMount 服務 |

---

## 🚫 禁止操作

- 不修改現有服務程式與埠
- 不刪除 `.env`、`cloudbase.json`、資料庫檔
- 不將 `.config/rclone/`、`rclone.conf` 提交至 Git（已加入 `.gitignore`）

---

## 📚 參考

- Rclone：<https://rclone.org/>
- Google Drive 遠端：<https://rclone.org/drive/>
- 掛載指令：<https://rclone.org/commands/rclone_mount/>
- WinFsp：<https://winfsp.dev/rel/>
- NSSM：<https://nssm.cc/download>
=======
# Rclone 配置注意事项（给 Cursor 的说明）

## 📋 项目目标

将 4TB Google Drive 挂载为 Windows 本地的 **Z 槽**，实现：
- 本地文件访问（如 `Z:\` 盘符）
- 自动同步文件到云端
- 远程访问 4TB 存储空间

---

## ⚠️ 关键注意事项（必读）

### 🔴 1. 不要重复安装依赖

**重要说明：**
- ✅ 项目已使用 `winfsp` 和 `rclone` 相关工具
- ✅ 不要重新下载这些工具
- ✅ 使用系统中已有的 rclone 二进制文件

**检查方法：**
```powershell
# 检查 rclone 是否已安装
rclone version

# 检查 winfsp 是否已安装（如果未安装再安装）
# 查看"应用和功能"中是否有 WinFsp
```

---

### 🔴 2. Google Drive 授权注意事项

**OAuth 认证流程：**
- Rclone 需要通过浏览器完成 Google OAuth 授权
- 授权时会打开浏览器，需要登录 Google 账号
- **重要：** 账号必须与您的 4TB Google Drive 账号一致

**授权后会产生文件：**
- 配置文件：`C:\Users\用户名\.config\rclone\rclone.conf`
- **注意：** 这个文件包含敏感的访问令牌，不要提交到 Git

---

### 🔴 3. 挂载目录权限问题

**Windows 挂载 Z 槽需要：**
- ✅ 管理员权限
- ✅ 正确的目录权限设置
- ✅ 确保挂载点存在且可访问

**推荐的挂载流程：**
```powershell
# 1. 创建挂载点目录（如果不存在）
mkdir C:\gdrive 2>nul

# 2. 使用 rclone mount 挂载（需要管理员权限）
rclone mount gdrive: Z: --vfs-cache-mode full --no-modtime --dir-cache-time 1h
```

---

### 🔴 4. 性能优化配置

**关键配置参数：**
- `--vfs-cache-mode full`：必须使用完整缓存模式，避免文件损坏
- `--no-modtime`：禁用修改时间检查，提高性能
- `--dir-cache-time 1h`：目录缓存 1 小时，减少 API 调用
- `--vfs-cache-max-size 10G`：限制本地缓存大小（防止占满硬盘）

**推荐配置：**
```
Drive Name: gdrive
Mount Point: Z:
Cache Mode: full
Max Cache Size: 10G
Dir Cache Time: 1h
```

---

### 🔴 5. 不要破坏现有服务

**当前运行的服务：**
- ✅ Ollama（端口 11434）
- ✅ 网站服务器（端口 8000）
- ✅ API 监控面板（端口 8001）

**操作前检查：**
```powershell
# 检查挂载点是否被占用
net use Z: >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Z 槽已被占用，请先卸载
    net use Z: /delete
)
```

---

## 📝 给 Cursor 的具体要求

### 任务 1: 配置 Rclone

**要求：**

1. **检查现有安装**
   ```powershell
   # 确认 rclone 已安装
   rclone version

   # 检查现有配置
   rclone config list
   ```

2. **配置 Google Drive（如果未配置）**
   ```powershell
   # 交互式配置
   rclone config

   # 按照提示选择：
   # - n/new (new remote)
   # - Name: gdrive
   # - Type: drive
   # - scope: 1 (drive)
   # - root_folder_id: 留空（使用根目录）
   # - service_account_file: 留空
   # - advanced config: n (no)
   ```

3. **验证配置**
   ```powershell
   # 测试连接
   rclone ls gdrive:

   # 查看存储空间
   rclone about gdrive:
   ```

---

### 任务 2: 创建挂载脚本

**要求：**

创建两个批处理文件：

#### 2.1 `挂载 Google Drive 为 Z 槽.bat`

**功能要求：**
- 检查 Z 槽是否已被占用
- 检查 rclone 是否已配置
- 检查 Google Drive 连接
- 使用管理员权限挂载
- 显示挂载状态和存储空间
- 错误处理和友好提示

**关键参数：**
```batch
rclone mount gdrive: Z: ^
  --vfs-cache-mode full ^
  --no-modtime ^
  --dir-cache-time 1h ^
  --vfs-cache-max-size 10G ^
  --no-checksum ^
  --no-modtime ^
  --allow-non-empty
```

**输出要求：**
```
============================================================
筑未科技 - 挂载 Google Drive 为 Z 槽
============================================================

[检查 1/5] 检查 Z 槽状态...
[检查 2/5] 检查 rclone 安装...
[检查 3/5] 检查 Google Drive 连接...
[检查 4/5] 准备挂载...
[挂载中] 正在挂载到 Z:...

✅ 挂载成功！

[信息]
  挂载点: Z:\
  驱动器: Google Drive
  存储空间: 4 TB
  可用空间: X.XX TB

[提示]
  - 保持此窗口打开以维持挂载
  - 按 Ctrl+C 可卸载
  - 文件会自动同步到云端
============================================================
```

#### 2.2 `卸载 Google Drive.bat`

**功能要求：**
- 检查 Z 槽是否已挂载
- 安全卸载挂载
- 显示卸载状态

**实现方式：**
```batch
@echo off
title 筑未科技 - 卸载 Google Drive

echo 正在卸载 Z: 盘...
net use Z: /delete /y

if %ERRORLEVEL% EQU 0 (
    echo ✅ 卸载成功
) else (
    echo ❌ 卸载失败或 Z: 未挂载
)

pause
```

---

### 任务 3: 创建系统服务（可选但推荐）

**要求：**

使用 NSSM (Non-Sucking Service Manager) 将挂载注册为 Windows 服务。

**步骤：**

1. **下载 NSSM**
   - 访问：https://nssm.cc/download
   - 下载最新版本
   - 解压到 `C:\tools\nssm`

2. **创建安装脚本 `安装 Rclone 服务.bat`**

**功能要求：**
- 检查管理员权限
- 检查 NSSM 是否安装
- 创建 Windows 服务
- 设置为自动启动
- 启动服务

**关键命令：**
```batch
# 创建服务
nssm install RcloneMount rclone mount gdrive: Z: --vfs-cache-mode full --no-modtime --dir-cache-time 1h --vfs-cache-max-size 10G

# 设置服务配置
nssm set RcloneMount AppDirectory C:\path\to\project
nssm set RcloneMount DisplayName "筑未科技 - Google Drive 挂载"
nssm set RcloneMount Description "将 Google Drive 挂载为 Z: 盘"
nssm set RcloneMount Start SERVICE_AUTO_START

# 启动服务
nssm start RcloneMount
```

3. **创建卸载脚本 `卸载 Rclone 服务.bat`**

**功能要求：**
- 停止服务
- 删除服务
- 清理注册表（如果需要）

---

### 任务 4: 创建测试脚本

**要求：**

创建 `test_rclone_mount.bat`：

**测试项目：**
1. 检查 rclone 版本
2. 检查 Google Drive 连接
3. 检查存储空间
4. 测试文件读写
5. 测试同步

**示例测试：**
```batch
@echo off
echo [测试 1/5] 检查 rclone 版本...
rclone version

echo.
echo [测试 2/5] 检查 Google Drive 连接...
rclone ls gdrive:

echo.
echo [测试 3/5] 检查存储空间...
rclone about gdrive:

echo.
echo [测试 4/5] 测试文件读写...
echo 测试内容 > Z:\test_$(date +%Y%m%d_%H%M%S).txt

echo.
echo [测试 5/5] 测试同步...
rclone sync Z:\ gdrive: --dry-run

echo.
echo ✅ 测试完成
```

---

### 任务 5: 创建使用指南

**要求：**

创建 `RCLONE_USAGE.md`，包含：

1. **快速开始**
   - 首次挂载步骤
   - 每次开机如何使用

2. **常用操作**
   - 挂载/卸载
   - 文件同步
   - 排查问题

3. **性能优化**
   - 缓存设置
   - API 限流
   - 网络优化

4. **故障排查**
   - 常见错误
   - 解决方案
   - 日志查看

---

## 🚫 禁止的操作

### ❌ 1. 不要修改现有文件

**受保护的文件：**
- `website_server.py`
- `ai_service.py`
- `monitoring_service.py`
- `brain_server.py`
- 所有 `.bat` 启动脚本

**除非：**
- 明确要求添加新功能
- 修复已知 bug

---

### ❌ 2. 不要删除现有配置

**受保护的配置：**
- `.env` 文件
- `cloudbase.json`
- 任何数据库文件（`.db`）

---

### ❌ 3. 不要更改服务端口

**现有端口：**
- 8000 - 网站服务器
- 8001 - API 监控面板
- 11434 - Ollama

**不要使用这些端口。**

---

### ❌ 4. 不要提交敏感文件到 Git

**必须添加到 `.gitignore`：**
```
# Rclone 配置
.config/rclone/

# 缓存文件
*.cache
.cache/

# 临时文件
*.tmp
.temp/
```

---

## 📊 验收标准

完成后的检查清单：

### 基本功能
- [ ] `rclone version` 显示版本信息
- [ ] `rclone ls gdrive:` 列出 Google Drive 文件
- [ ] `rclone about gdrive:` 显示存储空间
- [ ] Z 槽可以访问（`Z:\`）

### 挂载脚本
- [ ] `挂载 Google Drive 为 Z 槽.bat` 可以正常挂载
- [ ] `卸载 Google Drive.bat` 可以正常卸载
- [ ] 挂载后可以在 Z 槽读写文件
- [ ] 文件会自动同步到云端

### 系统服务（可选）
- [ ] 服务已创建
- [ ] 服务可以启动/停止
- [ ] 服务开机自动启动
- [ ] 服务运行稳定

### 文档
- [ ] `RCLONE_USAGE.md` 使用指南已创建
- [ ] 包含所有必要的信息
- [ ] 格式清晰易读

---

## 🎯 成功标志

配置成功的标志：

1. **Z 槽可用**
   ```
   打开"此电脑"，应该看到 Z: 盘
   容量显示为 4 TB
   可以在 Z: 中浏览 Google Drive 文件
   ```

2. **文件同步正常**
   ```
   在 Z: 中创建文件
   等待几秒后
   在 Google Drive 网页版可以看到文件
   ```

3. **性能良好**
   ```
   文件浏览响应迅速（< 1 秒）
   文件下载速度符合网速
   不卡顿或死机
   ```

---

## 💡 额外建议

### 1. 缓存位置

**将 rclone 缓存放在 SSD 上：**
```powershell
# 设置缓存目录
rclone mount gdrive: Z: --vfs-cache-mode full --cache-dir C:\rclone_cache
```

### 2. 监控 API 使用

**Google Drive API 限制：**
- 每天 1TB 上传下载
- 每天 1,000 万文件操作

**监控方法：**
```powershell
# 定期检查配额
rclone about gdrive:
```

### 3. 错误处理

**自动重连：**
```powershell
rclone mount gdrive: Z: --vfs-cache-mode full --retries 3 --low-level-retries 10
```

---

## 📚 参考资源

**Rclone 官方文档：**
- 主页：https://rclone.org/
- Google Drive 配置：https://rclone.org/drive/
- 挂载命令：https://rclone.org/commands/rclone_mount/

**Windows 相关：**
- WinFsp 下载：https://winfsp.dev/rel/
- NSSM 下载：https://nssm.cc/download

---

## 🆘 常见问题

### Q1: 挂载后 Z 槽无法访问？

**解决方案：**
1. 检查是否以管理员权限运行
2. 检查 Z 槽是否被其他程序占用
3. 尝试卸载后重新挂载

### Q2: 文件上传很慢？

**解决方案：**
1. 检查网络连接
2. 增加 `--transfers` 参数（默认 4）
3. 使用 `--bwlimit` 限速避免占满带宽

### Q3: 挂载后电脑很卡？

**解决方案：**
1. 减少 `--vfs-cache-max-size`
2. 增加 `--dir-cache-time`
3. 减少 `--checkers` 数量

---

## 📞 需要帮助？

如果在配置过程中遇到问题：

1. 查看 Rclone 官方文档
2. 查看 `RCLONE_USAGE.md`（创建后）
3. 运行 `test_rclone_mount.bat` 诊断

---

**祝配置顺利！** 🎉
>>>>>>> bd6537def53debaba0c16f279817e4a317eed98c

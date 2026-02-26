# 给 Cursor 的 Rclone 配置任务

## 🎯 任务概述

将 4TB Google Drive 挂载为 Windows 本地的 **Z 槽**，实现本地文件访问和云端自动同步。

---

## ⚠️ 重要前提（必读）

### 1. 不要重新下载依赖
- 项目已有 `rclone` 和 `winfsp`
- 先用 `rclone version` 检查是否已安装

### 2. 保护现有文件和服务
- 不要修改 `website_server.py`、`ai_service.py`、`monitoring_service.py` 等
- 不要更改端口 8000、8001、11434
- 不要删除 `.env`、`cloudbase.json`、数据库文件

### 3. OAuth 授权
- 配置时会打开浏览器，需要 Google 账号授权
- 确保使用的账号与 4TB Google Drive 账号一致

---

## 📋 需要创建的文件

### 1. `挂载 Google Drive 为 Z 槽.bat`
- 检查 Z 槽状态
- 检查 rclone 配置
- 以管理员权限挂载
- 显示挂载状态和存储空间

### 2. `卸载 Google Drive.bat`
- 检查挂载状态
- 安全卸载 Z 槽

### 3. `test_rclone_mount.bat`
- 测试 rclone 版本
- 测试 Google Drive 连接
- 测试文件读写
- 测试同步功能

### 4. `RCLONE_USAGE.md`
- 快速开始指南
- 常用操作说明
- 性能优化建议
- 故障排查

### 5. （可选）`安装 Rclone 服务.bat` 和 `卸载 Rclone 服务.bat`
- 使用 NSSM 创建 Windows 服务
- 开机自动挂载

---

## 🔧 核心功能要求

### 挂载命令

```batch
rclone mount gdrive: Z: ^
  --vfs-cache-mode full ^
  --no-modtime ^
  --dir-cache-time 1h ^
  --vfs-cache-max-size 10G ^
  --no-checksum ^
  --allow-non-empty
```

### 配置检查

```powershell
# 检查 rclone 版本
rclone version

# 测试连接
rclone ls gdrive:

# 查看存储空间
rclone about gdrive:
```

### 验收标准

- [ ] Z 槽可以访问（`Z:\`）
- [ ] 可以在 Z 槽浏览 Google Drive 文件
- [ ] 文件自动同步到云端
- [ ] 挂载/卸载脚本正常工作
- [ ] 使用指南完整清晰

---

## 🚫 禁止操作

1. ❌ 修改现有服务文件
2. ❌ 删除 `.env`、`cloudbase.json`、数据库
3. ❌ 使用端口 8000、8001、11434
4. ❌ 提交敏感文件到 Git（`.config/rclone/`）

---

## 📚 详细文档

详细注意事项请查看：`RCLONE_CONFIG_NOTES.md`

---

## 🎯 成功标志

配置成功后：
- 打开"此电脑"看到 Z: 盘（4TB）
- 可以在 Z: 浏览文件
- 文件自动同步到 Google Drive
- 性能良好（不卡顿）

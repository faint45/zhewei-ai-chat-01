# 築未科技远程控制API文档

## 📋 概述

築未科技远程控制系统提供统一的API接口，支持通过多种通讯软件（微信小程序、Telegram、Discord等）远程控制本地AI模型和执行系统命令。

## 🌐 基础信息

- **基础URL**: `http://localhost:8003` (可根据实际部署调整)
- **认证方式**: API密钥认证
- **数据格式**: JSON
- **编码**: UTF-8

## 🔑 认证方式

所有API请求需要在Header中包含认证信息：

```http
Authorization: zhuwei-tech-2026
Content-Type: application/json
```

## 📊 API端点

### 1. 健康检查

检查服务器运行状态

**请求**
```http
GET /health
```

**响应**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-03 15:00:00",
  "connectionCount": 5,
  "version": "1.0.0"
}
```

### 2. 执行命令

执行AI或系统命令

**请求**
```http
POST /api/command
```

**请求体**
```json
{
  "type": "ai" | "sys",
  "command": "要执行的命令"
}
```

**参数说明**
- `type`: 命令类型
  - `ai`: AI对话命令
  - `sys`: 系统命令
- `command`: 具体命令内容

**响应**
```json
{
  "status": "success",
  "result": "命令执行结果",
  "execution_time": 2.5,
  "timestamp": "2026-02-03 15:00:00"
}
```

### 3. 获取连接状态

获取当前WebSocket连接信息

**请求**
```http
GET /api/connections
```

**响应**
```json
{
  "active_connections": 3,
  "connections": [
    {
      "id": "connection_id",
      "connected_at": "2026-02-03 14:30:00",
      "last_activity": "2026-02-03 15:00:00"
    }
  ]
}
```

## 💬 命令示例

### AI命令示例

```json
{
  "type": "ai",
  "command": "解释什么是机器学习"
}
```

```json
{
  "type": "ai", 
  "command": "帮我分析这个Python代码"
}
```

### 系统命令示例

```json
{
  "type": "sys",
  "command": "python --version"
}
```

```json
{
  "type": "sys",
  "command": "ping google.com"
}
```

## 🔌 通讯软件集成

### 1. 微信小程序集成

**配置文件**: `wechat_miniprogram/`

**使用方法**:
1. 在微信开发者工具中导入项目
2. 修改 `app.js` 中的 `serverUrl` 配置
3. 上传审核发布

**主要功能**:
- AI智能对话
- 系统命令执行
- 实时状态监控
- 快速指令按钮

### 2. Telegram机器人集成

**配置文件**: `telegram_bot.py`

**使用方法**:
1. 创建Telegram机器人并获取token
2. 设置环境变量: `TELEGRAM_BOT_TOKEN=你的token`
3. 运行: `python telegram_bot.py`

**命令列表**:
- `/start` - 开始使用
- `/help` - 帮助信息
- `/status` - 服务器状态
- `/ai <问题>` - AI对话
- `/sys <命令>` - 系统命令

### 3. Discord机器人集成

**配置文件**: `discord_bot.py`

**使用方法**:
1. 在Discord开发者门户创建应用
2. 获取机器人token
3. 设置环境变量: `DISCORD_BOT_TOKEN=你的token`
4. 运行: `python discord_bot.py`

**命令列表**:
- **前缀命令**: `!help`, `!status`, `!ai <问题>`, `!sys <命令>`
- **斜杠命令**: `/ai`, `/sys`, `/status`

## ⚠️ 安全注意事项

1. **API密钥保护**: 不要将API密钥硬编码在客户端代码中
2. **输入验证**: 所有用户输入都应进行验证和过滤
3. **命令限制**: 限制可执行的系统命令范围
4. **访问控制**: 限制可访问的IP地址范围
5. **日志记录**: 记录所有API调用和命令执行

## 🔧 错误处理

### 常见错误码

| 状态码 | 错误信息 | 说明 |
|--------|----------|------|
| 200 | OK | 请求成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 认证失败 |
| 403 | Forbidden | 权限不足 |
| 404 | Not Found | 接口不存在 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务不可用 |

### 错误响应格式

```json
{
  "error": {
    "code": 400,
    "message": "请求参数错误",
    "details": "缺少必要的参数"
  }
}
```

## 📈 性能指标

- **响应时间**: 平均 < 3秒
- **并发连接**: 支持100+并发连接
- **命令执行**: AI命令 < 5秒，系统命令 < 10秒
- **可用性**: 99.9%以上

## 🔄 WebSocket实时通信

除了HTTP API，还支持WebSocket实时通信：

**连接地址**: `ws://localhost:8003/ws`

**消息格式**:
```json
{
  "type": "command",
  "data": {
    "type": "ai" | "sys",
    "command": "命令内容"
  }
}
```

**实时响应**:
```json
{
  "type": "result",
  "data": {
    "status": "success",
    "result": "执行结果"
  }
}
```

## 🚀 部署说明

### 本地部署

1. 启动远程控制服务器:
```bash
python remote_control_server.py
```

2. 启动通讯软件机器人:
```bash
# Telegram机器人
python telegram_bot.py

# Discord机器人
python discord_bot.py
```

### 生产环境部署

1. 使用反向代理（Nginx）
2. 配置SSL证书
3. 设置防火墙规则
4. 配置监控和日志
5. 使用进程管理工具（PM2）

## 📞 技术支持

如有问题请联系築未科技技术支持团队:
- 邮箱: support@zhuwei-tech.com
- 电话: 400-123-4567
- 官网: https://zhuwei-tech.com

---

*最后更新: 2026-02-03*
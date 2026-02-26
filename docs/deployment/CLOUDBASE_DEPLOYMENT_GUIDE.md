# 築未科技 - 腾讯云CloudBase部署指南

## 📋 部署前准备

### 1. 创建腾讯云账号
- 访问：https://cloud.tencent.com/
- 注册并登录账号
- 完成实名认证

### 2. 开通CloudBase服务
- 访问：https://console.cloud.tencent.com/tcb
- 点击"新建环境"
- 选择"免费套餐"（每月2GB存储 + 5GB流量）
- 设置环境名称：`zhewei-ai-system`

---

## 🚀 部署步骤

### 第一步：创建CloudBase环境

1. **登录腾讯云控制台**
   ```
   https://console.cloud.tencent.com/tcb
   ```

2. **创建新环境**
   - 点击"新建环境"
   - 环境名称：`zhewei-ai-system`
   - 基础套餐：按量付费（有免费额度）
   - 地域：选择离您最近的区域（如广州、上海）

3. **等待环境创建完成**（通常需要1-2分钟）

### 第二步：部署后端服务（CloudRun）

由于这是Python后端服务，需要使用CloudRun容器化部署。

#### 2.1 创建Dockerfile

在项目根目录创建`Dockerfile`：

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements_ai.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements_ai.txt

# 复制应用代码
COPY remote_control_server.py .
COPY ai_service.py .
COPY config_ai.py .

# 暴露端口
EXPOSE 8080

# 设置环境变量
ENV PYTHONPATH=/app
ENV PORT=8080

# 启动命令
CMD ["uvicorn", "remote_control_server:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### 2.2 创建Docker忽略文件

创建`.dockerignore`：

```
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
.venv/
.git/
.gitignore
README*.md
*.bat
*.md
static/
templates/
deploy_temp/
```

#### 2.3 部署到CloudRun

**方法A：使用腾讯云CLI工具**

1. 安装腾讯云CLI：
```bash
npm install -g @cloudbase/cli
```

2. 登录并初始化：
```bash
cloudbase login
cloudbase init
```

3. 部署：
```bash
cd cloudrun/zhewei-api
cloudbase hosting deploy
```

**方法B：通过控制台部署**

1. 访问CloudRun控制台：
```
https://console.cloud.tencent.com/tcb/cloudrun
```

2. 创建新服务：
   - 服务名称：`zhewei-api`
   - 服务类型：容器型服务
   - 运行环境：Python 3.9

3. 上传代码：
   - 选择"本地代码上传"
   - 上传包含Dockerfile的整个项目
   - 或使用Git仓库导入

4. 配置服务：
   - CPU：0.5核
   - 内存：1GB
   - 最小实例数：1（避免冷启动）
   - 最大实例数：3
   - 端口：8080

5. 部署并等待完成

### 第三步：配置环境变量

在CloudRun服务配置中添加环境变量：

```env
PYTHONPATH=/app
PORT=8080
CLOUD_DEPLOYMENT=true
OLAMA_BASE_URL=http://localhost:11434
DEFAULT_AI_MODEL=gemma3:4b
```

### 第四步：配置安全规则

1. 访问安全规则页面：
```
https://console.cloud.tencent.com/tcb/security-rules
```

2. 配置API访问规则：
   - 添加允许访问的IP地址
   - 或设置白名单域名

3. 配置CORS：
   - 允许的源：`*`（开发环境）或具体域名（生产环境）
   - 允许的方法：`GET, POST, PUT, DELETE, OPTIONS`
   - 允许的头部：`*`

### 第五步：获取访问地址

部署完成后，您将获得：

1. **后端API地址**：
```
https://zhewei-api-xxx.service.tcloudbase.com
```

2. **统一API端点**：
```
https://zhewei-api-xxx.service.tcloudbase.com/v1/execute
```

3. **API文档**：
```
https://zhewei-api-xxx.service.tcloudbase.com/docs
```

---

## 📱 配置客户端使用云端地址

### 更新Telegram机器人

修改`telegram_bot.py`中的服务器地址：

```python
# 修改前
self.server_url = "http://localhost:8006"

# 修改后
self.server_url = "https://zhewei-api-xxx.service.tcloudbase.com"
```

### 更新Discord机器人

修改`discord_bot.py`中的服务器地址：

```python
# 修改前
self.server_url = "http://localhost:8006"

# 修改后
self.server_url = "https://zhewei-api-xxx.service.tcloudbase.com"
```

### 更新Web前端

修改`remote_control.html`中的API地址：

```javascript
// 修改前
const API_BASE_URL = 'http://localhost:8006';

// 修改后
const API_BASE_URL = 'https://zhewei-api-xxx.service.tcloudbase.com';
```

---

## 🔧 测试部署

### 测试API端点

```bash
# 测试健康检查
curl https://zhewei-api-xxx.service.tcloudbase.com/health

# 测试统一API
curl -X POST https://zhewei-api-xxx.service.tcloudbase.com/v1/execute \
  -H "Content-Type: application/json" \
  -d '{
    "source": "test",
    "user_id": "test_user",
    "command": "ai:你好"
  }'
```

### 测试机器人连接

1. 重启Telegram机器人
2. 发送测试消息：`/ai 你好`
3. 验证响应是否正常

---

## 💰 成本预估

### CloudRun计费（免费套餐）

| 资源 | 免费额度 | 超出费用 |
|------|----------|----------|
| 函数运行时间 | 100万GBs/月 | ¥0.0000316/GBs |
| 函数调用次数 | 100万次/月 | ¥0.00133/万次 |
| 流量 | 5GB/月 | ¥0.8/GB |

**预估成本**：如果日均请求量在1000次以内，基本在免费额度内。

---

## 🛠️ 常见问题

### 1. 部署失败怎么办？

检查：
- Dockerfile是否正确
- requirements_ai.txt是否完整
- 端口配置是否正确（8080）
- 环境变量是否设置

### 2. API访问报错？

检查：
- 安全规则是否配置正确
- CORS是否允许访问
- 服务是否正常启动

### 3. 响应速度慢？

优化：
- 设置最小实例数为1（避免冷启动）
- 选择更近的地域
- 优化代码性能

---

## 📊 监控和管理

### 查看服务状态

访问CloudRun控制台：
```
https://console.cloud.tencent.com/tcb/cloudrun
```

查看：
- 服务运行状态
- 资源使用情况
- 调用次数统计
- 错误日志

### 查看日志

```
https://console.cloud.tencent.com/tcb/logs
```

---

## 🚀 升级和扩展

### 添加数据库

如需要持久化数据，可以：
1. 创建MySQL数据库
2. 在环境变量中配置数据库连接
3. 修改代码连接数据库

### 添加存储

如需要文件存储，可以：
1. 使用CloudBase云存储
2. 上传静态文件
3. 获取文件访问URL

---

## 📞 技术支持

### 文档地址

- CloudRun文档：https://cloud.tencent.com/document/product/1243
- CloudBase文档：https://cloud.tencent.com/document/product/876

### 控制台地址

- 总览：https://console.cloud.tencent.com/tcb
- CloudRun：https://console.cloud.tencent.com/tcb/cloudrun
- 日志：https://console.cloud.tencent.com/tcb/logs

---

**部署完成后，您的築未科技统一API系统将拥有：**

✅ 全球/国内可访问的HTTPS地址
✅ 自动扩缩容能力
✅ 99.9%服务可用性
✅ 自动SSL证书
✅ 无需端口转发配置

🎉 开始您的云端之旅吧！
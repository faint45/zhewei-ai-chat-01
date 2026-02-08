# 築未科技 - 环境变量配置指南

## 📋 需要配置的环境变量

### 必需环境变量

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `PYTHONPATH` | `/app` | Python模块路径 |
| `PORT` | `8080` | 服务监听端口 |
| `CLOUD_DEPLOYMENT` | `true` | 标识为云端部署 |

### AI服务配置

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `OLAMA_BASE_URL` | `http://localhost:11434` | Ollama服务地址 |
| `DEFAULT_AI_MODEL` | `gemma3:4b` | 默认AI模型 |

### 可选环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `LOG_LEVEL` | `info` | 日志级别 |
| `CORS_ORIGINS` | `*` | CORS允许的来源 |
| `JWT_SECRET` | `自动生成` | JWT密钥 |
| `RATE_LIMIT_PER_MINUTE` | `60` | 每分钟请求限制 |

---

## 🚀 在腾讯云CloudRun中配置

### 方法1：通过控制台界面配置

1. **打开CloudRun控制台**
   ```
   https://console.cloud.tencent.com/tcb/cloudrun
   ```

2. **进入服务配置**
   - 找到您的服务 `zhewei-api`
   - 点击服务名称进入详情
   - 找到"环境变量"或"服务配置"选项

3. **添加环境变量**
   点击"添加环境变量"按钮，逐个添加：

   **变量1**：
   ```
   键名：PYTHONPATH
   值：/app
   ```

   **变量2**：
   ```
   键名：PORT
   值：8080
   ```

   **变量3**：
   ```
   键名：CLOUD_DEPLOYMENT
   值：true
   ```

   **变量4**：
   ```
   键名：OLAMA_BASE_URL
   值：http://localhost:11434
   ```

   **变量5**：
   ```
   键名：DEFAULT_AI_MODEL
   值：gemma3:4b
   ```

4. **保存配置**
   - 点击"保存"或"更新配置"按钮
   - 等待配置生效（约30秒）

5. **重新部署服务**
   - 为了让新环境变量生效，需要重新部署服务
   - 点击"重新部署"按钮
   - 等待部署完成（约3-5分钟）

### 方法2：批量导入（如支持）

如果CloudRun支持批量导入，可以直接复制以下内容：

```env
PYTHONPATH=/app
PORT=8080
CLOUD_DEPLOYMENT=true
OLAMA_BASE_URL=http://localhost:11434
DEFAULT_AI_MODEL=gemma3:4b
LOG_LEVEL=info
CORS_ORIGINS=*
JWT_SECRET=zhewei-ai-secret-key-change-in-production
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

---

## 🔧 配置说明

### OLAMA_BASE_URL 重要说明

**当前配置**：`http://localhost:11434`

**问题**：云端环境无法访问本地Ollama服务

**解决方案**：
1. **不使用AI功能**：注释掉或删除此变量
2. **使用云端AI服务**：配置实际的云端API地址，如：
   ```
   OLAMA_BASE_URL=https://your-ai-service.com/api
   ```

### DEFAULT_AI_MODEL 说明

**当前配置**：`gemma3:4b`

**可选模型**：
- `gemma3:4b` - 轻量级，响应快
- `llava:latest` - 支持图像识别
- `llama2:7b` - 平衡性能和准确性
- `mistral:7b` - 高质量输出

### CORS_ORIGINS 安全配置

**开发环境**：
```env
CORS_ORIGINS=*
```

**生产环境**（推荐）：
```env
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

---

## ✅ 验证配置

配置完成后，验证环境变量是否生效：

### 1. 检查服务日志

在CloudRun控制台查看服务日志：
```
https://console.cloud.tencent.com/tcb/cloudrun
```

查找包含环境变量信息的日志。

### 2. 测试API健康检查

```bash
# 测试健康检查端点
curl https://zhewei-api-xxxxx.service.tcloudbase.com/health

# 预期响应
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-03T12:00:00"
}
```

### 3. 测试统一API

```bash
curl -X POST https://zhewei-api-xxxxx.service.tcloudbase.com/v1/execute \
  -H "Content-Type: application/json" \
  -d '{
    "source": "test",
    "user_id": "test_user",
    "command": "ai:你好"
  }'
```

或使用测试脚本：
```bash
python test_cloud_api.py https://zhewei-api-xxxxx.service.tcloudbase.com
```

---

## 🔄 更新环境变量

如需修改环境变量：

1. 进入CloudRun服务配置页面
2. 修改对应的变量值
3. 点击"保存"
4. 重新部署服务使更改生效

---

## 💡 最佳实践

### 安全性

1. **生产环境不要使用 `*` 作为CORS_ORIGINS**
2. **修改默认的JWT_SECRET**
3. **配置适当的速率限制**
4. **启用HTTPS**（CloudBase自动提供）

### 性能优化

1. **设置最小实例数为1**，避免冷启动
2. **选择合适的AI模型**，平衡性能和准确性
3. **配置合理的速率限制**，防止滥用

### 可维护性

1. **使用描述性的变量名**
2. **记录环境变量变更**
3. **定期审查和更新配置**

---

## 📞 获取帮助

### 文档

- **完整部署指南**：`DEPLOY_INSTRUCTIONS.md`
- **API文档**：`api_documentation.md`
- **项目文档**：`README.md`

### 技术支持

- **腾讯云文档**：https://cloud.tencent.com/document/product/1243
- **CloudRun文档**：https://cloud.tencent.com/document/product/1243/43891

---

**环境变量配置完成！** 🎉

记得在配置完成后重新部署服务，使更改生效。

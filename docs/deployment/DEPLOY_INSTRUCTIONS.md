# 築未科技 - 腾讯云CloudBase完整部署指南

## ✅ 部署准备检查

所有必需文件已准备完成：

- ✅ `Dockerfile` - Docker容器配置
- ✅ `requirements_ai.txt` - Python依赖
- ✅ `remote_control_server.py` - 主服务器代码
- ✅ `CLOUDBASE_DEPLOYMENT_GUIDE.md` - 详细部署指南
- ✅ `開始騰訊雲部署.bat` - 一键部署脚本
- ✅ `update_cloud_config.bat` - 配置更新工具
- ✅ `test_cloud_api.py` - API测试工具

---

## 🚀 立即开始部署

### 第一步：登录腾讯云控制台

**直接访问链接**：
```
https://console.cloud.tencent.com/tcb/cloudrun
```

**或访问CloudBase首页**：
```
https://console.cloud.tencent.com/tcb
```

### 第二步：创建CloudBase环境

1. 点击页面上的"新建环境"按钮
2. 填写环境信息：
   - **环境名称**：`zhewei-ai-system`
   - **套餐类型**：按量付费（有免费额度）
   - **地域**：选择广州或上海（选择离您最近的）
3. 点击"新建"按钮
4. 等待环境创建完成（通常1-2分钟）

### 第三步：创建CloudRun服务

1. 进入CloudRun控制台
   ```
   https://console.cloud.tencent.com/tcb/cloudrun
   ```

2. 点击"新建服务"按钮

3. 填写服务信息：
   - **服务名称**：`zhewei-api`
   - **服务类型**：容器型服务
   - **运行环境**：自定义镜像/代码

4. 选择代码来源：
   - **方式A**：Git仓库（推荐）
     - 连接GitHub账号
     - 选择包含项目的仓库
   - **方式B**：本地上传
     - 压缩项目文件
     - 上传ZIP文件

5. 确保上传的文件包含：
   - `Dockerfile`（必须）
   - `requirements_ai.txt`（必须）
   - `remote_control_server.py`（必须）
   - `ai_service.py`
   - `config_ai.py`

### 第四步：配置服务参数

在服务配置页面设置：

**基础配置**：
- **CPU规格**：0.5核
- **内存规格**：1GB
- **最小实例数**：1（重要：避免冷启动延迟）
- **最大实例数**：3
- **端口**：8080

**环境变量**：
```
PYTHONPATH=/app
PORT=8080
CLOUD_DEPLOYMENT=true
OLAMA_BASE_URL=http://localhost:11434
DEFAULT_AI_MODEL=gemma3:4b
```

**访问配置**：
- **访问类型**：公网访问
- **安全组**：允许HTTP(80)和HTTPS(443)端口

### 第五步：部署并等待

1. 点击"部署"按钮
2. 等待部署完成（通常3-5分钟）
3. 部署成功后会显示访问地址

### 第六步：测试部署

部署完成后，您将获得类似以下的地址：

```
https://zhewei-api-xxxxx.service.tcloudbase.com
```

**测试命令**：
```bash
# 测试健康检查
curl https://zhewei-api-xxxxx.service.tcloudbase.com/health

# 测试统一API
curl -X POST https://zhewei-api-xxxxx.service.tcloudbase.com/v1/execute \
  -H "Content-Type: application/json" \
  -d '{"source":"test","user_id":"test_user","command":"ai:你好"}'

# 或使用Python测试
python test_cloud_api.py https://zhewei-api-xxxxx.service.tcloudbase.com
```

---

## 🔧 部署后配置

### 更新客户端配置

**方法1：使用配置更新工具**
```cmd
update_cloud_config.bat
```

输入您的云端地址，自动更新所有客户端。

**方法2：手动更新**

**Telegram机器人** (`telegram_bot.py`)：
```python
self.server_url = "https://zhewei-api-xxxxx.service.tcloudbase.com"
```

**Discord机器人** (`discord_bot.py`)：
```python
self.server_url = "https://zhewei-api-xxxxx.service.tcloudbase.com"
```

**Web前端** (`remote_control.html`等)：
```javascript
const API_BASE_URL = 'https://zhewei-api-xxxxx.service.tcloudbase.com';
```

### 重启服务

```cmd
# 重启Telegram机器人
python telegram_bot.py

# 重启Discord机器人
python discord_bot.py

# 刷新浏览器，访问新地址
https://zhewei-api-xxxxx.service.tcloudbase.com
```

---

## 📊 访问地址汇总

部署成功后，您将拥有以下访问地址：

| 功能 | 访问地址 |
|------|----------|
| 统一API | `https://zhewei-api-xxxxx.service.tcloudbase.com/v1/execute` |
| API文档 | `https://zhewei-api-xxxxx.service.tcloudbase.com/docs` |
| 健康检查 | `https://zhewei-api-xxxxx.service.tcloudbase.com/health` |
| 管理面板 | `https://zhewei-api-xxxxx.service.tcloudbase.com/dashboard` |

---

## 💰 成本和限制

### 免费套餐额度

腾讯云CloudBase免费套餐：
- **存储**：1GB/月
- **流量**：5GB/月
- **CloudRun运行**：100万GBs/月

### 预估成本

| 使用场景 | 月费用 |
|----------|--------|
| 轻度使用（<1000次/天） | ¥0（免费额度内） |
| 中度使用（<10000次/天） | ¥50-100 |
| 重度使用（>10000次/天） | ¥100-300 |

---

## 🔐 安全配置建议

### 生产环境安全设置

1. **配置CORS白名单**：
   - 仅允许特定域名访问
   - 不在生产环境使用 `*`

2. **设置IP白名单**：
   - 在安全规则中添加受信任的IP地址
   - 限制API访问来源

3. **启用HTTPS**：
   - CloudBase自动提供SSL证书
   - 强制使用HTTPS协议

4. **API限流**：
   - 配置每用户每分钟请求次数限制
   - 防止API滥用

---

## 📞 技术支持和文档

### 腾讯云文档

- **CloudRun文档**：https://cloud.tencent.com/document/product/1243
- **CloudBase文档**：https://cloud.tencent.com/document/product/876
- **控制台**：https://console.cloud.tencent.com/tcb

### 项目文档

- **详细部署指南**：`CLOUDBASE_DEPLOYMENT_GUIDE.md`
- **部署状态**：`DEPLOYMENT_STATUS.md`
- **快速开始**：`QUICK_START.md`
- **项目文档**：`README.md`

### 获取帮助

遇到问题？
1. 查看项目文档中的"常见问题"章节
2. 检查CloudRun服务日志
3. 联系腾讯云技术支持

---

## ✅ 部署检查清单

完成部署后，请检查以下项目：

- [ ] CloudBase环境创建成功
- [ ] CloudRun服务部署成功
- [ ] 能够访问API文档页面
- [ ] 健康检查接口返回正常
- [ ] 统一API接口调用成功
- [ ] 所有客户端已更新云端地址
- [ ] 机器人连接正常
- [ ] Web前端访问正常
- [ ] 配置了CORS和安全规则
- [ ] 查看并理解服务日志

---

## 🎯 下一步

部署完成后，您可以：

1. **扩展功能**
   - 添加数据库存储（MySQL）
   - 集成文件存储
   - 添加更多AI模型

2. **优化性能**
   - 配置CDN加速
   - 调整实例数量
   - 优化数据库查询

3. **监控和维护**
   - 设置告警通知
   - 定期查看日志
   - 备份重要数据

---

**祝您部署顺利！** 🚀

如有任何问题，请参考文档或联系技术支持。

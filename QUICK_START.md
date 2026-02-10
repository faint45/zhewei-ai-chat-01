# 築未科技 - 快速开始指南

## 🚀 本地部署

### 一键启动
```cmd
啟動築未科技大腦.bat
```

### 分步启动
```cmd
# 1. 启动Ollama
start_ollama.bat

# 2. 启动服务器
python remote_control_server.py

# 3. 访问API文档
# 浏览器打开：http://localhost:8003/docs
```

## ☁️ 云端部署

### 腾讯云CloudBase（推荐国内）

**一键部署助手**：
```cmd
開始騰訊雲部署.bat
```

**快速测试**：
```cmd
# 测试云端API连接
python test_cloud_api.py https://your-domain.com

# 更新客户端配置
update_cloud_config.bat
```

### 其他云平台

**Vercel**：
```cmd
deploy_to_vercel.bat
```

**Railway**：
访问 https://railway.app/ 连接GitHub仓库

## 🔧 配置更新

### 更新服务器地址

部署到云端后，运行：
```cmd
update_cloud_config.bat
```

输入您的云端地址，自动更新所有客户端配置。

## 📞 部署后操作

1. **测试API连接**
   ```cmd
   python test_cloud_api.py https://your-domain.com
   ```

2. **更新机器人配置**
   - Telegram：`telegram_bot.py`
   - Discord：`discord_bot.py`

3. **重启服务**
   ```cmd
   python telegram_bot.py
   python discord_bot.py
   ```

4. **访问新地址**
   - API：`https://your-domain.com/v1/execute`
   - 文档：`https://your-domain.com/docs`

## 📚 详细文档

- **完整README**：`README.md`
- **腾讯云部署指南**：`CLOUDBASE_DEPLOYMENT_GUIDE.md`
- **部署状态**：`DEPLOYMENT_STATUS.md`
- **API文档**：`api_documentation.md`

## ❓ 常见问题

**Q: 端口被占用？**
A: 修改`remote_control_server.py`中的端口配置

**Q: 云部署失败？**
A: 查看`CLOUDBASE_DEPLOYMENT_GUIDE.md`详细步骤

**Q: 机器人不响应？**
A: 检查`update_cloud_config.bat`是否已更新地址

---

**开始您的築未科技之旅吧！** 🚀

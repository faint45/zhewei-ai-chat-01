# 築未科技 — 雲端快速部署指南（5 分鐘上線）

## 🎯 目標
解決本地電腦關機後系統停止的問題，實現 24/7 雲端運行。

---

## 📋 前置需求

### 選項 A：Oracle Cloud 免費 VPS（推薦新手）
- ✅ 完全免費
- ✅ 1GB RAM（可運行輕量模型）
- ❌ 無 GPU（僅 CPU 推理）

### 選項 B：付費 VPS（推薦生產環境）
- Linode/DigitalOcean：$12/月起（2GB RAM）
- Vultr：$12/月起（可選配 GPU）

---

## 🚀 快速部署（3 步驟）

### 步驟 1：建立 VPS 並安裝 Docker

```bash
# SSH 連線到 VPS
ssh ubuntu@YOUR_VPS_IP

# 一鍵安裝 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 登出再登入使 Docker 生效
exit
ssh ubuntu@YOUR_VPS_IP
```

### 步驟 2：上傳專案

**方法 A：Git Clone（推薦）**
```bash
cd /opt
sudo mkdir zhewei && sudo chown $USER:$USER zhewei
cd zhewei
git clone https://github.com/YOUR_REPO/zhe-wei-tech.git .
```

**方法 B：本地上傳**
```powershell
# 在本地 PowerShell 執行
scp -r d:\zhe-wei-tech ubuntu@YOUR_VPS_IP:/opt/zhewei/
```

### 步驟 3：設定環境變數並啟動

```bash
cd /opt/zhewei

# 建立 .env 檔案
cat > .env << 'EOF'
# Cloudflare Tunnel Token（必要）
CLOUDFLARE_TOKEN=your_cloudflare_tunnel_token

# AI Provider Keys（至少設定一個）
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key

# Ollama 設定
OLLAMA_BASE_URL=http://ollama:11434
AI_COST_MODE=local_first
EOF

# 執行自動部署腳本
chmod +x scripts/deploy_to_cloud.sh
./scripts/deploy_to_cloud.sh
```

---

## ✅ 驗證部署

```bash
# 檢查服務狀態
docker compose -f docker-compose.cloud.yml ps

# 查看日誌
docker compose -f docker-compose.cloud.yml logs -f brain_server

# 測試本地存取
curl http://localhost:8002/health

# 測試外網存取
curl https://jarvis.zhe-wei.net/health
```

---

## 🔧 常用指令

```bash
# 查看所有服務
docker compose -f docker-compose.cloud.yml ps

# 重啟單一服務
docker compose -f docker-compose.cloud.yml restart brain_server

# 查看日誌
docker compose -f docker-compose.cloud.yml logs -f

# 停止所有服務
docker compose -f docker-compose.cloud.yml down

# 更新並重啟
git pull
docker compose -f docker-compose.cloud.yml up -d --build
```

---

## 📊 監控與維護

### 設定自動健康檢查

```bash
# 設定執行權限
chmod +x /opt/zhewei/scripts/health_monitor.sh

# 加入 crontab（每 5 分鐘檢查）
crontab -e
# 加入以下行：
*/5 * * * * /opt/zhewei/scripts/health_monitor.sh >> /var/log/zhewei_health.log 2>&1
```

### 查看健康日誌

```bash
tail -f /var/log/zhewei_health.log
```

---

## 🎛️ 已部署的服務

| 服務 | 容器名 | Port | 外網域名 |
|------|--------|------|----------|
| Ollama AI | zhewei_ollama | 11434 | - |
| Brain Server | zhewei_brain | 8002 | jarvis.zhe-wei.net |
| Portal | zhewei_portal | 8888 | zhe-wei.net |
| CMS | zhewei_cms | 8020 | cms.zhe-wei.net |
| CodeSim | zhewei_codesim | 8001 | codesim.zhe-wei.net |
| Prediction | zhewei_prediction | 8025 | predict.zhe-wei.net |
| Smart Bridge | zhewei_smart_bridge | 8003 | bridge.zhe-wei.net |
| Gateway | zhewei_gateway | 80 | - |
| Tunnel | zhewei_tunnel | - | - |

---

## 🆘 故障排除

### Ollama 記憶體不足
```bash
# 使用更小的模型
docker exec zhewei_ollama ollama pull gemma2:2b
docker exec zhewei_ollama ollama pull qwen2.5:3b

# 啟用 Swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Brain Server 無法連接 Ollama
```bash
# 檢查網路連接
docker exec zhewei_brain curl http://ollama:11434/api/tags

# 重啟 Ollama
docker compose -f docker-compose.cloud.yml restart ollama
```

### Cloudflare Tunnel 斷線
```bash
# 檢查 Token
docker logs zhewei_tunnel

# 重啟 Tunnel
docker compose -f docker-compose.cloud.yml restart tunnel
```

---

## 💰 成本估算

### 免費方案（Oracle Cloud）
- VPS：$0/月
- 流量：10TB/月 免費
- **總計：$0/月**

### 基礎方案（Linode 2GB）
- VPS：$12/月
- 流量：2TB/月 免費
- **總計：$12/月**

### 進階方案（Vultr 4GB + GPU）
- VPS：$90/月（含 GPU）
- **總計：$90/月**

---

## 📚 詳細文件

- 完整部署指南：`docs/deployment/CLOUD_24_7_DEPLOYMENT.md`
- Oracle Cloud 建立：`docs/Oracle_Cloud_免費VPS建立指南.md`
- Docker Compose 配置：`docker-compose.cloud.yml`

---

## ✨ 完成！

您的系統現在已在雲端 24/7 運行，不受本地電腦關機影響。

**外網存取：**
- 主入口：https://zhe-wei.net
- Jarvis AI：https://jarvis.zhe-wei.net
- 營建管理：https://cms.zhe-wei.net
- 代碼模擬器：https://codesim.zhe-wei.net
- 預測系統：https://predict.zhe-wei.net

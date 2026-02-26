# 築未科技 — 雲端 24/7 部署指南

**目的**：將系統部署到雲端 VPS，實現 24/7 不間斷運行，不受本地電腦關機影響。

---

## 問題分析

### 當前架構依賴本地主機的服務：
1. **Ollama (port 11460)** — 所有 AI 推理引擎
2. **Vision AI (port 8030)** — 視覺辨識系統
3. **Host API (port 8010)** — 截圖、系統資訊
4. **Dify (port 8080)** — AI 平台
5. **Prediction System (port 8025)** — 預測系統

**核心問題**：Docker 容器透過 `host.docker.internal` 呼叫本地服務，本機關機後整個系統停擺。

---

## 解決方案：雲端完整部署

### 方案 A：Oracle Cloud 免費 VPS（推薦）
- **成本**：完全免費
- **規格**：1 vCPU、1GB RAM（E2.1.Micro）或 2 vCPU、12GB RAM（ARM A1.Flex）
- **限制**：無 GPU，僅能運行小型 Ollama 模型（gemma2:2b, qwen2.5:3b）
- **適用**：測試環境、備援系統

### 方案 B：付費 VPS（生產環境）
- **推薦供應商**：
  - Linode/Akamai：$12/月起（2GB RAM）
  - DigitalOcean：$12/月起（2GB RAM）
  - Vultr：$12/月起（2GB RAM + GPU 選配）
  - AWS EC2 t3.medium：~$30/月（4GB RAM）
- **GPU 選配**：
  - Vultr Cloud GPU：$90/月起（NVIDIA RTX A4000）
  - AWS EC2 g4dn.xlarge：~$0.526/hr（NVIDIA T4）

### 方案 C：混合部署（最佳方案）
- **雲端 VPS**：運行核心服務（brain_server, portal, cms, codesim）
- **本地主機**：運行 GPU 密集服務（Ollama with GPU, Vision AI）
- **連接方式**：Cloudflare Tunnel 或 Tailscale VPN
- **優勢**：成本低、性能好、本地關機時降級運行

---

## 部署步驟（方案 A：Oracle Cloud）

### 1. 建立 Oracle Cloud VPS

參考 `docs/Oracle_Cloud_免費VPS建立指南.md`

關鍵步驟：
```bash
# SSH 連線
ssh -i /path/to/your-key.key ubuntu@<PUBLIC_IP>

# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 登出再登入

# 安裝 Docker Compose
sudo apt install docker-compose-plugin -y
```

### 2. 上傳專案到 VPS

```bash
# 方法 1：Git Clone（推薦）
cd /opt
sudo mkdir zhewei && sudo chown $USER:$USER zhewei
cd zhewei
git clone https://github.com/your-repo/zhe-wei-tech.git .

# 方法 2：rsync 同步
rsync -avz --exclude 'node_modules' --exclude '.git' \
  -e "ssh -i /path/to/key.key" \
  d:/zhe-wei-tech/ ubuntu@<PUBLIC_IP>:/opt/zhewei/
```

### 3. 設定環境變數

```bash
cd /opt/zhewei
nano .env
```

必要環境變數：
```env
# Cloudflare Tunnel Token
CLOUDFLARE_TOKEN=your_tunnel_token_here

# AI Provider Keys（至少設定一個雲端 API）
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
DEEPSEEK_API_KEY=your_deepseek_key

# Ollama 設定（雲端版使用容器內 Ollama）
OLLAMA_BASE_URL=http://ollama:11434
AI_COST_MODE=local_first

# 其他服務
NTFY_SERVER=https://notify.zhewei.tech
```

### 4. 拉取 Ollama 模型（首次部署）

```bash
# 啟動 Ollama 容器
docker compose -f docker-compose.cloud.yml up -d ollama

# 等待 Ollama 啟動（約 10 秒）
sleep 10

# 拉取輕量模型（適合 1GB RAM VPS）
docker exec -it zhewei_ollama ollama pull gemma2:2b
docker exec -it zhewei_ollama ollama pull qwen2.5:3b
docker exec -it zhewei_ollama ollama pull nomic-embed-text

# 如果是 ARM A1.Flex（12GB RAM），可拉取更大模型
docker exec -it zhewei_ollama ollama pull qwen2.5-coder:7b
docker exec -it zhewei_ollama ollama pull llama3.2:3b
```

### 5. 啟動所有服務

```bash
cd /opt/zhewei

# 構建映像
docker compose -f docker-compose.cloud.yml build

# 啟動所有服務
docker compose -f docker-compose.cloud.yml up -d

# 查看日誌
docker compose -f docker-compose.cloud.yml logs -f

# 檢查服務狀態
docker compose -f docker-compose.cloud.yml ps
```

### 6. 驗證部署

```bash
# 檢查 Ollama
curl http://localhost:11434/api/tags

# 檢查 Brain Server
curl http://localhost:8002/health

# 檢查 Gateway
curl http://localhost/nginx-health

# 檢查外網（替換為您的域名）
curl https://jarvis.zhe-wei.net/health
```

---

## 部署步驟（方案 C：混合部署）

### 本地主機設定

1. **保持本地 Ollama 運行**（port 11460）
2. **安裝 Cloudflare Tunnel 或 Tailscale**

```powershell
# 安裝 Cloudflare Tunnel（Windows）
winget install Cloudflare.cloudflared

# 建立本地 Ollama Tunnel
cloudflared tunnel create ollama-local
cloudflared tunnel route dns ollama-local ollama.zhe-wei.net
```

### VPS 設定

修改 `.env`：
```env
# 指向本地 Ollama（透過 Tunnel）
OLLAMA_BASE_URL=https://ollama.zhe-wei.net
```

或使用 Tailscale VPN：
```env
# 指向本地主機 Tailscale IP
OLLAMA_BASE_URL=http://100.x.x.x:11460
```

---

## 監控與維護

### 自動重啟腳本

建立 `/opt/zhewei/scripts/health_check.sh`：

```bash
#!/bin/bash
# 健康檢查與自動重啟

SERVICES=("brain_server" "gateway" "ollama" "portal")

for service in "${SERVICES[@]}"; do
  if ! docker ps | grep -q "zhewei_$service"; then
    echo "[$(date)] $service is down, restarting..."
    docker compose -f /opt/zhewei/docker-compose.cloud.yml up -d $service
  fi
done
```

設定 Cron 每 5 分鐘檢查：
```bash
crontab -e
# 加入：
*/5 * * * * /opt/zhewei/scripts/health_check.sh >> /var/log/zhewei_health.log 2>&1
```

### 日誌管理

```bash
# 查看即時日誌
docker compose -f docker-compose.cloud.yml logs -f brain_server

# 清理舊日誌（保留最近 3 天）
docker system prune -af --filter "until=72h"
```

### 備份策略

```bash
# 每日備份腳本
#!/bin/bash
DATE=$(date +%Y%m%d)
tar -czf /backup/zhewei_$DATE.tar.gz \
  /opt/zhewei/brain_workspace \
  /opt/zhewei/zhewei_memory \
  /opt/zhewei/.env

# 上傳到 Google Drive（需安裝 rclone）
rclone copy /backup/zhewei_$DATE.tar.gz gdrive:zhewei_backup/

# 刪除 7 天前的備份
find /backup -name "zhewei_*.tar.gz" -mtime +7 -delete
```

---

## 成本估算

### 方案 A：Oracle Cloud 免費
- **VPS**：$0/月
- **流量**：10TB/月 免費
- **總計**：$0/月

### 方案 B：Linode 2GB
- **VPS**：$12/月
- **流量**：2TB/月 免費
- **總計**：$12/月

### 方案 C：混合部署
- **VPS**：$12/月（Linode 2GB）
- **本地電費**：~$10/月（24/7 運行）
- **總計**：$22/月

---

## 故障排除

### Ollama 容器無法啟動
```bash
# 檢查日誌
docker logs zhewei_ollama

# 常見問題：記憶體不足
# 解決：使用更小的模型或升級 VPS
```

### Brain Server 無法連接 Ollama
```bash
# 檢查網路
docker exec -it zhewei_brain curl http://ollama:11434/api/tags

# 檢查環境變數
docker exec -it zhewei_brain env | grep OLLAMA
```

### Cloudflare Tunnel 斷線
```bash
# 重啟 Tunnel
docker compose -f docker-compose.cloud.yml restart tunnel

# 檢查 Token
docker logs zhewei_tunnel
```

---

## 性能優化

### 1. 使用輕量模型
```bash
# 推薦模型（1GB RAM VPS）
gemma2:2b          # 1.4GB
qwen2.5:3b         # 1.9GB
phi3:mini          # 2.2GB

# 推薦模型（4GB RAM VPS）
qwen2.5-coder:7b   # 4.7GB
llama3.2:3b        # 2.0GB
mistral:7b         # 4.1GB
```

### 2. 啟用 Swap（記憶體不足時）
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 3. 限制容器資源
修改 `docker-compose.cloud.yml`：
```yaml
services:
  brain_server:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

---

## 下一步

1. ✅ 選擇部署方案（A/B/C）
2. ✅ 建立 VPS 並安裝 Docker
3. ✅ 上傳專案並設定環境變數
4. ✅ 啟動服務並驗證
5. ✅ 設定監控與備份
6. ✅ 測試外網存取

完成後，您的系統將 24/7 運行，不受本地電腦關機影響！

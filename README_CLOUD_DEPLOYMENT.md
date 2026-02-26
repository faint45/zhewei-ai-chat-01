# 築未科技 — 雲端部署解決方案

## 🎯 解決的問題

**問題**：本地電腦關機後，整個系統停止運行。

**原因**：當前架構依賴本地主機服務：
- Ollama AI 引擎 (port 11460)
- Vision AI 視覺辨識 (port 8030)
- Host API 系統資訊 (port 8010)
- Dify AI 平台 (port 8080)
- Prediction 預測系統 (port 8025)

**解決方案**：將系統部署到雲端 VPS，實現 24/7 不間斷運行。

---

## 📦 已建立的檔案

### 1. Docker Compose 雲端配置
- **`docker-compose.cloud.yml`** — 完整雲端部署配置
  - 包含 Ollama 容器（不依賴本地主機）
  - 所有服務完全獨立運行
  - 自動健康檢查與重啟

### 2. Nginx 雲端配置
- **`gateway/nginx.cloud.conf`** — 雲端版 Nginx 配置
  - 移除所有 `host.docker.internal` 依賴
  - 直接路由到容器服務

### 3. 自動化腳本
- **`scripts/deploy_to_cloud.sh`** — 一鍵部署腳本
  - 自動檢測記憶體並選擇合適模型
  - 完整健康檢查
  - 彩色輸出與錯誤處理

- **`scripts/health_monitor.sh`** — 健康監控腳本
  - 定期檢查服務狀態
  - 自動重啟異常服務
  - 磁碟與記憶體監控
  - 建議加入 crontab 每 5 分鐘執行

### 4. 部署文件
- **`docs/deployment/CLOUD_24_7_DEPLOYMENT.md`** — 完整部署指南
  - 三種部署方案（Oracle Cloud 免費 / 付費 VPS / 混合部署）
  - 詳細步驟說明
  - 故障排除指南
  - 性能優化建議

- **`QUICK_CLOUD_DEPLOY.md`** — 快速部署指南
  - 5 分鐘快速上線
  - 精簡步驟
  - 常用指令參考

---

## 🚀 快速開始

### 方案選擇

#### 方案 A：Oracle Cloud 免費 VPS（推薦測試）
- ✅ 完全免費
- ✅ 1GB RAM（可運行輕量模型）
- ❌ 無 GPU

#### 方案 B：付費 VPS（推薦生產）
- Linode/DigitalOcean：$12/月起（2GB RAM）
- Vultr：$12/月起（可選配 GPU）

#### 方案 C：混合部署（最佳方案）
- 雲端：核心服務（brain_server, portal, cms）
- 本地：GPU 服務（Ollama with GPU, Vision AI）
- 連接：Cloudflare Tunnel 或 Tailscale VPN

### 3 步驟部署

```bash
# 1. SSH 連線到 VPS
ssh ubuntu@YOUR_VPS_IP

# 2. 安裝 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 登出再登入

# 3. 上傳專案並部署
cd /opt
sudo mkdir zhewei && sudo chown $USER:$USER zhewei
cd zhewei
git clone YOUR_REPO .

# 設定環境變數
nano .env
# 加入 CLOUDFLARE_TOKEN 和 API Keys

# 執行部署
chmod +x scripts/deploy_to_cloud.sh
./scripts/deploy_to_cloud.sh
```

---

## 📊 雲端部署架構

```
┌─────────────────────────────────────────┐
│         Cloudflare Tunnel               │
│         (zhewei_tunnel)                 │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│         Nginx Gateway                   │
│         (zhewei_gateway)                │
│         Port: 80                        │
└─┬──────┬──────┬──────┬──────┬──────┬───┘
  │      │      │      │      │      │
  ▼      ▼      ▼      ▼      ▼      ▼
┌───┐  ┌───┐  ┌───┐  ┌───┐  ┌───┐  ┌───┐
│Brain│Portal│ CMS │CodeSim│Pred│Bridge│
│8000 │ 8888 │ 8020│ 8001 │8025│ 8003│
└──┬──┘ └───┘  └───┘  └──┬──┘└───┘  └──┬──┘
   │                      │            │
   └──────────┬───────────┴────────────┘
              ▼
      ┌───────────────┐
      │    Ollama     │
      │  (容器內運行)  │
      │  Port: 11434  │
      └───────────────┘
```

---

## 🔧 服務列表

| 服務 | 容器名 | Port | 外網域名 | 狀態 |
|------|--------|------|----------|------|
| Ollama AI | zhewei_ollama | 11434 | - | ✅ 雲端獨立 |
| Brain Server | zhewei_brain | 8002 | jarvis.zhe-wei.net | ✅ 雲端獨立 |
| Portal | zhewei_portal | 8888 | zhe-wei.net | ✅ 雲端獨立 |
| CMS | zhewei_cms | 8020 | cms.zhe-wei.net | ✅ 雲端獨立 |
| CodeSim | zhewei_codesim | 8001 | codesim.zhe-wei.net | ✅ 雲端獨立 |
| Prediction | zhewei_prediction | 8025 | predict.zhe-wei.net | ✅ 雲端獨立 |
| Smart Bridge | zhewei_smart_bridge | 8003 | bridge.zhe-wei.net | ✅ 雲端獨立 |
| Gateway | zhewei_gateway | 80 | - | ✅ 雲端獨立 |
| Tunnel | zhewei_tunnel | - | - | ✅ 雲端獨立 |

**本地依賴服務（可選）：**
- Vision AI (port 8030) — 需本地 GPU，可透過 Tunnel 連接
- Host API (port 8010) — 本地系統資訊，雲端不需要
- Dify (port 8080) — 可選，雲端可獨立部署

---

## 🎛️ 環境變數設定

```env
# Cloudflare Tunnel（必要）
CLOUDFLARE_TOKEN=your_cloudflare_tunnel_token

# AI Provider Keys（至少設定一個雲端 API）
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key

# Ollama 設定（雲端版）
OLLAMA_BASE_URL=http://ollama:11434
AI_COST_MODE=local_first

# 其他服務
NTFY_SERVER=https://notify.zhewei.tech
```

---

## 📈 監控與維護

### 自動健康檢查

```bash
# 設定 crontab
crontab -e

# 加入以下行（每 5 分鐘檢查）
*/5 * * * * /opt/zhewei/scripts/health_monitor.sh >> /var/log/zhewei_health.log 2>&1
```

### 常用指令

```bash
# 查看服務狀態
docker compose -f docker-compose.cloud.yml ps

# 查看日誌
docker compose -f docker-compose.cloud.yml logs -f brain_server

# 重啟服務
docker compose -f docker-compose.cloud.yml restart brain_server

# 更新並重啟
git pull
docker compose -f docker-compose.cloud.yml up -d --build

# 清理舊資源
docker system prune -af --filter "until=72h"
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

## 🆘 故障排除

### Ollama 記憶體不足
```bash
# 使用輕量模型
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
# 檢查網路
docker exec zhewei_brain curl http://ollama:11434/api/tags

# 重啟 Ollama
docker compose -f docker-compose.cloud.yml restart ollama
```

### Cloudflare Tunnel 斷線
```bash
# 檢查日誌
docker logs zhewei_tunnel

# 重啟 Tunnel
docker compose -f docker-compose.cloud.yml restart tunnel
```

---

## ✅ 驗證部署

```bash
# 本地檢查
curl http://localhost:8002/health
curl http://localhost/nginx-health

# 外網檢查
curl https://jarvis.zhe-wei.net/health
curl https://cms.zhe-wei.net/health
curl https://codesim.zhe-wei.net/health
```

---

## 📚 相關文件

- 完整部署指南：`docs/deployment/CLOUD_24_7_DEPLOYMENT.md`
- 快速部署指南：`QUICK_CLOUD_DEPLOY.md`
- Oracle Cloud 建立：`docs/Oracle_Cloud_免費VPS建立指南.md`
- Docker Compose 配置：`docker-compose.cloud.yml`
- Nginx 配置：`gateway/nginx.cloud.conf`

---

## 🎉 完成

您的系統現在可以在雲端 24/7 運行，不受本地電腦關機影響！

**外網存取：**
- 主入口：<https://zhe-wei.net>
- Jarvis AI：<https://jarvis.zhe-wei.net>
- 營建管理：<https://cms.zhe-wei.net>
- 代碼模擬器：<https://codesim.zhe-wei.net>
- 預測系統：<https://predict.zhe-wei.net>

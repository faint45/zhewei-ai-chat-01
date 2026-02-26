# Linode + 本地 GPU 混合部署完整實施方案（台灣用戶版）

## 📋 方案概覽

```
總成本：NT$450/月
├─ 雲端：Linode 2核4GB（NT$360/月）
├─ 本地：RTX 4060 Ti GPU（NT$90/月電費）
└─ 優勢：速度快 + 性能強 + 成本低（節省 97% GPU 成本）

架構：
┌─────────────┐      ┌─────────────┐
│  台灣本地   │      │  Linode     │
│  RTX 4060   │──────│  東京機房   │
│   GPU       │Tunnel│ 2核4GB      │
└─────────────┘      └─────────────┘
        │                    │
        └──────┬─────────────┘
               │
        ┌──────┴──────────┐
        │  Cloudflare     │
        │  統一網關       │
        └─────────────────┘
```

---

## 🚀 第一步：購買 Linode VPS

### 1.1 註冊帳號

**網址：** https://www.linode.com

**步驟：**
1. 點擊 "Sign Up"
2. 輸入 Email、密碼、國家選 Taiwan
3. 驗證 Email

### 1.2 選擇機房

```
Region：Tokyo, JP（東京，日本）
★ 推薦原因：距離台灣最近，延遲最低（30-50ms）
```

### 1.3 選擇方案

```
Plan：Shared CPU
Type：Linode 4GB
Image：Ubuntu 22.04 LTS
Root Password：設定強密碼（記下來！）
SSH Keys：可選（稍後可加入）
Label：zhewei-hybrid-cloud
Tags：hybrid, ai, gpu
```

### 1.4 完成付款

```
Payment Method：Credit Card
接受的卡：Visa, Mastercard, JCB
Billing：Monthly（月付，彈性高）
```

**費用：** $12/月 = NT$360/月

### 1.5 取得 SSH 連線資訊

```
IP Address：139.162.xxx.xxx（建立後顯示）
Username：root
Password：（您設定的密碼）
SSH Command：ssh root@139.162.xxx.xxx
```

---

## 🖥️ 第二步：本地 GPU 環境確認

### 2.1 確認您的本地 GPU 配置

根據系統記錄，您的本地配置：

```
GPU：NVIDIA RTX 4060 Ti 8GB
VRAM：8GB
CUDA：12.1
PyTorch：2.5.1+cu121
Ollama Port：11434
```

### 2.2 確認本地服務運行中

**PowerShell 執行：**

```powershell
# 檢查 Ollama 是否運行
Get-Process ollama

# 檢查 Ollama 可用模型
ollama list

# 預期看到：
# NAME                    ID              SIZE      MODIFIED
# qwen2.5-coder:7b        xxxxxxxx        4.7 GB    xx minutes ago
# deepseek-r1:8b          xxxxxxxx        4.9 GB    xx minutes ago
```

### 2.3 確認 ComfyUI 可用（可選）

```powershell
# 檢查 ComfyUI 是否運行
curl http://localhost:9188

# 預期返回：ComfyUI Web 介面
```

---

## ☁️ 第三步：設定 Linode VPS

### 3.1 SSH 連線到 Linode

**在 Windows PowerShell 執行：**

```powershell
# 使用 SSH 連線（替換為您的實際 IP）
ssh root@139.162.xxx.xxx

# 輸入密碼
```

### 3.2 系統更新

```bash
# 更新系統
apt update && apt upgrade -y

# 安裝基本工具
apt install -y curl wget git vim htop docker.io docker-compose

# 啟動 Docker
systemctl enable docker
systemctl start docker

# 驗證 Docker
docker --version
```

### 3.3 建立 Swap（重要！）

```bash
# 建立 4GB Swap
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# 加入 /etc/fstab
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# 驗證
free -h
# 應該顯示 Swap: 4.0G
```

### 3.4 設定時區

```bash
# 設定台灣時區
timedatectl set-timezone Asia/Taipei
timedatectl
```

---

## 🔧 第四步：部署雲端服務（Linode）

### 4.1 建立專案目錄

```bash
# 建立專案目錄
mkdir -p /opt/zhewei
cd /opt/zhewei

# 設定權限
chmod 755 /opt/zhewei
```

### 4.2 複製專案程式碼

**選項 A：使用 Git（如果有 Git 倉庫）**

```bash
cd /opt/zhewei
git clone https://github.com/your-repo/zhe-wei-tech.git .
```

**選項 B：本地上傳（使用 SCP）**

**在 Windows PowerShell 執行：**

```powershell
# 將本地專案上傳到 Linode（在本地執行）
# 先壓縮專案
Compress-Archive -Path "D:\zhe-wei-tech\*" -DestinationPath "D:\zhewei-deploy.zip"

# 上傳到 Linode
scp D:\zhewei-deploy.zip root@139.162.xxx.xxx:/opt/zhewei/
```

**回到 Linode SSH：**

```bash
cd /opt/zhewei
unzip zhewei-deploy.zip
rm zhewei-deploy.zip
```

### 4.3 建立環境變數檔案

```bash
cd /opt/zhewei

# 建立 .env 檔案
cat > .env << 'EOF'
# ==========================================
# Linode + 本地 GPU 混合部署環境變數
# ==========================================

# Cloudflare Tunnel Token（稍後設定）
CLOUDFLARE_TOKEN=your_cloudflare_token_here

# Ollama 智慧路由
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_GPU_URL=https://ollama-gpu.zhe-wei.net
SMART_ROUTER_ENABLED=true
OLLAMA_PRIORITY=local

# AI Provider API Keys
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key

# 本地服務 URL（透過 Cloudflare Tunnel）
LOCAL_API_BASE=https://local-api.zhe-wei.net
LOCAL_OLLAMA_URL=https://ollama-gpu.zhe-wei.net
LOCAL_COMFYUI_URL=https://comfyui-gpu.zhe-wei.net

# 工作目錄
WORK_DIR=/app/workspace
TEMP_DIR=/app/temp

# 服務端口
BRAIN_SERVER_PORT=8000
SMART_BRIDGE_PORT=8003
PORTAL_PORT=8888
CMS_PORT=8020
CODESIM_PORT=8001
PREDICTION_PORT=8025

# Ntfy 推播
NTFY_SERVER=https://notify.zhewei.tech
NTFY_ADMIN_USER=your_ntfy_user
NTFY_ADMIN_PASS=your_ntfy_pass
NTFY_DEFAULT_TOPIC=zhewei_general

# 資料庫
DB_TYPE=sqlite
SQLITE_PATH=/app/data/brain.db

# 監控
HEALTH_CHECK_INTERVAL=60
AUTO_RESTART=true

# 安全
JWT_SECRET=your_jwt_secret_here
API_RATE_LIMIT=1000

# 混合部署設定
HYBRID_MODE=true
CLOUD_PROVIDER=linode
LOCAL_GPU_ENABLED=true
TUNNEL_HEALTH_CHECK=true
EOF

chmod 600 .env
```

### 4.4 建立 docker-compose.yml

```bash
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # ==========================================
  # Nginx Gateway（統一入口）
  # ==========================================
  gateway:
    image: nginx:alpine
    container_name: zhewei_gateway
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./gateway/nginx.cloud.conf:/etc/nginx/nginx.conf:ro
      - ./gateway/ssl:/etc/nginx/ssl:ro
    depends_on:
      - brain_server
      - smart_bridge
      - portal
      - cms
      - codesim
      - prediction
    networks:
      - zhewei_net
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ==========================================
  # Brain Server（核心 AI 服務）
  # ==========================================
  brain_server:
    build:
      context: .
      dockerfile: Dockerfile.brain
    container_name: zhewei_brain
    environment:
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://ollama:11434}
      - OLLAMA_GPU_URL=${OLLAMA_GPU_URL}
      - SMART_ROUTER_ENABLED=${SMART_ROUTER_ENABLED:-true}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
      - DB_TYPE=${DB_TYPE:-sqlite}
      - SQLITE_PATH=${SQLITE_PATH:-/app/data/brain.db}
    volumes:
      - ./brain_workspace:/app/workspace
      - brain_data:/app/data
      - .:/app:ro
    ports:
      - "8000:8000"
    networks:
      - zhewei_net
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ==========================================
  # Smart Bridge（智慧橋接）
  # ==========================================
  smart_bridge:
    build:
      context: .
      dockerfile: Dockerfile.bridge
    container_name: zhewei_bridge
    environment:
      - BRAIN_SERVER_URL=http://brain_server:8000
      - LOCAL_API_BASE=${LOCAL_API_BASE}
      - HYBRID_MODE=${HYBRID_MODE:-true}
    volumes:
      - ./bridge_workspace:/app/workspace
    ports:
      - "8003:8003"
    networks:
      - zhewei_net
    restart: unless-stopped

  # ==========================================
  # Portal（入口網站）
  # ==========================================
  portal:
    image: nginx:alpine
    container_name: zhewei_portal
    volumes:
      - ./portal:/usr/share/nginx/html:ro
      - ./portal/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "8888:80"
    networks:
      - zhewei_net
    restart: unless-stopped

  # ==========================================
  # CMS（營建管理系統）
  # ==========================================
  cms:
    build:
      context: ./construction_mgmt
      dockerfile: Dockerfile
    container_name: zhewei_cms
    environment:
      - DATABASE_URL=sqlite:///app/data/cms.db
      - WHISPER_MODEL=base
    volumes:
      - ./construction_mgmt/data:/app/data
      - ./construction_mgmt/uploads:/app/uploads
    ports:
      - "8020:8020"
    networks:
      - zhewei_net
    restart: unless-stopped

  # ==========================================
  # CodeSim（代碼模擬器）
  # ==========================================
  codesim:
    build:
      context: ./simulator
      dockerfile: Dockerfile
    container_name: zhewei_codesim
    volumes:
      - ./simulator/projects:/app/projects
    ports:
      - "8001:8001"
    networks:
      - zhewei_net
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

  # ==========================================
  # Prediction（預測系統）
  # ==========================================
  prediction:
    build:
      context: ./prediction_modules
      dockerfile: Dockerfile
    container_name: zhewei_prediction
    volumes:
      - ./prediction_modules/data_cache:/app/data_cache
    ports:
      - "8025:8025"
    networks:
      - zhewei_net
    restart: unless-stopped

  # ==========================================
  # Ollama CPU（雲端備援）
  # ==========================================
  ollama:
    image: ollama/ollama:latest
    container_name: zhewei_ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    networks:
      - zhewei_net
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 2G

  # ==========================================
  # Cloudflare Tunnel
  # ==========================================
  tunnel:
    image: cloudflare/cloudflared:latest
    container_name: zhewei_tunnel
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TOKEN}
    networks:
      - zhewei_net
    restart: unless-stopped
    depends_on:
      - gateway
      - brain_server

networks:
  zhewei_net:
    driver: bridge

volumes:
  brain_data:
  ollama_data:
EOF
```

---

## 🌐 第五步：設定 Cloudflare Tunnel

### 5.1 安裝 cloudflared（在本地 Windows）

**PowerShell（以管理員身份執行）：**

```powershell
# 下載 cloudflared
Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile "C:\Windows\System32\cloudflared.exe"

# 驗證安裝
cloudflared --version
```

### 5.2 登入 Cloudflare

```powershell
# 登入 Cloudflare（會開啟瀏覽器）
cloudflared tunnel login

# 選擇您的域名：zhe-wei.net
```

### 5.3 建立 Tunnel

```powershell
# 建立 Tunnel
cloudflared tunnel create zhewei-hybrid-gpu

# 記下 Tunnel ID
# 例如：546fffc1-eb7d-4f9a-a3df-d30a1940aa0c
```

### 5.4 設定 DNS 路由

```powershell
# 為本地 GPU Ollama 建立子域名
cloudflared tunnel route dns zhewei-hybrid-gpu ollama-gpu.zhe-wei.net

# 為本地 API 建立子域名（可選）
cloudflared tunnel route dns zhewei-hybrid-gpu local-api.zhe-wei.net

# 為 ComfyUI 建立子域名（可選）
cloudflared tunnel route dns zhewei-hybrid-gpu comfyui-gpu.zhe-wei.net
```

### 5.5 建立設定檔

**檔案：`C:\Users\<您的用戶名>\.cloudflared\config.yml`**

```yaml
tunnel: 546fffc1-eb7d-4f9a-a3df-d30a1940aa0c
credentials-file: C:\Users\<您的用戶名>\.cloudflared\546fffc1-eb7d-4f9a-a3df-d30a1940aa0c.json

ingress:
  # 本地 Ollama GPU 服務
  - hostname: ollama-gpu.zhe-wei.net
    service: http://localhost:11434
    originRequest:
      noTLSVerify: true

  # 本地 API 服務（可選）
  - hostname: local-api.zhe-wei.net
    service: http://localhost:8002
    originRequest:
      noTLSVerify: true

  # 本地 ComfyUI（可選）
  - hostname: comfyui-gpu.zhe-wei.net
    service: http://localhost:9188
    originRequest:
      noTLSVerify: true

  # 拒絕其他請求
  - service: http_status:404
```

### 5.6 取得 Tunnel Token

```powershell
# 列出 Tunnel
cloudflared tunnel list

# 取得 Tunnel Token（用於 Linode Docker）
cloudflared tunnel token 546fffc1-eb7d-4f9a-a3df-d30a1940aa0c

# 複製這個 Token，稍後加入 Linode 的 .env 檔案
```

### 5.7 將 Token 加入 Linode .env

**回到 Linode SSH：**

```bash
cd /opt/zhewei

# 編輯 .env，加入 Tunnel Token
vim .env

# 修改這一行：
# CLOUDFLARE_TOKEN=your_cloudflare_token_here
# 改為：
# CLOUDFLARE_TOKEN=eyJh...（您複製的 Token）
```

### 5.8 安裝 Windows 服務（本地）

```powershell
# 安裝為 Windows 服務
cloudflared service install

# 啟動服務
net start cloudflared

# 設定開機自動啟動
sc config cloudflared start= auto

# 驗證服務狀態
Get-Service cloudflared
```

---

## 🚀 第六步：啟動所有服務

### 6.1 啟動 Linode 雲端服務

```bash
cd /opt/zhewei

# 啟動服務
docker-compose up -d

# 查看狀態
docker-compose ps

# 查看日誌
docker-compose logs -f
```

### 6.2 驗證服務運行

```bash
# 檢查所有容器是否運行
docker ps

# 預期看到 7-8 個容器運行中：
# - zhewei_gateway
# - zhewei_brain
# - zhewei_bridge
# - zhewei_portal
# - zhewei_cms
# - zhewei_codesim
# - zhewei_prediction
# - zhewei_ollama
# - zhewei_tunnel
```

### 6.3 檢查本地 Tunnel 連線

**在 Windows PowerShell：**

```powershell
# 檢查 Tunnel 狀態
cloudflared tunnel info zhewei-hybrid-gpu

# 預期看到 Connector 狀態為 Connected
```

---

## 🧪 第七步：測試混合部署

### 7.1 測試雲端服務（Linode）

```bash
# SSH 在 Linode 執行

# 測試 Brain Server
curl http://localhost:8000/health

# 測試 Ollama（雲端 CPU）
curl http://localhost:11434/api/tags

# 測試 Portal
curl http://localhost:8888

# 測試 CMS
curl http://localhost:8020/healthz
```

### 7.2 測試本地 GPU（透過 Tunnel）

**在 Windows PowerShell：**

```powershell
# 測試本地 Ollama GPU（透過 Cloudflare Tunnel）
curl https://ollama-gpu.zhe-wei.net/api/tags

# 預期看到本地模型列表，例如：
# qwen2.5-coder:7b
# deepseek-r1:8b
```

### 7.3 測試智慧路由

```powershell
# 測試智慧路由 API
$headers = @{
    "Content-Type" = "application/json"
}

$body = @{
    "model" = "qwen2.5-coder:7b"
    "messages" = @(
        @{
            "role" = "user"
            "content" = "你好，測試混合部署"
        }
    )
} | ConvertTo-Json

# 呼叫 API（會自動路由到本地 GPU）
Invoke-RestMethod -Uri "https://jarvis.zhe-wei.net/api/ai/chat" -Method POST -Headers $headers -Body $body
```

---

## 🔍 第八步：監控與維護

### 8.1 建立健康檢查腳本

**Linode SSH：**

```bash
cat > /opt/zhewei/health_check.sh << 'EOF'
#!/bin/bash
# 混合部署健康檢查腳本

echo "=== Zhewei Hybrid Deployment Health Check ==="
echo "Date: $(date)"
echo ""

# 檢查 Docker 容器
echo "--- Docker Containers ---"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 檢查資源使用
echo ""
echo "--- Resource Usage ---"
free -h
df -h /
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# 檢查 Tunnel 連線
echo ""
echo "--- Tunnel Connectivity ---"
curl -s -o /dev/null -w "%{http_code}" https://ollama-gpu.zhe-wei.net/api/tags
echo " (200 = OK)"

# 檢查服務健康
echo ""
echo "--- Service Health ---"
for port in 8000 8003 8888 8020 8001 8025; do
    status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health || echo "000")
    echo "Port $port: $status"
done

echo ""
echo "=== Health Check Complete ==="
EOF

chmod +x /opt/zhewei/health_check.sh
```

### 8.2 設定定時檢查（Cron）

```bash
# 編輯 crontab
crontab -e

# 加入以下行（每 5 分鐘檢查一次）
*/5 * * * * /opt/zhewei/health_check.sh >> /var/log/zhewei-health.log 2>&1

# 每天凌晨 3 點重啟服務（清理記憶體）
0 3 * * * cd /opt/zhewei && docker-compose restart
```

### 8.3 監控 Dashboard

訪問以下網址監控狀態：

```
主系統：     https://jarvis.zhe-wei.net
監控面板：   https://jarvis.zhe-wei.net/hybrid-dashboard
智慧路由：   https://jarvis.zhe-wei.net/api/router/status
```

---

## 📊 成本分析

### 月度成本（台幣）

| 項目 | 成本 | 說明 |
|------|------|------|
| **Linode VPS** | NT$360/月 | 2核4GB，東京機房 |
| **本地電費** | NT$90/月 | RTX 4060 Ti 每天 4 小時 |
| **Cloudflare** | NT$0/月 | 免費方案 |
| **域名** | NT$15/月 | zhe-wei.net |
| **流量** | NT$0/月 | Linode 4TB/月 免費 |
| **---** | **---** | **---** |
| **總計** | **NT$465/月** | 約 NT$5,580/年 |

### 與純雲端 GPU 對比

| 方案 | 月費 | 年費 | 性能 |
|------|------|------|------|
| **純雲端 GPU** | NT$15,000 | NT$180,000 | V100/A10 |
| **混合部署** | NT$465 | NT$5,580 | RTX 4060 Ti |
| **節省** | **97%** | **97%** | **本地 GPU 更快** |

---

## 🚨 故障排除

### 問題 1：Tunnel 無法連線

**症狀：** `curl https://ollama-gpu.zhe-wei.net` 無回應

**解決：**

```powershell
# Windows PowerShell
# 1. 檢查本地 Ollama 是否運行
ollama list

# 2. 重啟 Tunnel 服務
net stop cloudflared
net start cloudflared

# 3. 查看 Tunnel 日誌
cd C:\Users\<您的用戶名>\.cloudflared
Get-Content cloudflared.log -Tail 50
```

### 問題 2：Linode 服務無法啟動

**症狀：** `docker-compose up -d` 失敗

**解決：**

```bash
# SSH 在 Linode

# 1. 檢查 Docker 是否運行
systemctl status docker

# 2. 檢查端口是否被佔用
netstat -tlnp | grep -E '8000|8003|8888|8020|8001|8025|11434'

# 3. 清理並重啟
cd /opt/zhewei
docker-compose down
docker system prune -f
docker-compose up -d
```

### 問題 3：記憶體不足

**症狀：** OOM Killer 終止容器

**解決：**

```bash
# 檢查記憶體使用
free -h
docker stats --no-stream

# 減少 Ollama 記憶體限制
docker update --memory=1g zhewei_ollama

# 或增加 Swap（已設定 4GB）
swapon -s
```

### 問題 4：智慧路由沒有切換到本地 GPU

**症狀：** API 回應慢（使用雲端 CPU Ollama）

**解決：**

```bash
# 檢查本地 Tunnel 是否運行（Windows PowerShell）
Get-Service cloudflared

# 檢查本地 Ollama 是否運行
ollama list

# 檢查路由狀態
curl https://jarvis.zhe-wei.net/api/router/status

# 手動測試本地 Ollama
curl https://ollama-gpu.zhe-wei.net/api/generate -d '{
  "model": "qwen2.5-coder:7b",
  "prompt": "test"
}'
```

---

## 🎉 完成！

恭喜！您已成功建立 **Linode + 本地 GPU 混合部署**！

### 架構總覽

```
台灣本地                    網際網路                   Linode 東京
┌──────────┐               ┌──────────┐              ┌──────────┐
│ RTX 4060 │◄──Tunnel────►│ Cloudflare│◄──Tunnel───►│ 2核4GB   │
│ Ollama   │               │  Gateway │              │ Docker   │
│ ComfyUI  │               │          │              │ Services │
└──────────┘               └──────────┘              └──────────┘
     │                           │                          │
     └───────────────────────────┴──────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │   https://jarvis.zhe-wei.net   │
                    │   統一入口（自動路由）          │
                    └─────────────────────────┘
```

### 訪問您的系統

```
主入口：      https://jarvis.zhe-wei.net
登入頁面：    https://jarvis.zhe-wei.net/jarvis-login
管理後台：    https://jarvis.zhe-wei.net/admin-commercial
監控面板：    https://jarvis.zhe-wei.net/hybrid-dashboard
```

### 總成本

```
NT$465/月 = NT$5,580/年
節省 97% 雲端 GPU 成本！
```

**享受您的 AI 混合部署系統吧！** 🚀

# Oracle Cloud + 本地 GPU 混合部署完整指南

## 📋 方案概覽

```
總成本：NT$90-150/月（極低成本！）
├─ 雲端：Oracle Cloud 免費方案（NT$0/月）
├─ 本地：RTX 4060 Ti GPU（NT$90/月電費）
└─ 可選：額外付費升級（NT$360/月起）

架構：
┌─────────────┐      ┌─────────────┐
│  台灣本地   │      │ Oracle Cloud│
│  RTX 4060   │──────│  日本機房   │
│   GPU       │Tunnel│ 免費方案    │
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

## 🎯 為什麼選擇 Oracle Cloud + 本地 GPU？

### ✅ 最大優勢：極低成本！

| 項目 | 成本 | 說明 |
|------|------|------|
| **Oracle Cloud** | NT$0/月 | 永久免費方案 |
| **本地 GPU 電費** | NT$90/月 | RTX 4060 Ti 每天 4 小時 |
| **總計** | **NT$90/月** | **最便宜的混合部署！** |

### ✅ 其他優勢

- 🆓 **永久免費**：Always Free Tier 永不過期
- 🌏 **日本機房**：距離台灣近（60-80ms）
- 💳 **台灣信用卡**：Visa/Mastercard 可用
- 🔓 **不需實名認證**：無需台胞證
- 🚀 **足夠的配置**：1核1GB + 50GB 儲存

### ⚠️ 限制

- 💾 **記憶體較小**：僅 1GB RAM（需要優化）
- 🔥 **無法擴展**：免費方案固定配置
- ⏱️ **可能回收**：閒置帳號可能被回收
- 🚫 **無 GPU**：免費方案無 GPU 選項

---

## 🚀 第一步：註冊 Oracle Cloud

### 1.1 前往 Oracle Cloud 官網

**網址：** https://www.oracle.com/cloud/free/

### 1.2 點擊 "Start for Free"

### 1.3 填寫帳號資訊

```
Email：您的 Gmail 或公司信箱
Country/Region：Taiwan
Account Type：Personal（個人）
```

### 1.4 驗證 Email

- 檢查信箱，點擊驗證連結

### 1.5 設定密碼

```
密碼要求：
- 至少 12 個字元
- 包含大小寫字母
- 包含數字
- 包含特殊符號
```

### 1.6 驗證手機號碼

```
Country Code：+886（台灣）
Phone Number：您的手機號碼（去掉第一個 0）
例如：0912345678 → 912345678
```

- 輸入收到的簡訊驗證碼

### 1.7 驗證信用卡

**注意：這是驗證用途，不會扣款！**

```
Card Type：Visa / Mastercard
Card Number：您的信用卡號
Expiration Date：到期日
CVV：安全碼
```

- Oracle 會預扣 $1-5 美元驗證，稍後返還
- 免費方案永遠不會收費（除非您升級）

### 1.8 選擇 Home Region

```
推薦選擇：
1. Japan East (Tokyo) — 距離台灣最近
2. Japan Central (Osaka) — 距離台灣近
3. South Korea Central (Seoul) — 距離台灣近
```

**建議選擇：Japan East (Tokyo)**

---

## 🖥️ 第二步：建立免費 VM

### 2.1 登入 Oracle Cloud Console

**網址：** https://cloud.oracle.com

### 2.2 建立 VM Instance

**步驟：**

1. 點擊左上選單 ☰
2. Compute → Instances
3. 點擊 "Create Instance"

### 2.3 配置 VM

**Name：**
```
zhewei-hybrid-cloud
```

**Placement：**
```
AD 1（默認）
```

**Image and Shape：**
```
Image：Canonical Ubuntu 22.04
Shape：VM.Standard.E2.1.Micro（永遠免費）
- OCPU：1
- Memory：1GB
- Network：480 Mbps
```

**Networking：**
```
Virtual Cloud Network：創建新的 VCN
Subnet：Public Subnet
Public IP Address：Assign
```

**Add SSH Keys：**

**選項 A：使用您現有的 SSH 金鑰**

```powershell
# Windows PowerShell 生成 SSH 金鑰（如果還沒有）
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 顯示公鑰
Get-Content C:\Users\$env:USERNAME\.ssh\id_rsa.pub
```

- 複製公鑰內容貼到 Oracle Cloud

**選項 B：讓 Oracle 生成金鑰**
- 選 "Generate SSH key pair"
- 下載私鑰和公鑰（保存好！）

**Boot Volume：**
```
Boot Volume：50GB（免費上限）
```

### 2.4 點擊 "Create"

- 等待 1-2 分鐘，VM 建立完成

### 2.5 取得連線資訊

**在 Instances 頁面，查看：**

```
Public IP：132.145.xxx.xxx（這是您的 IP）
SSH Command：ssh opc@132.145.xxx.xxx
Username：opc（不是 root！）
```

---

## 🔓 第三步：設定防火牆規則

### 3.1 開放必要端口

**步驟：**

1. 進入 Instance Details
2. 點擊 "Subnet: ..." 連結
3. 點擊 "Default Security List"
4. 點擊 "Add Ingress Rules"

### 3.2 加入規則

**規則 1：HTTP**
```
Stateless: No
Source Type: CIDR
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
Destination Port Range: 80
Description: HTTP
```

**規則 2：HTTPS**
```
Stateless: No
Source Type: CIDR
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
Destination Port Range: 443
Description: HTTPS
```

**規則 3：SSH**
```
Stateless: No
Source Type: CIDR
Source CIDR: 0.0.0.0/0  （或您的 IP/32 更安全）
IP Protocol: TCP
Destination Port Range: 22
Description: SSH
```

**規則 4：Brain Server**
```
Stateless: No
Source Type: CIDR
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
Destination Port Range: 8000
Description: Brain Server
```

**規則 5：其他服務端口**
```
端口：8001, 8003, 8020, 8025, 8888, 11434
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
```

---

## ☁️ 第四步：連線並設定 VM

### 4.1 SSH 連線

**Windows PowerShell：**

```powershell
# 使用 SSH 連線（使用 opc 用戶，不是 root）
ssh opc@132.145.xxx.xxx

# 如果您使用 Oracle 生成的金鑰
ssh -i C:\path\to\private_key opc@132.145.xxx.xxx
```

### 4.2 系統更新

```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝基本工具
sudo apt install -y curl wget git vim htop docker.io docker-compose

# 啟動 Docker
sudo systemctl enable docker
sudo systemctl start docker

# 驗證 Docker
sudo docker --version
```

### 4.3 建立 Swap（非常重要！）

因為只有 1GB RAM，必須建立足夠的 Swap：

```bash
# 建立 8GB Swap（比 RAM 大）
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 加入 /etc/fstab
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 驗證
free -h
# 應該顯示 Swap: 8.0G
```

### 4.4 優化記憶體使用

```bash
# 安裝 early OOM killer
sudo apt install -y earlyoom
sudo systemctl enable earlyoom
sudo systemctl start earlyoom

# 設定 swappiness（更積極使用 Swap）
echo 'vm.swappiness=80' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 4.5 設定時區

```bash
sudo timedatectl set-timezone Asia/Taipei
timedatectl
```

---

## 🔧 第五步：優化部署（針對 1GB RAM）

### 5.1 建立專案目錄

```bash
sudo mkdir -p /opt/zhewei
sudo chown opc:opc /opt/zhewei
cd /opt/zhewei
```

### 5.2 複製專案（精簡版）

由於記憶體限制，我們只部署核心服務：

**本地上傳（Windows PowerShell）：**

```powershell
# 只上傳必要檔案
$files = @(
    "ai_service.py",
    "ai_modules\",
    "brain_server.py",
    "brain_modules\",
    "brain_workspace\",
    "gateway\nginx.cloud.conf",
    "Dockerfile.brain",
    "requirements.txt"
)

# 壓縮必要檔案
Compress-Archive -Path $files -DestinationPath "D:\zhewei-core.zip"

# 上傳到 Oracle Cloud
scp D:\zhewei-core.zip opc@132.145.xxx.xxx:/opt/zhewei/
```

**Oracle Cloud VM：**

```bash
cd /opt/zhewei
unzip zhewei-core.zip
rm zhewei-core.zip
```

### 5.3 建立優化的 .env

```bash
cat > /opt/zhewei/.env << 'EOF'
# ==========================================
# Oracle Cloud + 本地 GPU 混合部署
# 針對 1GB RAM 優化配置
# ==========================================

# Cloudflare Tunnel Token
CLOUDFLARE_TOKEN=your_cloudflare_token_here

# Ollama 智慧路由
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_GPU_URL=https://ollama-gpu.zhe-wei.net
SMART_ROUTER_ENABLED=true
OLLAMA_PRIORITY=local

# AI Provider API Keys
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key

# 本地服務 URL
LOCAL_OLLAMA_URL=https://ollama-gpu.zhe-wei.net
LOCAL_COMFYUI_URL=https://comfyui-gpu.zhe-wei.net

# 工作目錄
WORK_DIR=/app/workspace
TEMP_DIR=/tmp

# 服務端口
BRAIN_SERVER_PORT=8000
PORTAL_PORT=8888

# Ntfy 推播
NTFY_SERVER=https://notify.zhewei.tech
NTFY_DEFAULT_TOPIC=zhewei_general

# 資料庫（使用 SQLite）
DB_TYPE=sqlite
SQLITE_PATH=/app/data/brain.db

# 監控
HEALTH_CHECK_INTERVAL=60

# 安全
JWT_SECRET=your_jwt_secret_here

# 混合部署設定
HYBRID_MODE=true
CLOUD_PROVIDER=oracle
LOCAL_GPU_ENABLED=true

# Oracle Cloud 優化
ORACLE_FREE_TIER=true
MEMORY_LIMIT_MB=800
EOF

chmod 600 /opt/zhewei/.env
```

### 5.4 建立精簡版 docker-compose.yml

只運行核心服務，節省記憶體：

```bash
cat > /opt/zhewei/docker-compose.yml << 'EOF'
version: '3.8'

services:
  # ==========================================
  # Nginx Gateway（精簡版）
  # ==========================================
  gateway:
    image: nginx:alpine
    container_name: zhewei_gateway
    ports:
      - "80:80"
    volumes:
      - ./gateway/nginx.cloud.conf:/etc/nginx/nginx.conf:ro
    networks:
      - zhewei_net
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 50M

  # ==========================================
  # Brain Server（核心服務，限制記憶體）
  # ==========================================
  brain_server:
    build:
      context: .
      dockerfile: Dockerfile.brain
    container_name: zhewei_brain
    environment:
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL}
      - OLLAMA_GPU_URL=${OLLAMA_GPU_URL}
      - SMART_ROUTER_ENABLED=${SMART_ROUTER_ENABLED:-true}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
      - DB_TYPE=${DB_TYPE:-sqlite}
      - SQLITE_PATH=${SQLITE_PATH}
      - HYBRID_MODE=true
    volumes:
      - brain_data:/app/data
      - .:/app:ro
    ports:
      - "8000:8000"
    networks:
      - zhewei_net
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.8'
          memory: 400M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 60s
      timeout: 10s
      retries: 5
      start_period: 60s

  # ==========================================
  # Ollama CPU（雲端備援，限制資源）
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
          cpus: '0.5'
          memory: 300M
    environment:
      - OLLAMA_NUM_PARALLEL=1
      - OLLAMA_MAX_LOADED_MODELS=1

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
    deploy:
      resources:
        limits:
          memory: 50M

networks:
  zhewei_net:
    driver: bridge

volumes:
  brain_data:
  ollama_data:
EOF
```

---

## 🌐 第六步：設定 Cloudflare Tunnel

與 Linode 方案相同，請參考之前的設定。

### 快速設定摘要：

```powershell
# 1. 安裝 cloudflared（如果還沒安裝）
# 2. 登入
cloudflared tunnel login

# 3. 建立 Tunnel
cloudflared tunnel create zhewei-oracle-hybrid

# 4. 設定 DNS
cloudflared tunnel route dns zhewei-oracle-hybrid ollama-gpu.zhe-wei.net
cloudflared tunnel route dns zhewei-oracle-hybrid local-api.zhe-wei.net

# 5. 取得 Token
cloudflared tunnel token <tunnel-id>
```

---

## 🚀 第七步：啟動服務

### 7.1 啟動容器

```bash
cd /opt/zhewei

# 啟動服務
sudo docker-compose up -d

# 查看狀態
sudo docker-compose ps

# 查看日誌
sudo docker-compose logs -f brain_server
```

### 7.2 監控記憶體使用

```bash
# 持續監控
watch -n 2 'free -h && docker stats --no-stream'
```

### 7.3 如果記憶體不足

```bash
# 檢查哪個容器使用最多記憶體
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

# 重啟特定容器
docker restart zhewei_ollama

# 清理 Docker
docker system prune -f
```

---

## 🧪 第八步：測試部署

### 8.1 測試雲端服務

```bash
# SSH 在 Oracle VM 執行

# 測試 Brain Server
curl http://localhost:8000/health

# 測試 Ollama（雲端 CPU）
curl http://localhost:11434/api/tags
```

### 8.2 測試本地 GPU

```powershell
# Windows PowerShell

# 測試本地 Ollama（透過 Tunnel）
curl https://ollama-gpu.zhe-wei.net/api/tags

# 預期看到本地模型列表
```

### 8.3 測試智慧路由

```powershell
# 測試 API 呼叫（自動路由到本地 GPU）
Invoke-RestMethod -Uri "https://jarvis.zhe-wei.net/api/ai/chat" -Method POST -Body '{
    "model": "qwen2.5-coder:7b",
    "messages": [{"role": "user", "content": "測試 Oracle Cloud 混合部署"}]
}' -ContentType "application/json"
```

---

## 💾 第九步：資料備份（重要！）

### 9.1 自動備份腳本

```bash
cat > /opt/zhewei/backup.sh << 'EOF'
#!/bin/bash
# Oracle Cloud 自動備份腳本

BACKUP_DIR="/home/opc/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 建立備份目錄
mkdir -p $BACKUP_DIR

# 備份資料庫
docker exec zhewei_brain cat /app/data/brain.db > $BACKUP_DIR/brain_$DATE.db

# 備份環境變數
cp /opt/zhewei/.env $BACKUP_DIR/env_$DATE

# 備份 Docker Volume
docker run --rm -v zhewei_brain_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/brain_data_$DATE.tar.gz -C /data .

# 上傳到 Oracle Object Storage（可選）
# oci os object put --bucket-name zhewei-backups --file $BACKUP_DIR/brain_$DATE.db

# 清理舊備份（保留 7 天）
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /opt/zhewei/backup.sh
```

### 9.2 設定自動備份

```bash
# 編輯 crontab
crontab -e

# 每天凌晨 2 點備份
0 2 * * * /opt/zhewei/backup.sh >> /var/log/zhewei-backup.log 2>&1
```

---

## 📊 成本分析

### Oracle Cloud 免費方案 + 本地 GPU

| 項目 | 成本 | 說明 |
|------|------|------|
| **Oracle Cloud VM** | **NT$0/月** | 永久免費 |
| **本地 GPU 電費** | NT$90/月 | RTX 4060 Ti 每天 4 小時 |
| **域名** | NT$15/月 | zhe-wei.net |
| **流量** | NT$0/月 | 免費 10TB/月 |
| **---** | **---** | **---** |
| **總計** | **NT$105/月** | 約 NT$1,260/年 |

### 與其他方案對比

| 方案 | 月費 | 年費 | 總成本 |
|------|------|------|--------|
| **Oracle + 本地 GPU** | **NT$105** | **NT$1,260** | ⭐ 最便宜 |
| **Linode + 本地 GPU** | NT$465 | NT$5,580 | 性能好 |
| **騰訊雲 + 本地 GPU** | NT$555 | NT$6,660 | 中國快 |
| **純雲端 GPU** | NT$15,000 | NT$180,000 | 最貴 |

**節省：** 比 Linode 方案便宜 **77%**，比純雲端 GPU 便宜 **99%**！

---

## 🚨 故障排除

### 問題 1：VM 被回收（最常見）

**症狀：** VM 突然消失或無法連線

**原因：** Oracle 免費帳號閒置太久會被回收

**預防：**

```bash
# 設定定時 ping（每 10 分鐘）
crontab -e

# 加入：
*/10 * * * * curl -s https://httpbin.org/get > /dev/null

# 或使用健康檢查腳本
*/10 * * * * /opt/zhewei/health_check.sh
```

### 問題 2：記憶體不足（OOM）

**症狀：** 容器被殺死、服務重啟

**解決：**

```bash
# 增加 Swap（已設定 8GB）
sudo swapon -s

# 減少並發連線數
# 編輯 docker-compose.yml，降低 OLLAMA_NUM_PARALLEL

# 限制容器記憶體（已設定）
docker update --memory=300m zhewei_ollama
docker update --memory=400m zhewei_brain
```

### 問題 3：CPU 100%

**症狀：** 系統變慢、回應延遲

**解決：**

```bash
# 查看哪個程序使用最多 CPU
top

# 限制 Docker 容器 CPU
docker update --cpus=0.5 zhewei_ollama

# 使用輕量級模型
# 在本地 GPU 運行較大模型，雲端只運行小模型
```

### 問題 4：Tunnel 連線問題

**症狀：** 無法從外網訪問

**解決：**

```powershell
# Windows PowerShell

# 檢查 Tunnel 狀態
cloudflared tunnel info zhewei-oracle-hybrid

# 重啟 Tunnel 服務
net stop cloudflared
net start cloudflared

# 檢查防火牆
# 確認 Oracle Cloud 安全列表已開放端口
```

---

## 🔄 升級選項

如果需要更多資源，Oracle Cloud 提供付費升級：

| 配置 | 規格 | 月費（估計） |
|------|------|-------------|
| **標準 2.1** | 1 OCPU, 15GB RAM | NT$360/月 |
| **標準 2.2** | 2 OCPU, 30GB RAM | NT$720/月 |
| **靈活形狀** | 自定義 CPU/RAM | 按用量計費 |

**升級方式：**
- 進入 Instance Details
- 點擊 "Edit"
- 選擇新的 Shape
- 需要綁定付費帳戶

---

## 🎉 完成！

恭喜！您已成功建立 **Oracle Cloud + 本地 GPU 混合部署**！

### 架構總覽

```
台灣本地                    網際網路                   Oracle Cloud
┌──────────┐               ┌──────────┐              ┌──────────┐
│ RTX 4060 │◄──Tunnel────►│ Cloudflare│◄──Tunnel───►│ 1核1GB   │
│ Ollama   │               │  Gateway │              │ 免費 VM  │
│ ComfyUI  │               │          │              │ 日本     │
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
本地 GPU：    https://ollama-gpu.zhe-wei.net
```

### 總成本

```
NT$105/月 = NT$1,260/年
節省 99% 雲端 GPU 成本！
```

### 注意事項

⚠️ **重要提醒：**
1. 定期使用 VM（每週至少一次）避免被回收
2. 監控記憶體使用（只有 1GB）
3. 定期備份資料
4. 考慮升級到付費方案如果需要更多資源

**享受您的免費 AI 混合部署系統吧！** 🚀

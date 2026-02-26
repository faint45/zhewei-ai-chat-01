# Oracle Cloud Failover 部署指南

## 架構概覽

```
正常運行：
  用戶 → Cloudflare → 本地 Windows (RTX 4060 Ti)
                         ↓ 每30分鐘同步
                    Google Drive
                         ↓ 離線時自動拉取
                    Oracle Cloud VPS (1GB RAM)

本地離線時：
  用戶 → Cloudflare → Oracle Cloud VPS (failover)
                       ├─ Portal (zhe-wei.net)
                       ├─ Brain Server (cloud AI only)
                       ├─ CMS (cms.zhe-wei.net)
                       ├─ CodeSim (codesim.zhe-wei.net)
                       └─ Smart Bridge
```

## 成本

| 項目 | 費用 |
|------|------|
| Oracle Cloud Always Free | NT$0/月 |
| Google Drive 15GB | NT$0/月 |
| Cloudflare Tunnel | NT$0/月 |
| **總計** | **NT$0/月** |

## 前置需求

- Oracle Cloud 帳號（台灣 Visa/Mastercard 可用）
- Google Drive（rclone 設定完成）
- Cloudflare Zero Trust（已有）

---

## Step 1: 建立 Oracle Cloud VM

1. 登入 https://cloud.oracle.com
2. Compute → Instances → Create Instance
3. 選擇：
   - **Shape**: VM.Standard.E2.1.Micro (Always Free)
   - **Image**: Ubuntu 22.04
   - **Region**: Japan East (Tokyo) 或 Japan Central (Osaka)
   - **Boot Volume**: 50GB
4. 下載 SSH Key 並記錄 Public IP

## Step 2: 設定 VM

```bash
# SSH 進入 VM
ssh -i oracle_key ubuntu@<VPS_IP>

# 上傳並執行一鍵安裝腳本
scp -i oracle_key scripts/oracle_vm_setup_failover.sh ubuntu@<VPS_IP>:/tmp/
ssh -i oracle_key ubuntu@<VPS_IP> "sudo bash /tmp/oracle_vm_setup_failover.sh"
```

## Step 3: 設定 rclone (Google Drive)

```bash
# 在 VPS 上
rclone config
# 選 "n" new remote
# 名稱: gdrive
# 類型: Google Drive
# 按照提示完成 OAuth（需要在本地瀏覽器開啟授權連結）

# 驗證
rclone lsd gdrive:Zhewei_Brain
```

## Step 4: 建立 Cloudflare Failover Tunnel

1. 登入 https://one.dash.cloudflare.com
2. Networks → Tunnels → Create a tunnel
3. 命名: `zhewei-failover`
4. 複製 tunnel token
5. 設定 Public Hostnames（與本地相同）:

| Hostname | Service |
|----------|---------|
| zhe-wei.net | http://gateway:80 |
| jarvis.zhe-wei.net | http://gateway:80 |
| cms.zhe-wei.net | http://gateway:80 |
| codesim.zhe-wei.net | http://gateway:80 |
| bridge.zhe-wei.net | http://gateway:80 |

**重要**: 在 Cloudflare DNS 設定中，每個域名需要有兩條 CNAME：
- 本地 tunnel（優先）
- failover tunnel（備援）

Cloudflare 會自動在本地 tunnel 斷線時切換到 failover tunnel。

## Step 5: 設定 .env

```bash
# 在 VPS 上建立 .env
cat > /opt/zhewei/zhe-wei-tech/.env << 'EOF'
# Cloudflare Failover Tunnel Token
CLOUDFLARE_FAILOVER_TOKEN=<paste-failover-tunnel-token>

# AI Keys (cloud only, no Ollama)
GEMINI_API_KEY=<your-key>
GROQ_API_KEY=<your-key>
DEEPSEEK_API_KEY=<your-key>
MINIMAX_API_KEY=<your-key>
MISTRAL_API_KEY=<your-key>

# Auth
JWT_SECRET=<same-as-local>

# Ntfy (optional, for failover notifications)
NTFY_TOPIC=zhewei_ops
EOF
```

或直接從本地同步：
```bash
# 在本地 Windows PowerShell
scp -i oracle_key D:\zhe-wei-tech\.env ubuntu@<VPS_IP>:/opt/zhewei/zhe-wei-tech/.env
```

## Step 6: 初始同步

```powershell
# 在本地 Windows 執行首次同步
powershell -File D:\zhe-wei-tech\scripts\sync_to_oracle.ps1
```

## Step 7: 設定本地定時同步

```powershell
# 建立 Windows 排程任務（每 30 分鐘同步一次）
schtasks /create /tn "ZheweiCloudSync" /tr "powershell -ExecutionPolicy Bypass -File D:\zhe-wei-tech\scripts\sync_to_oracle.ps1" /sc minute /mo 30 /ru SYSTEM
```

## Step 8: 測試

```bash
# 在 VPS 上手動測試 failover
sudo -u ubuntu /opt/zhewei/failover_health_check.sh

# 手動啟動 failover（測試用）
cd /opt/zhewei/zhe-wei-tech
docker compose -f docker-compose.failover.yml up -d

# 檢查容器狀態
docker ps

# 手動停止 failover
docker compose -f docker-compose.failover.yml down
```

---

## 運作機制

### 自動切換流程

```
每 2 分鐘 (cron):
  ├─ 檢查 https://zhe-wei.net/health
  ├─ 本地正常 → 什麼都不做（standby）
  ├─ 本地異常 → 累計失敗次數
  │   ├─ < 3 次 → 等待（可能只是暫時）
  │   └─ >= 3 次 → 啟動 failover！
  │       ├─ rclone 拉取最新程式碼
  │       ├─ docker compose up
  │       └─ 發送 ntfy 通知
  └─ 本地恢復 + failover 運行中 → 自動關閉 failover
```

### Cloudflare Tunnel Failover

Cloudflare 支援同一域名綁定多個 tunnel：
- **Primary**: 本地 tunnel（`zhewei_tunnel`）
- **Fallback**: Oracle tunnel（`zhewei-failover`）

當 primary tunnel 斷線，Cloudflare 自動將流量導向 fallback tunnel。
本地恢復後，流量自動切回 primary。

### 1GB RAM 限制下的取捨

| 功能 | Failover | 說明 |
|------|----------|------|
| Portal | ✅ | 完整功能 |
| Brain Server | ✅ | 僅雲端 AI（Gemini/MiniMax/Groq） |
| CMS | ✅ | 完整功能 |
| CodeSim | ✅ | 僅雲端 AI |
| Smart Bridge | ✅ | 僅雲端 AI |
| Ollama 本地模型 | ❌ | 需 2GB+ RAM |
| Dify | ❌ | 需 1GB+ RAM |
| Vision | ❌ | 需 GPU |
| ComfyUI | ❌ | 需 GPU |
| ChromaDB | ❌ | 記憶體不足 |

---

## 相關檔案

| 檔案 | 用途 |
|------|------|
| `docker-compose.failover.yml` | Oracle Cloud 輕量版 compose |
| `scripts/oracle_vm_setup_failover.sh` | VPS 一鍵安裝 |
| `scripts/sync_to_oracle.ps1` | 本地→雲端定時同步 |
| `scripts/failover_health_check.sh` | 健康檢查 + 自動切換 |
| `gateway/nginx.cloud.conf` | 雲端 nginx 配置 |

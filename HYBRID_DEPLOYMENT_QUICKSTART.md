# 混合部署快速啟動指南（方案 C）

## 🎯 5 分鐘快速部署

### 架構說明
- **雲端 VPS**：核心服務 24/7 運行（$12/月）
- **本地主機**：GPU 加速服務（需要時開機）
- **智慧路由**：自動偵測並使用最佳資源

---

## 📋 前置需求

### 雲端 VPS
- Linode/DigitalOcean 2GB RAM（$12/月）
- Ubuntu 22.04
- Docker 已安裝

### 本地主機（Windows）
- Ollama 運行在 port 11460
- Vision AI 運行在 port 8030（可選）
- ComfyUI 運行在 port 9188（可選）
- Cloudflare 帳號

---

## 🚀 部署步驟

### 步驟 1：雲端 VPS 部署（10 分鐘）

```bash
# SSH 連線
ssh ubuntu@YOUR_VPS_IP

# 安裝 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
exit && ssh ubuntu@YOUR_VPS_IP

# 部署專案
cd /opt
sudo mkdir zhewei && sudo chown $USER:$USER zhewei
cd zhewei
git clone YOUR_REPO .

# 設定環境變數
nano .env
# 加入 CLOUDFLARE_TOKEN, GEMINI_API_KEY 等

# 執行部署
chmod +x scripts/deploy_to_cloud.sh
./scripts/deploy_to_cloud.sh
```

### 步驟 2：本地 Tunnel 設定（5 分鐘）

```powershell
# 安裝 cloudflared
winget install Cloudflare.cloudflared

# 執行自動設定腳本
cd d:\zhe-wei-tech
.\scripts\setup_local_tunnel.ps1

# 登入 Cloudflare
cloudflared tunnel login

# 建立 Tunnel
cloudflared tunnel create zhewei-local-gpu

# 設定 DNS（在 Cloudflare Dashboard）
# ollama-gpu.zhe-wei.net → CNAME → YOUR_TUNNEL_ID.cfargotunnel.com
# vision-gpu.zhe-wei.net → CNAME → YOUR_TUNNEL_ID.cfargotunnel.com

# 安裝為 Windows 服務
cloudflared service install
Start-Service cloudflared
```

### 步驟 3：測試連接（2 分鐘）

```bash
# 測試混合部署
python scripts/test_hybrid_deployment.py
```

---

## ✅ 驗證清單

### 雲端服務
- [ ] https://jarvis.zhe-wei.net/health 可存取
- [ ] https://cms.zhe-wei.net/health 可存取
- [ ] https://codesim.zhe-wei.net 可存取

### 本地服務（本地開機時）
- [ ] https://ollama-gpu.zhe-wei.net/api/tags 可存取
- [ ] https://vision-gpu.zhe-wei.net/healthz 可存取

### 智慧路由
- [ ] 本地開機時使用 GPU 模型
- [ ] 本地關機時降級為 CPU 模型

---

## 🎛️ 運行模式

### 模式 1：本地開機（最佳性能）
- ⚡ GPU 加速推理
- 🎯 大模型可用（7B-14B）
- ✅ 視覺辨識、生圖可用
- 💰 成本：$12/月 + 電費

### 模式 2：本地關機（降級運行）
- 🔄 自動切換雲端 CPU
- 📦 輕量模型（2B-3B）
- ⚠️ 視覺辨識、生圖不可用
- 💰 成本：僅 $12/月

---

## 🔧 常用指令

### 雲端管理
```bash
# 查看服務狀態
docker compose -f docker-compose.cloud.yml ps

# 重啟服務
docker compose -f docker-compose.cloud.yml restart brain_server

# 查看日誌
docker compose -f docker-compose.cloud.yml logs -f
```

### 本地管理
```powershell
# 檢查 Tunnel 狀態
Get-Service cloudflared

# 重啟 Tunnel
Restart-Service cloudflared

# 測試本地服務
.\scripts\test_hybrid_deployment.py
```

---

## 📚 完整文件

- 詳細指南：`docs/deployment/HYBRID_DEPLOYMENT_GUIDE.md`
- 雲端部署：`docs/deployment/CLOUD_24_7_DEPLOYMENT.md`
- 快速部署：`QUICK_CLOUD_DEPLOY.md`

---

## ✨ 完成

您的系統現在採用混合部署架構：
- ✅ 雲端核心服務 24/7 運行
- ✅ 本地 GPU 服務按需使用
- ✅ 智慧路由自動切換
- ✅ 成本最優化（$12/月 + 彈性電費）

**外網存取：**
- 主入口：https://zhe-wei.net
- Jarvis AI：https://jarvis.zhe-wei.net
- 本地 GPU：https://ollama-gpu.zhe-wei.net（本地開機時）

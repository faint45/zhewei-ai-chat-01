# 築未科技 — 混合部署指南（方案 C）

## 🎯 架構概覽

**混合部署**：雲端 + 本地最佳組合

```
┌─────────────────────────────────────────────────────────┐
│                    雲端 VPS (24/7)                       │
│  ┌──────────┐  ┌────────┐  ┌─────┐  ┌────────┐         │
│  │ Ollama   │  │ Brain  │  │ CMS │  │CodeSim │         │
│  │ (CPU)    │  │ Server │  │     │  │        │         │
│  │ 輕量模型  │  │        │  │     │  │        │         │
│  └────┬─────┘  └───┬────┘  └──┬──┘  └───┬────┘         │
│       │            │           │         │              │
│       └────────────┴───────────┴─────────┘              │
│                    │                                     │
│            ┌───────▼────────┐                           │
│            │ Cloudflare     │                           │
│            │ Tunnel         │                           │
│            └───────┬────────┘                           │
└────────────────────┼──────────────────────────────────┘
                     │ Internet
                     │
┌────────────────────▼──────────────────────────────────┐
│              本地主機（需要時開機）                      │
│  ┌──────────┐  ┌────────┐  ┌─────────┐  ┌─────────┐  │
│  │ Ollama   │  │ Vision │  │ ComfyUI │  │  Dify   │  │
│  │ (GPU)    │  │   AI   │  │  生圖   │  │         │  │
│  │ 大模型    │  │ YOLOv8 │  │         │  │         │  │
│  └────┬─────┘  └───┬────┘  └────┬────┘  └────┬────┘  │
│       │            │             │            │        │
│       └────────────┴─────────────┴────────────┘        │
│                    │                                    │
│            ┌───────▼────────┐                          │
│            │ Cloudflare     │                          │
│            │ Tunnel (Local) │                          │
│            └────────────────┘                          │
└─────────────────────────────────────────────────────────┘
```

---

## 💡 方案優勢

### ✅ 優點
1. **成本最優**：雲端僅需 $12/月（2GB VPS）
2. **性能最佳**：本地 GPU 處理視覺與大模型
3. **穩定可靠**：核心服務 24/7 雲端運行
4. **彈性擴展**：本地關機時降級為雲端輕量模型

### 📊 服務分配

| 服務 | 位置 | 原因 | 開機需求 |
|------|------|------|----------|
| Brain Server | 雲端 | 核心服務，24/7 需求 | 必須 |
| Portal | 雲端 | 入口頁面，24/7 需求 | 必須 |
| CMS | 雲端 | 營建管理，24/7 需求 | 必須 |
| CodeSim | 雲端 | 代碼模擬，24/7 需求 | 必須 |
| Prediction | 雲端 | 預測系統，24/7 需求 | 必須 |
| Ollama (CPU) | 雲端 | 輕量模型備援 | 必須 |
| Ollama (GPU) | 本地 | 大模型推理 | 可選 |
| Vision AI | 本地 | YOLOv8 需 GPU | 可選 |
| ComfyUI | 本地 | 生圖需 GPU | 可選 |
| Dify | 本地 | AI 平台 | 可選 |

---

## 🚀 部署步驟

### 階段 1：雲端 VPS 部署

#### 1.1 建立 VPS（Linode 推薦）

```bash
# 規格建議
- CPU: 2 vCPU
- RAM: 2GB
- 儲存: 50GB SSD
- 流量: 2TB/月
- 成本: $12/月
```

#### 1.2 安裝 Docker

```bash
ssh ubuntu@YOUR_VPS_IP

# 安裝 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 登出再登入
exit
ssh ubuntu@YOUR_VPS_IP
```

#### 1.3 部署雲端服務

```bash
cd /opt
sudo mkdir zhewei && sudo chown $USER:$USER zhewei
cd zhewei

# Clone 專案
git clone YOUR_REPO .

# 設定環境變數
cat > .env << 'EOF'
# Cloudflare Tunnel Token
CLOUDFLARE_TOKEN=your_cloudflare_tunnel_token

# AI Provider Keys
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key

# Ollama 設定（雲端 CPU 版）
OLLAMA_BASE_URL=http://ollama:11434
AI_COST_MODE=smart_route

# 本地 GPU Ollama（透過 Tunnel）
OLLAMA_GPU_URL=https://ollama-gpu.zhe-wei.net
EOF

# 執行部署
chmod +x scripts/deploy_to_cloud.sh
./scripts/deploy_to_cloud.sh
```

---

### 階段 2：本地主機設定

#### 2.1 安裝 Cloudflare Tunnel（Windows）

```powershell
# 安裝 cloudflared
winget install Cloudflare.cloudflared

# 登入 Cloudflare
cloudflared tunnel login

# 建立 Tunnel（本地 GPU 服務）
cloudflared tunnel create zhewei-local-gpu

# 記下 Tunnel ID 和 Token
```

#### 2.2 設定本地服務 Tunnel

建立 `C:\Users\YOUR_USER\.cloudflared\config.yml`：

```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: C:\Users\YOUR_USER\.cloudflared\YOUR_TUNNEL_ID.json

ingress:
  # Ollama GPU
  - hostname: ollama-gpu.zhe-wei.net
    service: http://localhost:11460
  
  # Vision AI
  - hostname: vision-gpu.zhe-wei.net
    service: http://localhost:8030
  
  # ComfyUI
  - hostname: comfyui.zhe-wei.net
    service: http://localhost:9188
  
  # Dify
  - hostname: dify-local.zhe-wei.net
    service: http://localhost:8080
  
  # 404 fallback
  - service: http_status:404
```

#### 2.3 設定 DNS（Cloudflare Dashboard）

```
ollama-gpu.zhe-wei.net    → CNAME → YOUR_TUNNEL_ID.cfargotunnel.com
vision-gpu.zhe-wei.net    → CNAME → YOUR_TUNNEL_ID.cfargotunnel.com
comfyui.zhe-wei.net       → CNAME → YOUR_TUNNEL_ID.cfargotunnel.com
dify-local.zhe-wei.net    → CNAME → YOUR_TUNNEL_ID.cfargotunnel.com
```

#### 2.4 啟動本地 Tunnel（Windows 服務）

```powershell
# 安裝為 Windows 服務
cloudflared service install

# 啟動服務
Start-Service cloudflared

# 設定開機自動啟動
Set-Service -Name cloudflared -StartupType Automatic

# 檢查狀態
Get-Service cloudflared
cloudflared tunnel info zhewei-local-gpu
```

---

### 階段 3：智慧路由配置

#### 3.1 修改 Brain Server 配置

更新 `ai_service.py` 的 Ollama 路由邏輯：

```python
# 智慧 Ollama 路由
def get_ollama_url():
    """根據本地 GPU 可用性選擇 Ollama"""
    gpu_url = os.getenv("OLLAMA_GPU_URL", "https://ollama-gpu.zhe-wei.net")
    cpu_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    
    try:
        # 嘗試連接本地 GPU Ollama（5 秒超時）
        resp = requests.get(f"{gpu_url}/api/tags", timeout=5)
        if resp.status_code == 200:
            return gpu_url
    except:
        pass
    
    # Fallback 到雲端 CPU Ollama
    return cpu_url
```

#### 3.2 環境變數設定

雲端 VPS `.env`：

```env
# 主要 Ollama（雲端 CPU）
OLLAMA_BASE_URL=http://ollama:11434

# 備援 Ollama（本地 GPU，透過 Tunnel）
OLLAMA_GPU_URL=https://ollama-gpu.zhe-wei.net

# 智慧路由模式
AI_COST_MODE=smart_route
OLLAMA_FALLBACK_ENABLED=true
OLLAMA_GPU_TIMEOUT=5
```

---

## 🔄 智慧降級策略

### 場景 1：本地主機開機（最佳性能）

```
用戶請求 → Brain Server (雲端)
           ↓
    檢測本地 GPU Ollama
           ↓
    ✅ 可用 → 使用 ollama-gpu.zhe-wei.net (GPU 推理)
           ↓
    大模型任務 → qwen2.5-coder:7b, deepseek-r1:14b
    視覺任務 → vision-gpu.zhe-wei.net (YOLOv8)
    生圖任務 → comfyui.zhe-wei.net (Stable Diffusion)
```

### 場景 2：本地主機關機（降級運行）

```
用戶請求 → Brain Server (雲端)
           ↓
    檢測本地 GPU Ollama
           ↓
    ❌ 不可用 → 使用 ollama:11434 (雲端 CPU)
           ↓
    輕量模型 → gemma2:2b, qwen2.5:3b
    視覺任務 → 回傳「需要本地 GPU」
    生圖任務 → 回傳「需要本地 GPU」
```

---

## 📊 性能與成本對比

| 項目 | 本地開機 | 本地關機 |
|------|----------|----------|
| AI 推理速度 | ⚡ 快（GPU） | 🐢 慢（CPU） |
| 可用模型 | 🎯 全部（7B-14B） | 📦 輕量（2B-3B） |
| 視覺辨識 | ✅ YOLOv8 GPU | ❌ 不可用 |
| 圖片生成 | ✅ ComfyUI GPU | ❌ 不可用 |
| 月成本 | $12 + 電費 | $12 |
| 適用場景 | 工作時間 | 夜間/假日 |

---

## 🛠️ 維護與監控

### 自動健康檢查（雲端）

```bash
# 雲端 VPS
crontab -e

# 加入以下行
*/5 * * * * /opt/zhewei/scripts/health_monitor.sh >> /var/log/zhewei_health.log 2>&1
```

### 本地服務監控（Windows）

建立 `scripts/check_local_services.ps1`：

```powershell
# 檢查本地服務狀態
$services = @(
    @{Name="Ollama"; Port=11460},
    @{Name="Vision AI"; Port=8030},
    @{Name="ComfyUI"; Port=9188},
    @{Name="Dify"; Port=8080}
)

foreach ($svc in $services) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$($svc.Port)" -TimeoutSec 2 -ErrorAction Stop
        Write-Host "✅ $($svc.Name) 運行中"
    } catch {
        Write-Host "❌ $($svc.Name) 未運行"
    }
}

# 檢查 Cloudflare Tunnel
$tunnel = Get-Service cloudflared -ErrorAction SilentlyContinue
if ($tunnel.Status -eq "Running") {
    Write-Host "✅ Cloudflare Tunnel 運行中"
} else {
    Write-Host "❌ Cloudflare Tunnel 未運行"
}
```

設定 Windows 工作排程器每 10 分鐘執行。

---

## 🧪 測試混合連接

### 測試腳本

建立 `scripts/test_hybrid_deployment.py`：

```python
import requests
import time

def test_hybrid():
    """測試混合部署連接"""
    
    tests = [
        # 雲端服務
        ("Brain Server (雲端)", "https://jarvis.zhe-wei.net/health"),
        ("Portal (雲端)", "https://zhe-wei.net"),
        ("CMS (雲端)", "https://cms.zhe-wei.net/health"),
        
        # 本地 GPU 服務（透過 Tunnel）
        ("Ollama GPU (本地)", "https://ollama-gpu.zhe-wei.net/api/tags"),
        ("Vision AI (本地)", "https://vision-gpu.zhe-wei.net/healthz"),
        ("ComfyUI (本地)", "https://comfyui.zhe-wei.net"),
    ]
    
    print("🧪 測試混合部署連接...\n")
    
    for name, url in tests:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                print(f"✅ {name}")
            else:
                print(f"⚠️ {name} (HTTP {resp.status_code})")
        except requests.exceptions.Timeout:
            print(f"⏱️ {name} (超時，可能本地關機)")
        except Exception as e:
            print(f"❌ {name} ({str(e)[:50]})")
    
    print("\n測試完成！")

if __name__ == "__main__":
    test_hybrid()
```

執行測試：

```bash
# 雲端 VPS
python scripts/test_hybrid_deployment.py

# 本地 Windows
python scripts\test_hybrid_deployment.py
```

---

## 📋 部署檢查清單

### 雲端 VPS ✅
- [ ] VPS 已建立並安裝 Docker
- [ ] 專案已上傳到 `/opt/zhewei`
- [ ] `.env` 已設定（CLOUDFLARE_TOKEN, API Keys）
- [ ] 執行 `deploy_to_cloud.sh` 成功
- [ ] 所有容器運行中（`docker ps`）
- [ ] 外網可存取 https://jarvis.zhe-wei.net
- [ ] 健康監控已加入 crontab

### 本地主機 ✅
- [ ] Cloudflare Tunnel 已安裝
- [ ] `config.yml` 已設定 4 個服務
- [ ] DNS 已設定 CNAME 記錄
- [ ] Tunnel 已安裝為 Windows 服務
- [ ] Ollama 運行在 port 11460
- [ ] Vision AI 運行在 port 8030
- [ ] ComfyUI 運行在 port 9188
- [ ] 外網可存取 https://ollama-gpu.zhe-wei.net

### 智慧路由 ✅
- [ ] Brain Server 可偵測本地 GPU
- [ ] 本地開機時使用 GPU 模型
- [ ] 本地關機時降級為 CPU 模型
- [ ] 測試腳本全部通過

---

## 🎯 完成後效果

### 本地主機開機時
- ⚡ **最佳性能**：GPU 加速推理
- 🎯 **完整功能**：所有服務可用
- 💰 **成本**：$12/月 + 電費

### 本地主機關機時
- 🔄 **自動降級**：切換到雲端 CPU
- ✅ **核心可用**：對話、管理系統正常
- ⚠️ **功能受限**：視覺辨識、生圖不可用
- 💰 **成本**：僅 $12/月

---

## 🆘 故障排除

### 本地 GPU 服務無法連接

```bash
# 檢查 Tunnel 狀態
Get-Service cloudflared

# 重啟 Tunnel
Restart-Service cloudflared

# 檢查 Tunnel 日誌
cloudflared tunnel info zhewei-local-gpu
```

### Brain Server 無法切換到本地 GPU

```bash
# 檢查環境變數
docker exec zhewei_brain env | grep OLLAMA

# 檢查日誌
docker logs zhewei_brain | grep -i ollama

# 手動測試連接
docker exec zhewei_brain curl https://ollama-gpu.zhe-wei.net/api/tags
```

---

## 📚 相關文件

- 雲端完整部署：`docs/deployment/CLOUD_24_7_DEPLOYMENT.md`
- 快速部署指南：`QUICK_CLOUD_DEPLOY.md`
- Docker Compose：`docker-compose.cloud.yml`

---

## ✨ 總結

混合部署方案結合了雲端的穩定性與本地的性能優勢：

- **雲端**：24/7 核心服務，成本僅 $12/月
- **本地**：GPU 加速，需要時開機
- **智慧路由**：自動偵測並切換最佳資源
- **彈性擴展**：隨時可升級雲端 GPU

這是最經濟實惠且性能最佳的部署方案！

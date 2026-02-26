# 混合部署成本分析與實施計劃

## 💰 成本詳細分析

### 方案對比：純雲端 vs 混合部署

| 項目 | 純雲端 GPU | 混合部署 | 節省 |
|------|-----------|---------|------|
| **雲端伺服器** | ¥4,000/月 | ¥90-108/月 | ¥3,892-3,910/月 |
| **本地電費** | - | ¥30/月 | - |
| **總成本** | ¥4,000/月 | ¥120-138/月 | ¥3,862-3,880/月 |
| **年度成本** | ¥48,000/年 | ¥1,440-1,656/年 | ¥46,344-46,560/年 |
| **節省比例** | - | - | **97%** |

---

## 🎯 混合部署方案詳解

### 架構組成

```
┌─────────────────────────────────────────────────────────────┐
│                    Internet (Cloudflare)                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
┌─────────────────┐         ┌─────────────────┐
│  雲端 VPS       │         │  本地主機        │
│  (24/7 運行)    │         │  (需要時開機)    │
├─────────────────┤         ├─────────────────┤
│ Brain Server    │         │ Ollama GPU      │
│ Portal          │◄────────┤ Vision AI       │
│ CMS             │ Tunnel  │ ComfyUI         │
│ CodeSim         │         │ Dify            │
│ Prediction      │         │ 其他 GPU 服務    │
│ Ollama CPU      │         └─────────────────┘
│ Gateway         │         本地 RTX 4060/4070
└─────────────────┘         工作時間開機
騰訊雲/阿里雲              電費約 ¥30/月
¥90-108/月
```

### 雲端部分（¥90-108/月）

**選項 A：騰訊雲（推薦）**
- **配置**：2核4GB 輕量應用伺服器
- **價格**：¥90/月（年付 ¥75/月）
- **學生價**：¥10/月（首年）
- **包含**：
  - 3 Mbps 固定帶寬
  - 2 TB/月 流量
  - 50GB SSD 儲存
- **優勢**：
  - 微信/QQ 生態整合
  - 混元大模型 API
  - 代金券優惠多
  - 中國訪問速度極快

**選項 B：阿里雲**
- **配置**：2核4GB 輕量應用伺服器
- **價格**：¥108/月（年付 ¥90/月）
- **學生價**：¥9.5/月（首年）
- **包含**：
  - 3 Mbps 固定帶寬
  - 1 TB/月 流量
  - 40GB SSD 儲存
- **優勢**：
  - 淘寶/釘釘生態整合
  - 通義千問 API
  - 文件最完善
  - 企業級服務

### 本地部分（¥30/月電費）

**硬體需求：**
- **GPU**：RTX 4060（8GB）或以上
- **CPU**：i5-12400 或以上
- **RAM**：16GB 或以上
- **儲存**：500GB SSD

**電費計算：**
```
假設配置：RTX 4060 + i5-12400
- 滿載功耗：約 300W
- 工作時間：每天 8 小時
- 每月用電：300W × 8h × 30天 = 72 kWh
- 電費單價：¥0.6/kWh（台灣約 NT$3/kWh）
- 月電費：72 × 0.6 = ¥43

實際使用（非滿載）：
- 平均功耗：約 150W
- 月電費：約 ¥20-30
```

**運行服務：**
- Ollama GPU（port 11460）
- Vision AI（port 8030，可選）
- ComfyUI（port 9188，可選）
- Dify（port 3000，可選）

---

## 📊 詳細成本拆解

### 月度成本（騰訊雲方案）

| 項目 | 成本 | 說明 |
|------|------|------|
| 騰訊雲 VPS | ¥90 | 2核4GB，3Mbps，2TB流量 |
| 本地電費 | ¥30 | 每天 8 小時，平均 150W |
| Cloudflare Tunnel | ¥0 | 免費 |
| 域名費用 | ¥5 | 年付 ¥60，分攤到月 |
| **總計** | **¥125** | 實際月度成本 |

### 月度成本（阿里雲方案）

| 項目 | 成本 | 說明 |
|------|------|------|
| 阿里雲 VPS | ¥108 | 2核4GB，3Mbps，1TB流量 |
| 本地電費 | ¥30 | 每天 8 小時，平均 150W |
| Cloudflare Tunnel | ¥0 | 免費 |
| 域名費用 | ¥5 | 年付 ¥60，分攤到月 |
| **總計** | **¥143** | 實際月度成本 |

### 年度成本對比

| 方案 | 月成本 | 年成本 | 3年成本 |
|------|--------|--------|---------|
| **純雲端 GPU** | ¥4,000 | ¥48,000 | ¥144,000 |
| **混合部署（騰訊雲）** | ¥125 | ¥1,500 | ¥4,500 |
| **混合部署（阿里雲）** | ¥143 | ¥1,716 | ¥5,148 |
| **節省（騰訊雲）** | ¥3,875 | ¥46,500 | ¥139,500 |
| **節省（阿里雲）** | ¥3,857 | ¥46,284 | ¥138,852 |

### 學生方案（超值）

| 方案 | 月成本 | 年成本 | 節省 |
|------|--------|--------|------|
| **騰訊雲學生** | ¥10 + ¥30 = ¥40 | ¥480 | 99% |
| **阿里雲學生** | ¥9.5 + ¥30 = ¥39.5 | ¥474 | 99% |

---

## 💡 ROI 分析

### 投資回報

**初始投資：**
- 本地硬體（已有）：¥0
- 雲端 VPS（首月）：¥90-108
- 域名（年付）：¥60
- **總計**：¥150-168

**每月節省：**
- 對比純雲端 GPU：¥3,875-3,857
- **回本時間**：立即回本（第一個月就節省 ¥3,700+）

**年度 ROI：**
```
投資：¥150-168
節省：¥46,284-46,500
ROI = (節省 - 投資) / 投資 × 100%
    = (¥46,500 - ¥168) / ¥168 × 100%
    = 27,571%
```

### 3 年總擁有成本（TCO）

| 方案 | 初始投資 | 3年運營成本 | 總成本 |
|------|---------|------------|--------|
| **純雲端 GPU** | ¥0 | ¥144,000 | ¥144,000 |
| **混合部署** | ¥168 | ¥4,500 | ¥4,668 |
| **節省** | - | - | **¥139,332（97%）** |

---

## 🚀 實施計劃

### 階段 1：雲端 VPS 部署（第 1 天）

**時間：2-3 小時**

```bash
# 1. 建立 VPS（10 分鐘）
# 登入騰訊雲/阿里雲控制台
# 選擇 2核4GB 輕量應用伺服器
# 選擇 Ubuntu 22.04
# 配置安全組（22, 80, 443）

# 2. SSH 連接並初始化（20 分鐘）
ssh ubuntu@YOUR_VPS_IP
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
exit && ssh ubuntu@YOUR_VPS_IP

# 3. 部署專案（30 分鐘）
cd /opt && sudo mkdir zhewei && sudo chown $USER:$USER zhewei
cd zhewei && git clone YOUR_REPO .
cp env.hybrid.example .env
vim .env  # 填入配置

# 4. 執行部署（40 分鐘）
chmod +x scripts/deploy_to_cloud.sh
./scripts/deploy_to_cloud.sh

# 5. 驗證服務（10 分鐘）
docker compose -f docker-compose.cloud.yml ps
curl http://localhost:8000/health
```

**預期結果：**
- ✅ 所有容器運行中
- ✅ Brain Server 可訪問
- ✅ Ollama CPU 可用

### 階段 2：本地 Tunnel 設定（第 1 天）

**時間：30 分鐘**

```powershell
# 1. 安裝 Cloudflare Tunnel（5 分鐘）
winget install Cloudflare.cloudflared

# 2. 執行自動設定（10 分鐘）
cd d:\zhe-wei-tech
.\scripts\setup_local_tunnel.ps1

# 3. 登入並建立 Tunnel（5 分鐘）
cloudflared tunnel login
cloudflared tunnel create zhewei-local-gpu

# 4. 配置 DNS（5 分鐘）
# 在 Cloudflare Dashboard 添加 CNAME 記錄
# ollama-gpu.zhe-wei.net → YOUR_TUNNEL_ID.cfargotunnel.com

# 5. 安裝為服務（5 分鐘）
cloudflared service install
Start-Service cloudflared
Set-Service -Name cloudflared -StartupType Automatic
```

**預期結果：**
- ✅ Tunnel 運行中
- ✅ 本地 Ollama 可透過外網訪問
- ✅ 開機自動啟動

### 階段 3：智慧路由整合（第 2 天）

**時間：30 分鐘**

```bash
# 在雲端 VPS 執行
cd /opt/zhewei

# 1. 整合智慧路由（10 分鐘）
python scripts/integrate_smart_router.py

# 2. 更新環境變數（5 分鐘）
vim .env
# 確認 OLLAMA_GPU_URL=https://ollama-gpu.zhe-wei.net

# 3. 重啟服務（5 分鐘）
docker compose -f docker-compose.cloud.yml restart brain_server

# 4. 測試路由（10 分鐘）
python scripts/test_smart_router.py
```

**預期結果：**
- ✅ 路由器自動偵測 GPU
- ✅ 本地開機時使用 GPU
- ✅ 本地關機時降級 CPU

### 階段 4：測試與驗證（第 2 天）

**時間：1 小時**

```bash
# 1. 測試混合部署（20 分鐘）
python scripts/test_hybrid_deployment.py

# 2. 測試 GPU 模式（20 分鐘）
# 確保本地電腦開機
curl https://jarvis.zhe-wei.net/api/ollama/router/status
# 應顯示 GPU 模式

# 3. 測試 CPU 降級（20 分鐘）
# 關閉本地電腦
sleep 120  # 等待快取過期
curl https://jarvis.zhe-wei.net/api/ollama/router/status
# 應顯示 CPU 模式

# 4. 開啟監控儀表板
# https://jarvis.zhe-wei.net/static/hybrid-dashboard.html
```

**預期結果：**
- ✅ 所有測試通過
- ✅ GPU/CPU 自動切換
- ✅ 監控儀表板正常

---

## 📈 性能對比

### AI 推理速度

| 任務 | 純 CPU | 雲端 GPU | 本地 GPU | 提升 |
|------|--------|---------|---------|------|
| **文字生成（7B）** | 5 tokens/s | 40 tokens/s | 60 tokens/s | 12x |
| **代碼生成（7B）** | 4 tokens/s | 35 tokens/s | 55 tokens/s | 13x |
| **視覺辨識** | ❌ 不支援 | 2s/張 | 0.5s/張 | 4x |
| **圖片生成** | ❌ 不支援 | 30s/張 | 8s/張 | 4x |

### 用戶體驗

| 場景 | 純 CPU | 雲端 GPU | 本地 GPU |
|------|--------|---------|---------|
| **工作時間（本地開機）** | 🐢 慢 | ⚡ 快 | ⚡⚡ 極快 |
| **夜間/假日（本地關機）** | 🐢 慢 | ⚡ 快 | 🔄 自動降級 CPU |
| **成本** | ¥0 | ¥4,000/月 | ¥125/月 |

---

## 🎯 使用場景分析

### 場景 1：AI 聊天機器人

**需求：**
- 24/7 在線回應
- 支援多輪對話
- 需要代碼生成能力

**混合部署方案：**
- **工作時間**：本地 GPU（qwen2.5-coder:7b）
  - 速度：55 tokens/s
  - 成本：電費
- **夜間/假日**：雲端 CPU（qwen2.5:3b）
  - 速度：15 tokens/s
  - 成本：已包含在 VPS 費用

**效果：**
- ✅ 24/7 不間斷服務
- ✅ 工作時間性能最佳
- ✅ 夜間自動降級但仍可用
- ✅ 月成本僅 ¥125

### 場景 2：圖片生成服務

**需求：**
- 按需生成圖片
- 需要 Stable Diffusion
- 不需要 24/7

**混合部署方案：**
- **本地開機時**：ComfyUI GPU
  - 速度：8 秒/張（512×512）
  - 品質：高
- **本地關機時**：服務不可用
  - 提示用戶稍後再試

**效果：**
- ✅ 工作時間提供服務
- ✅ 性能極佳
- ✅ 成本極低（¥125/月）
- ⚠️ 夜間不可用（可接受）

### 場景 3：視覺辨識

**需求：**
- 工地照片分析
- 需要 YOLOv8
- 工作時間使用

**混合部署方案：**
- **本地開機時**：Vision AI GPU
  - 速度：0.5 秒/張
  - 準確率：高
- **本地關機時**：服務不可用

**效果：**
- ✅ 工作時間高效運行
- ✅ 成本極低
- ⚠️ 夜間不可用（符合使用場景）

---

## 💰 成本優化建議

### 1. 使用年付（節省 15-20%）

**騰訊雲：**
- 月付：¥90/月 × 12 = ¥1,080/年
- 年付：¥900/年（¥75/月）
- **節省：¥180/年**

**阿里雲：**
- 月付：¥108/月 × 12 = ¥1,296/年
- 年付：¥1,080/年（¥90/月）
- **節省：¥216/年**

### 2. 學生認證（節省 88%）

**騰訊雲學生：**
- 原價：¥90/月
- 學生價：¥10/月（首年）
- **節省：¥80/月 = ¥960/年**

**阿里雲學生：**
- 原價：¥108/月
- 學生價：¥9.5/月（首年）
- **節省：¥98.5/月 = ¥1,182/年**

### 3. 優化本地電費

**策略：**
- 使用省電模式（降低 GPU 功耗）
- 下班自動關機（節省 16 小時/天）
- 週末不使用時關機

**效果：**
```
原本：每天 8 小時 = ¥30/月
優化：每天 6 小時 = ¥22/月
節省：¥8/月 = ¥96/年
```

### 4. 使用代金券

**騰訊雲：**
- 新用戶代金券：最高 ¥5,000
- 可抵扣首年費用

**阿里雲：**
- 新用戶代金券：最高 ¥2,000
- 可抵扣首年費用

---

## 📋 部署檢查清單

### 雲端 VPS ✅

- [ ] VPS 已建立（騰訊雲/阿里雲）
- [ ] Docker 已安裝
- [ ] 專案已上傳到 `/opt/zhewei`
- [ ] `.env` 已設定（API Keys、Cloudflare Token）
- [ ] 執行 `deploy_to_cloud.sh` 成功
- [ ] 所有容器運行中（`docker ps`）
- [ ] Brain Server 可訪問（`curl http://localhost:8000/health`）
- [ ] 外網可訪問（https://jarvis.zhe-wei.net）
- [ ] 健康監控已加入 crontab

### 本地主機 ✅

- [ ] Cloudflare Tunnel 已安裝
- [ ] `config.yml` 已設定
- [ ] DNS CNAME 記錄已設定
- [ ] Tunnel 已安裝為 Windows 服務
- [ ] Ollama 運行在 port 11460
- [ ] Vision AI 運行在 port 8030（可選）
- [ ] ComfyUI 運行在 port 9188（可選）
- [ ] 外網可訪問（https://ollama-gpu.zhe-wei.net）
- [ ] 開機自動啟動

### 智慧路由 ✅

- [ ] `smart_ollama_router.py` 已建立
- [ ] 執行 `integrate_smart_router.py` 成功
- [ ] Brain Server 已重啟
- [ ] 路由器 API 可訪問（`/api/ollama/router/status`）
- [ ] 監控儀表板可開啟
- [ ] 測試腳本全部通過
- [ ] GPU/CPU 自動切換正常

---

## 🎉 預期效果

### 成本節省

- **月度節省**：¥3,875（對比純雲端 GPU）
- **年度節省**：¥46,500
- **3 年節省**：¥139,500
- **節省比例**：97%

### 性能提升

- **AI 推理速度**：提升 12-13 倍（對比純 CPU）
- **視覺辨識**：0.5 秒/張（對比雲端 GPU 的 2 秒）
- **圖片生成**：8 秒/張（對比雲端 GPU 的 30 秒）

### 穩定性

- **雲端服務**：24/7 不間斷
- **本地 GPU**：工作時間可用
- **自動降級**：本地不可用時自動切換 CPU
- **監控告警**：即時掌握系統狀態

### 用戶體驗

- **工作時間**：極快（本地 GPU）
- **夜間/假日**：可用（雲端 CPU）
- **無感切換**：自動選擇最佳資源
- **成本可控**：月成本僅 ¥125

---

## 📞 技術支援

### 常用指令

**雲端管理：**
```bash
# 查看服務狀態
docker compose -f docker-compose.cloud.yml ps

# 查看日誌
docker compose -f docker-compose.cloud.yml logs -f brain_server

# 重啟服務
docker compose -f docker-compose.cloud.yml restart brain_server

# 更新部署
cd /opt/zhewei && git pull
docker compose -f docker-compose.cloud.yml up -d --build
```

**本地管理：**
```powershell
# 檢查 Tunnel
Get-Service cloudflared

# 重啟 Tunnel
Restart-Service cloudflared

# 測試路由器
python scripts\test_smart_router.py
```

### 監控儀表板

**URL：** https://jarvis.zhe-wei.net/static/hybrid-dashboard.html

**功能：**
- 📊 GPU/CPU Ollama 即時狀態
- 📈 請求次數統計
- 🎯 當前運行模式
- 💡 推薦模型顯示
- 🔄 一鍵刷新路由器

---

## ✨ 總結

混合部署方案是最佳選擇，因為：

### ✅ 成本最優
- 月成本：¥120-138
- 對比純雲端 GPU：節省 97%
- 對比純本地：增加 24/7 穩定性

### ✅ 性能最佳
- 工作時間：本地 GPU 極速
- 夜間/假日：雲端 CPU 可用
- 自動切換：無感體驗

### ✅ 穩定可靠
- 雲端 24/7 運行
- 本地按需使用
- 自動降級機制

### ✅ 彈性擴展
- 隨時可升級雲端配置
- 隨時可添加本地服務
- 成本可控可預測

**立即開始部署，享受 97% 成本節省！** 🚀

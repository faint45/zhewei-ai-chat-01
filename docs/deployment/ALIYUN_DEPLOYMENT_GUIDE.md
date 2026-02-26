# 築未科技 — 阿里雲部署指南

## 🎯 阿里雲優勢

### 為什麼選擇阿里雲？

**✅ 適合中國用戶：**
- 🚀 中國大陸訪問速度快
- 💳 支援支付寶、微信支付
- 📱 中文介面與客服
- 🔧 豐富的中國生態整合

**✅ 價格優勢：**
- 💰 新用戶免費試用
- 🎁 學生優惠方案
- 📊 按量付費靈活

**✅ 產品豐富：**
- ☁️ ECS 雲伺服器
- 🗄️ OSS 物件儲存
- 🌐 CDN 加速
- 🔐 完整安全防護

---

## 💰 阿里雲方案對比

### 方案 A：輕量應用伺服器（推薦新手）

| 規格 | 配置 | 價格 | 適用場景 |
|------|------|------|----------|
| 入門版 | 2核2GB | ¥60/月 | 測試環境 |
| 基礎版 | 2核4GB | ¥108/月 | 小型生產 |
| 標準版 | 4核8GB | ¥288/月 | 中型生產 |

**特點：**
- ✅ 開箱即用，預裝環境
- ✅ 固定帶寬（3-5 Mbps）
- ✅ 包含流量包（1-3 TB/月）
- ✅ 簡單易用，適合新手

### 方案 B：ECS 雲伺服器（推薦進階）

| 規格 | 配置 | 價格 | 適用場景 |
|------|------|------|----------|
| 共享型 | 2核4GB | ¥80/月 | 開發測試 |
| 計算型 | 2核8GB | ¥180/月 | 標準生產 |
| 通用型 | 4核16GB | ¥450/月 | 大型生產 |

**特點：**
- ✅ 彈性配置，可隨時升級
- ✅ 按量付費或包年包月
- ✅ 支援 GPU 實例
- ✅ 更多進階功能

### 方案 C：混合部署（最推薦）

**架構：**
- 阿里雲 ECS：核心服務（¥108/月）
- 本地主機：GPU 服務（電費）
- **總成本：¥108-150/月**

---

## 🚀 阿里雲快速部署

### 步驟 1：建立 ECS 實例（10 分鐘）

#### 1.1 登入阿里雲控制台

```
https://ecs.console.aliyun.com
```

#### 1.2 建立實例

**基本配置：**
- **地域**：選擇離您最近的區域（如：華東2-上海）
- **實例規格**：ecs.t6-c1m2.large（2核4GB）
- **鏡像**：Ubuntu 22.04 64位
- **儲存**：40GB 高效雲盤
- **網路**：專有網路（VPC）

**網路與安全：**
- **公網 IP**：分配
- **帶寬**：按使用流量計費（建議 5 Mbps）
- **安全組**：允許 22（SSH）、80（HTTP）、443（HTTPS）

**系統配置：**
- **登入憑證**：密鑰對（推薦）或密碼
- **實例名稱**：zhewei-brain-server

#### 1.3 配置安全組規則

```
入方向規則：
- SSH (22)：允許 0.0.0.0/0
- HTTP (80)：允許 0.0.0.0/0
- HTTPS (443)：允許 0.0.0.0/0
- 自定義 TCP (8000-8030)：允許 0.0.0.0/0（可選，用於調試）
```

---

### 步驟 2：連接並初始化（5 分鐘）

#### 2.1 SSH 連接

```bash
# 使用密鑰對
ssh -i ~/.ssh/aliyun_key.pem root@YOUR_ECS_IP

# 或使用密碼
ssh root@YOUR_ECS_IP
```

#### 2.2 系統更新

```bash
# 更新系統
apt update && apt upgrade -y

# 安裝基礎工具
apt install -y curl wget git vim htop
```

#### 2.3 安裝 Docker

```bash
# 使用阿里雲 Docker 鏡像源（速度更快）
curl -fsSL https://get.docker.com | sh

# 配置阿里雲 Docker 鏡像加速器
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn",
    "https://registry.docker-cn.com"
  ]
}
EOF

# 重啟 Docker
systemctl daemon-reload
systemctl restart docker
systemctl enable docker

# 驗證安裝
docker --version
```

---

### 步驟 3：部署專案（10 分鐘）

#### 3.1 上傳專案

**方法 1：Git Clone（推薦）**

```bash
cd /opt
git clone YOUR_REPO zhewei
cd zhewei
```

**方法 2：使用阿里雲 OSS（適合大型專案）**

```bash
# 安裝 ossutil
wget http://gosspublic.alicdn.com/ossutil/1.7.15/ossutil64
chmod 755 ossutil64
mv ossutil64 /usr/local/bin/ossutil

# 配置 OSS
ossutil config

# 下載專案
cd /opt
ossutil cp -r oss://your-bucket/zhewei ./
```

#### 3.2 設定環境變數

```bash
cd /opt/zhewei
cp env.hybrid.example .env
vim .env
```

**阿里雲專屬配置：**

```env
# Cloudflare Tunnel（必要）
CLOUDFLARE_TOKEN=your_cloudflare_tunnel_token

# Ollama 配置
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_GPU_URL=https://ollama-gpu.zhe-wei.net

# 阿里雲通義千問 API（可選）
DASHSCOPE_API_KEY=your_dashscope_api_key
QWEN_MODEL=qwen-max

# AI Provider Keys
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key

# 阿里雲 OSS（可選，用於檔案儲存）
ALIYUN_OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com
ALIYUN_OSS_BUCKET=zhewei-storage
ALIYUN_OSS_ACCESS_KEY_ID=your_access_key_id
ALIYUN_OSS_ACCESS_KEY_SECRET=your_access_key_secret

# 工作目錄
WORK_DIR=/opt/zhewei
BRAIN_WORKSPACE=/app/brain_workspace
ZHEWEI_MEMORY_ROOT=/memory
```

#### 3.3 執行部署

```bash
chmod +x scripts/deploy_to_cloud.sh
./scripts/deploy_to_cloud.sh
```

---

### 步驟 4：配置域名（5 分鐘）

#### 4.1 在阿里雲 DNS 設定

**選項 A：使用 Cloudflare Tunnel（推薦）**

```bash
# 已在 deploy_to_cloud.sh 中自動配置
# 域名會自動透過 Cloudflare Tunnel 暴露
```

**選項 B：直接使用阿里雲 DNS**

```
登入阿里雲 DNS 控制台：
https://dns.console.aliyun.com

添加記錄：
- jarvis.zhe-wei.net → A → YOUR_ECS_IP
- cms.zhe-wei.net → A → YOUR_ECS_IP
- codesim.zhe-wei.net → A → YOUR_ECS_IP
```

#### 4.2 配置 SSL 證書（使用阿里雲免費證書）

```bash
# 安裝 acme.sh
curl https://get.acme.sh | sh
source ~/.bashrc

# 申請證書（使用阿里雲 DNS API）
export Ali_Key="your_aliyun_access_key"
export Ali_Secret="your_aliyun_secret_key"

acme.sh --issue --dns dns_ali \
  -d zhe-wei.net \
  -d *.zhe-wei.net

# 安裝證書
acme.sh --install-cert -d zhe-wei.net \
  --key-file /opt/zhewei/ssl/key.pem \
  --fullchain-file /opt/zhewei/ssl/cert.pem \
  --reloadcmd "docker compose -f /opt/zhewei/docker-compose.cloud.yml restart gateway"
```

---

### 步驟 5：優化配置（可選）

#### 5.1 啟用 Swap（記憶體不足時）

```bash
# 建立 2GB Swap
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# 永久啟用
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

#### 5.2 配置阿里雲 CDN（加速靜態資源）

```bash
# 在阿里雲 CDN 控制台配置
# 源站：YOUR_ECS_IP
# 加速域名：static.zhe-wei.net
# 快取規則：
#   - *.js, *.css, *.png, *.jpg → 快取 7 天
#   - *.html → 快取 1 小時
```

#### 5.3 配置阿里雲 SLB（負載均衡，可選）

```bash
# 適用於高流量場景
# 在阿里雲 SLB 控制台配置
# 後端伺服器：YOUR_ECS_IP:80
# 健康檢查：HTTP /health
```

---

## 🔧 阿里雲專屬功能整合

### 1. 通義千問 API 整合

建立 `qwen_client.py`（已存在，需更新配置）：

```python
import os
from http import HTTPStatus
import dashscope

dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

def call_qwen(messages):
    """呼叫通義千問 API"""
    response = dashscope.Generation.call(
        model='qwen-max',
        messages=messages,
        result_format='message',
    )
    
    if response.status_code == HTTPStatus.OK:
        return response.output.choices[0].message.content
    else:
        return f"錯誤: {response.message}"
```

### 2. 阿里雲 OSS 檔案儲存

建立 `aliyun_oss_client.py`：

```python
import oss2
import os

auth = oss2.Auth(
    os.getenv('ALIYUN_OSS_ACCESS_KEY_ID'),
    os.getenv('ALIYUN_OSS_ACCESS_KEY_SECRET')
)

bucket = oss2.Bucket(
    auth,
    os.getenv('ALIYUN_OSS_ENDPOINT'),
    os.getenv('ALIYUN_OSS_BUCKET')
)

def upload_file(local_path, oss_path):
    """上傳檔案到 OSS"""
    bucket.put_object_from_file(oss_path, local_path)
    return f"https://{bucket.bucket_name}.{bucket.endpoint}/{oss_path}"

def download_file(oss_path, local_path):
    """從 OSS 下載檔案"""
    bucket.get_object_to_file(oss_path, local_path)
```

### 3. 阿里雲日誌服務（SLS）

```python
from aliyun.log import LogClient

client = LogClient(
    os.getenv('ALIYUN_SLS_ENDPOINT'),
    os.getenv('ALIYUN_SLS_ACCESS_KEY_ID'),
    os.getenv('ALIYUN_SLS_ACCESS_KEY_SECRET')
)

def log_to_sls(project, logstore, logs):
    """寫入日誌到 SLS"""
    client.put_logs(
        project=project,
        logstore=logstore,
        logs=logs
    )
```

---

## 📊 阿里雲 vs 其他雲端對比

| 項目 | 阿里雲 | Oracle Cloud | Linode | Vultr |
|------|--------|--------------|--------|-------|
| **價格** | ¥108/月 | 免費 | $12/月 | $12/月 |
| **中國速度** | ⚡ 極快 | 🐢 慢 | 🚶 中等 | 🚶 中等 |
| **支付方式** | 支付寶/微信 | 信用卡 | 信用卡 | 信用卡 |
| **中文支援** | ✅ 完整 | ❌ 無 | ❌ 無 | ❌ 無 |
| **生態整合** | ✅ 豐富 | ❌ 少 | ❌ 少 | ❌ 少 |
| **GPU 實例** | ✅ 有 | ❌ 無 | ❌ 無 | ✅ 有 |
| **免費額度** | 試用 | 永久免費 | ❌ 無 | ❌ 無 |

### 推薦選擇

**選擇阿里雲如果：**
- ✅ 主要用戶在中國大陸
- ✅ 需要中文客服支援
- ✅ 想整合阿里雲生態（OSS、CDN、SLS）
- ✅ 需要通義千問 API

**選擇 Oracle Cloud 如果：**
- ✅ 預算極度有限（完全免費）
- ✅ 用戶主要在海外
- ✅ 只需基礎功能

**選擇 Linode/Vultr 如果：**
- ✅ 需要穩定的國際訪問
- ✅ 預算適中（$12/月）
- ✅ 需要簡單易用的介面

---

## 💰 阿里雲成本優化

### 1. 使用包年包月（節省 15-20%）

```
2核4GB 輕量應用伺服器：
- 按月：¥108/月
- 包年：¥1,080/年（相當於 ¥90/月，節省 ¥216）
```

### 2. 使用預留實例券（節省 30-50%）

```
ECS 預留實例券：
- 1 年期：節省 30%
- 3 年期：節省 50%
```

### 3. 使用阿里雲學生優惠

```
學生認證後：
- 輕量應用伺服器：¥9.5/月（首年）
- ECS 共享型：¥10/月（首年）
```

### 4. 使用按量付費（開發測試環境）

```
開發環境按需開關機：
- 運行時：¥0.15/小時
- 停機時：僅收取儲存費用（¥0.35/GB/月）
- 每天工作 8 小時：約 ¥36/月
```

---

## 🔧 阿里雲監控與維護

### 1. 雲監控（免費）

```bash
# 在阿里雲控制台啟用雲監控
# 自動監控：
# - CPU 使用率
# - 記憶體使用率
# - 磁碟使用率
# - 網路流量

# 設定告警規則：
# CPU > 80% 持續 5 分鐘 → 發送簡訊/郵件
```

### 2. 日誌服務（SLS）

```bash
# 安裝 Logtail
wget http://logtail-release-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/linux64/logtail.sh
sh logtail.sh install cn-shanghai

# 配置日誌收集
# Docker 容器日誌自動收集到 SLS
```

### 3. 自動快照備份

```bash
# 在阿里雲控制台設定自動快照策略
# 建議配置：
# - 每天凌晨 2:00 自動快照
# - 保留最近 7 天
# - 快照費用：¥0.12/GB/月
```

---

## 🆘 阿里雲常見問題

### Q1: 如何提升中國大陸訪問速度？

**A:** 使用阿里雲 CDN

```bash
# 1. 開通阿里雲 CDN
# 2. 添加加速域名：static.zhe-wei.net
# 3. 配置源站：YOUR_ECS_IP
# 4. 更新 Nginx 配置，靜態資源指向 CDN
```

### Q2: 如何降低流量成本？

**A:** 使用 OSS + CDN

```bash
# 1. 靜態資源上傳到 OSS
# 2. 啟用 OSS 的 CDN 加速
# 3. 成本對比：
#    - ECS 流量：¥0.8/GB
#    - OSS + CDN：¥0.15/GB（節省 80%）
```

### Q3: 如何備份資料？

**A:** 多重備份策略

```bash
# 1. 自動快照（每天）
# 2. 定期備份到 OSS
rsync -avz /opt/zhewei/ oss://zhewei-backup/$(date +%Y%m%d)/

# 3. 異地備份（使用 rclone 同步到 Google Drive）
```

### Q4: 如何處理 ICP 備案？

**A:** 如果使用自己的域名

```
1. 在阿里雲 ICP 備案系統提交申請
2. 準備資料：
   - 身份證
   - 域名證書
   - 網站資訊
3. 等待審核（約 20 個工作天）
4. 備案完成後才能使用 80/443 端口

臨時方案：
- 使用 Cloudflare Tunnel（不需要備案）
- 使用非標準端口（如 8080）
```

---

## 📚 相關文件

- **混合部署指南**：`docs/deployment/HYBRID_DEPLOYMENT_GUIDE.md`
- **快速部署**：`HYBRID_DEPLOYMENT_QUICKSTART.md`
- **雲端部署總覽**：`README_CLOUD_DEPLOYMENT.md`

---

## ✨ 阿里雲部署總結

### 優勢
- ✅ 中國大陸訪問速度極快
- ✅ 支付方式便利（支付寶/微信）
- ✅ 完整的中文支援與客服
- ✅ 豐富的生態整合（OSS、CDN、通義千問）
- ✅ 學生優惠超值（¥9.5/月）

### 成本
- **基礎方案**：¥108/月（2核4GB）
- **學生方案**：¥9.5/月（首年）
- **混合部署**：¥108/月 + 本地電費

### 適用場景
- 🎯 主要用戶在中國大陸
- 🎯 需要中文客服支援
- 🎯 想整合阿里雲生態
- 🎯 預算充足（相比 Oracle Cloud 免費方案）

**開始部署：** 登入 [阿里雲控制台](https://ecs.console.aliyun.com) 建立您的第一台 ECS 實例！

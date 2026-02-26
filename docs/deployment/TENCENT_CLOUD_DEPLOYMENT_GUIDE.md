# 築未科技 — 騰訊雲部署指南

## 🎯 騰訊雲優勢

### 為什麼選擇騰訊雲？

**✅ 遊戲與社交生態：**
- 🎮 微信、QQ 生態整合
- 🎯 遊戲行業優化方案
- 📱 小程式雲開發支援
- 💬 即時通訊 IM 服務

**✅ 價格競爭力：**
- 💰 新用戶免費試用
- 🎁 學生優惠（¥10/月）
- 📊 按量付費靈活
- 🎁 代金券優惠多

**✅ 技術優勢：**
- ☁️ CVM 雲伺服器
- 🤖 混元大模型 API
- 🗄️ COS 物件儲存
- 🌐 CDN 全球加速

---

## 💰 騰訊雲方案對比

### 方案 A：輕量應用伺服器（推薦新手）

| 規格 | 配置 | 價格 | 適用場景 |
|------|------|------|----------|
| 入門版 | 2核2GB | ¥50/月 | 測試環境 |
| 基礎版 | 2核4GB | ¥90/月 | 小型生產 |
| 標準版 | 4核8GB | ¥260/月 | 中型生產 |

**特點：**
- ✅ 預裝常用環境
- ✅ 固定帶寬（3-6 Mbps）
- ✅ 包含流量包（1-3 TB/月）
- ✅ 一鍵部署應用

### 方案 B：CVM 雲伺服器（推薦進階）

| 規格 | 配置 | 價格 | 適用場景 |
|------|------|------|----------|
| 標準型 | 2核4GB | ¥75/月 | 開發測試 |
| 計算型 | 2核8GB | ¥165/月 | 標準生產 |
| 通用型 | 4核16GB | ¥420/月 | 大型生產 |

**特點：**
- ✅ 彈性配置
- ✅ 支援 GPU 實例
- ✅ 多種計費模式
- ✅ 企業級 SLA

### 方案 C：混合部署（最推薦）

**架構：**
- 騰訊雲 CVM：核心服務（¥90/月）
- 本地主機：GPU 服務（電費）
- **總成本：¥90-130/月**

---

## 🚀 騰訊雲快速部署

### 步驟 1：建立 CVM 實例（10 分鐘）

#### 1.1 登入騰訊雲控制台

```
https://console.cloud.tencent.com/cvm
```

#### 1.2 建立實例

**基本配置：**
- **地域**：選擇離您最近的區域（如：廣州、上海）
- **實例規格**：標準型 S5.MEDIUM4（2核4GB）
- **鏡像**：Ubuntu Server 22.04 LTS 64位
- **儲存**：50GB 高性能雲硬碟
- **網路**：私有網路（VPC）

**網路與安全：**
- **公網 IP**：分配
- **帶寬**：按使用流量（建議 5 Mbps）
- **安全組**：
  - SSH (22)：允許所有 IP
  - HTTP (80)：允許所有 IP
  - HTTPS (443)：允許所有 IP

**系統配置：**
- **登入方式**：密鑰對（推薦）或密碼
- **實例名稱**：zhewei-brain-server
- **主機名**：zhewei-prod

#### 1.3 配置安全組規則

```
入站規則：
- SSH (22)：0.0.0.0/0
- HTTP (80)：0.0.0.0/0
- HTTPS (443)：0.0.0.0/0
- 自定義 TCP (8000-8030)：0.0.0.0/0（調試用）
```

---

### 步驟 2：連接並初始化（5 分鐘）

#### 2.1 SSH 連接

```bash
# 使用密鑰對
ssh -i ~/.ssh/tencent_key.pem ubuntu@YOUR_CVM_IP

# 或使用密碼
ssh ubuntu@YOUR_CVM_IP
```

#### 2.2 系統更新

```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝基礎工具
sudo apt install -y curl wget git vim htop net-tools
```

#### 2.3 安裝 Docker

```bash
# 使用騰訊雲 Docker 鏡像源（速度更快）
curl -fsSL https://get.docker.com | sh

# 配置騰訊雲 Docker 鏡像加速器
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
EOF

# 重啟 Docker
sudo systemctl daemon-reload
sudo systemctl restart docker
sudo systemctl enable docker

# 將當前用戶加入 docker 組
sudo usermod -aG docker $USER

# 登出再登入使權限生效
exit
ssh ubuntu@YOUR_CVM_IP

# 驗證安裝
docker --version
docker run hello-world
```

---

### 步驟 3：部署專案（10 分鐘）

#### 3.1 上傳專案

**方法 1：Git Clone（推薦）**

```bash
cd /opt
sudo mkdir zhewei && sudo chown $USER:$USER zhewei
cd zhewei
git clone YOUR_REPO .
```

**方法 2：使用騰訊雲 COS（適合大型專案）**

```bash
# 安裝 COSCMD
pip3 install coscmd

# 配置 COS
coscmd config -a YOUR_SECRET_ID -s YOUR_SECRET_KEY \
  -b YOUR_BUCKET -r ap-guangzhou

# 下載專案
cd /opt
coscmd download -r zhewei/ ./zhewei/
```

#### 3.2 設定環境變數

```bash
cd /opt/zhewei
cp env.hybrid.example .env
vim .env
```

**騰訊雲專屬配置：**

```env
# Cloudflare Tunnel（必要）
CLOUDFLARE_TOKEN=your_cloudflare_tunnel_token

# Ollama 配置
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_GPU_URL=https://ollama-gpu.zhe-wei.net

# 騰訊混元大模型 API（可選）
HUNYUAN_API_KEY=your_hunyuan_api_key
HUNYUAN_MODEL=hunyuan-lite

# AI Provider Keys
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key

# 騰訊雲 COS（可選，用於檔案儲存）
TENCENT_COS_SECRET_ID=your_secret_id
TENCENT_COS_SECRET_KEY=your_secret_key
TENCENT_COS_REGION=ap-guangzhou
TENCENT_COS_BUCKET=zhewei-storage-1234567890

# 騰訊雲 CDN（可選）
TENCENT_CDN_DOMAIN=static.zhe-wei.net

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

#### 4.1 在騰訊雲 DNSPod 設定

**選項 A：使用 Cloudflare Tunnel（推薦）**

```bash
# 已在 deploy_to_cloud.sh 中自動配置
# 域名會自動透過 Cloudflare Tunnel 暴露
```

**選項 B：直接使用騰訊雲 DNSPod**

```
登入 DNSPod 控制台：
https://console.dnspod.cn

添加記錄：
- jarvis.zhe-wei.net → A → YOUR_CVM_IP
- cms.zhe-wei.net → A → YOUR_CVM_IP
- codesim.zhe-wei.net → A → YOUR_CVM_IP
```

#### 4.2 配置 SSL 證書

**選項 A：使用騰訊雲免費證書**

```bash
# 在騰訊雲 SSL 證書控制台申請免費證書
# https://console.cloud.tencent.com/ssl

# 下載證書並上傳到伺服器
mkdir -p /opt/zhewei/ssl
# 上傳 certificate.crt 和 private.key

# 更新 Nginx 配置
vim /opt/zhewei/gateway/nginx.cloud.conf
# 添加 SSL 配置

# 重啟 Gateway
docker compose -f docker-compose.cloud.yml restart gateway
```

**選項 B：使用 Let's Encrypt（自動續期）**

```bash
# 安裝 acme.sh
curl https://get.acme.sh | sh
source ~/.bashrc

# 申請證書（使用 DNSPod API）
export DP_Id="YOUR_DNSPOD_ID"
export DP_Key="YOUR_DNSPOD_KEY"

acme.sh --issue --dns dns_dp \
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
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久啟用
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 調整 swappiness
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

#### 5.2 配置騰訊雲 CDN（加速靜態資源）

```bash
# 在騰訊雲 CDN 控制台配置
# https://console.cloud.tencent.com/cdn

# 配置項：
# - 源站類型：自有源
# - 源站地址：YOUR_CVM_IP
# - 加速域名：static.zhe-wei.net
# - 快取規則：
#   - *.js, *.css, *.png, *.jpg → 快取 30 天
#   - *.html → 快取 1 小時
#   - /api/* → 不快取
```

#### 5.3 配置騰訊雲 CLB（負載均衡，可選）

```bash
# 適用於高流量場景
# 在騰訊雲 CLB 控制台配置
# https://console.cloud.tencent.com/clb

# 配置項：
# - 監聽器：HTTP:80, HTTPS:443
# - 後端伺服器：YOUR_CVM_IP:80
# - 健康檢查：HTTP GET /health
# - 會話保持：啟用（30 分鐘）
```

---

## 🔧 騰訊雲專屬功能整合

### 1. 混元大模型 API 整合

建立 `tencent_hunyuan_client.py`：

```python
import os
import json
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

def call_hunyuan(messages):
    """呼叫騰訊混元大模型 API"""
    try:
        # 憑證配置
        cred = credential.Credential(
            os.getenv("TENCENT_SECRET_ID"),
            os.getenv("TENCENT_SECRET_KEY")
        )
        
        # HTTP 配置
        httpProfile = HttpProfile()
        httpProfile.endpoint = "hunyuan.tencentcloudapi.com"
        
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        
        # 建立客戶端
        client = hunyuan_client.HunyuanClient(cred, "", clientProfile)
        
        # 建立請求
        req = models.ChatCompletionsRequest()
        params = {
            "Model": os.getenv("HUNYUAN_MODEL", "hunyuan-lite"),
            "Messages": messages,
            "Stream": False
        }
        req.from_json_string(json.dumps(params))
        
        # 發送請求
        resp = client.ChatCompletions(req)
        
        # 解析回應
        result = json.loads(resp.to_json_string())
        return result['Choices'][0]['Message']['Content']
        
    except Exception as e:
        return f"錯誤: {str(e)}"

# 使用範例
if __name__ == "__main__":
    messages = [
        {"Role": "user", "Content": "你好，請介紹一下自己"}
    ]
    response = call_hunyuan(messages)
    print(response)
```

### 2. 騰訊雲 COS 檔案儲存

建立 `tencent_cos_client.py`：

```python
import os
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client

# 初始化配置
config = CosConfig(
    Region=os.getenv('TENCENT_COS_REGION', 'ap-guangzhou'),
    SecretId=os.getenv('TENCENT_COS_SECRET_ID'),
    SecretKey=os.getenv('TENCENT_COS_SECRET_KEY'),
    Token=None,
    Scheme='https'
)

client = CosS3Client(config)
bucket = os.getenv('TENCENT_COS_BUCKET')

def upload_file(local_path, cos_path):
    """上傳檔案到 COS"""
    response = client.upload_file(
        Bucket=bucket,
        LocalFilePath=local_path,
        Key=cos_path,
        PartSize=1,
        MAXThread=10
    )
    return f"https://{bucket}.cos.{config.Region}.myqcloud.com/{cos_path}"

def download_file(cos_path, local_path):
    """從 COS 下載檔案"""
    response = client.download_file(
        Bucket=bucket,
        Key=cos_path,
        DestFilePath=local_path
    )
    return local_path

def list_files(prefix=''):
    """列出 COS 中的檔案"""
    response = client.list_objects(
        Bucket=bucket,
        Prefix=prefix
    )
    if 'Contents' in response:
        return [obj['Key'] for obj in response['Contents']]
    return []

# 使用範例
if __name__ == "__main__":
    # 上傳檔案
    url = upload_file('/path/to/local/file.txt', 'uploads/file.txt')
    print(f"上傳成功: {url}")
    
    # 列出檔案
    files = list_files('uploads/')
    print(f"檔案列表: {files}")
```

### 3. 騰訊雲 IM 即時通訊整合

```python
from tencentcloud.common import credential
from tencentcloud.im.v20190719 import im_client, models

def send_im_message(user_id, content):
    """發送 IM 訊息"""
    cred = credential.Credential(
        os.getenv("TENCENT_SECRET_ID"),
        os.getenv("TENCENT_SECRET_KEY")
    )
    
    client = im_client.ImClient(cred, "")
    req = models.SendSingleChatRequest()
    
    params = {
        "SdkAppId": os.getenv("TENCENT_IM_SDK_APP_ID"),
        "UserId": user_id,
        "MsgBody": [{"MsgType": "TIMTextElem", "MsgContent": {"Text": content}}]
    }
    req.from_json_string(json.dumps(params))
    
    resp = client.SendSingleChat(req)
    return resp.to_json_string()
```

---

## 📊 騰訊雲 vs 其他雲端對比

| 項目 | 騰訊雲 | 阿里雲 | Oracle Cloud | Linode | Vultr |
|------|--------|--------|--------------|--------|-------|
| **價格** | ¥90/月 | ¥108/月 | 免費 | $12/月 | $12/月 |
| **中國速度** | ⚡ 極快 | ⚡ 極快 | 🐢 慢 | 🚶 中等 | 🚶 中等 |
| **支付方式** | 微信/支付寶 | 支付寶/微信 | 信用卡 | 信用卡 | 信用卡 |
| **中文支援** | ✅ 完整 | ✅ 完整 | ❌ 無 | ❌ 無 | ❌ 無 |
| **生態整合** | ✅ 微信/QQ | ✅ 淘寶/釘釘 | ❌ 少 | ❌ 少 | ❌ 少 |
| **GPU 實例** | ✅ 有 | ✅ 有 | ❌ 無 | ❌ 無 | ✅ 有 |
| **免費額度** | 試用 | 試用 | 永久免費 | ❌ 無 | ❌ 無 |
| **大模型 API** | ✅ 混元 | ✅ 通義千問 | ❌ 無 | ❌ 無 | ❌ 無 |
| **學生優惠** | ¥10/月 | ¥9.5/月 | ❌ 無 | ❌ 無 | ❌ 無 |

### 詳細對比

#### 價格對比（2核4GB 標準配置）
- **騰訊雲**：¥90/月（輕量）/ ¥75/月（CVM）
- **阿里雲**：¥108/月（輕量）/ ¥80/月（ECS）
- **Oracle Cloud**：免費（1GB RAM）
- **Linode**：$12/月（約 ¥85/月）
- **Vultr**：$12/月（約 ¥85/月）

#### 速度對比（中國大陸訪問）
1. **騰訊雲**：⭐⭐⭐⭐⭐（極快）
2. **阿里雲**：⭐⭐⭐⭐⭐（極快）
3. **Linode**：⭐⭐⭐（中等）
4. **Vultr**：⭐⭐⭐（中等）
5. **Oracle Cloud**：⭐⭐（較慢）

#### 生態整合對比
- **騰訊雲**：微信、QQ、小程式、遊戲
- **阿里雲**：淘寶、釘釘、支付寶、電商
- **其他**：基礎雲服務

---

## 💰 騰訊雲成本優化

### 1. 使用包年包月（節省 15-20%）

```
2核4GB 輕量應用伺服器：
- 按月：¥90/月
- 包年：¥900/年（相當於 ¥75/月，節省 ¥180）
- 3 年：¥2,160（相當於 ¥60/月，節省 ¥1,080）
```

### 2. 使用競價實例（節省 80%）

```
適用於開發測試環境：
- 標準價格：¥75/月
- 競價實例：¥15/月（節省 80%）
- 注意：可能被回收，需要做好容錯
```

### 3. 使用學生優惠（最划算）

```
學生認證後：
- 輕量應用伺服器：¥10/月（首年）
- CVM 標準型：¥10/月（首年）
- 節省：88% 成本
```

### 4. 使用 COS + CDN（降低流量成本）

```
流量成本對比：
- CVM 流量：¥0.8/GB
- COS + CDN：¥0.18/GB（節省 77%）

月流量 100GB 的成本：
- 純 CVM：¥80
- COS + CDN：¥18（節省 ¥62）
```

### 5. 使用代金券

```
騰訊雲經常發放代金券：
- 新用戶：¥2,000-5,000 代金券
- 活動期間：額外代金券
- 推薦好友：雙方獲得代金券
```

---

## 🔧 騰訊雲監控與維護

### 1. 雲監控（免費）

```bash
# 在騰訊雲控制台啟用雲監控
# https://console.cloud.tencent.com/monitor

# 自動監控指標：
# - CPU 使用率
# - 記憶體使用率
# - 磁碟使用率
# - 網路流量
# - 磁碟 I/O

# 設定告警策略：
# - CPU > 80% 持續 5 分鐘 → 發送簡訊/郵件/微信
# - 記憶體 > 90% → 告警
# - 磁碟使用率 > 85% → 告警
```

### 2. 日誌服務 CLS

```bash
# 安裝 LogListener
wget https://loglistener-1254077820.cos.ap-shanghai.myqcloud.com/loglistener-linux-x64-2.6.2.tar.gz
tar -zxvf loglistener-linux-x64-2.6.2.tar.gz
cd loglistener/tools
./loglistener.sh install

# 配置日誌收集
# Docker 容器日誌自動收集到 CLS
# 支援實時檢索和分析
```

### 3. 自動快照備份

```bash
# 在騰訊雲控制台設定定期快照策略
# https://console.cloud.tencent.com/cvm/snapshot

# 建議配置：
# - 每天凌晨 2:00 自動快照
# - 保留最近 7 天
# - 快照費用：¥0.099/GB/月（比阿里雲便宜）
```

### 4. 使用騰訊雲助手（自動化運維）

```bash
# 安裝騰訊雲助手
wget https://tat-gz-1258344699.cos.ap-guangzhou.myqcloud.com/install_tat_agent_linux.sh
bash install_tat_agent_linux.sh

# 功能：
# - 遠端執行命令
# - 批次操作
# - 自動化腳本
# - 無需 SSH 登入
```

---

## 🆘 騰訊雲常見問題

### Q1: 如何提升中國大陸訪問速度？

**A:** 使用騰訊雲 CDN + COS

```bash
# 1. 開通騰訊雲 CDN
# 2. 靜態資源上傳到 COS
# 3. 配置 CDN 加速域名
# 4. 更新 Nginx 配置指向 CDN

# 效果：
# - 訪問速度提升 3-5 倍
# - 降低源站壓力
# - 節省流量成本
```

### Q2: 如何整合微信小程式？

**A:** 使用騰訊雲開發（CloudBase）

```bash
# 1. 開通雲開發
# 2. 配置雲函數
# 3. 使用雲資料庫
# 4. 一鍵部署到小程式

# 優勢：
# - 無需伺服器運維
# - 自動擴縮容
# - 與微信生態深度整合
```

### Q3: 如何備份資料？

**A:** 多重備份策略

```bash
# 1. 自動快照（每天）
# 2. 定期備份到 COS
tar -czf backup-$(date +%Y%m%d).tar.gz /opt/zhewei
coscmd upload backup-$(date +%Y%m%d).tar.gz backups/

# 3. 異地備份（使用 rclone 同步到其他雲）
rclone sync /opt/zhewei remote:zhewei-backup
```

### Q4: 如何處理 ICP 備案？

**A:** 騰訊雲備案流程

```
1. 在騰訊雲備案系統提交申請
   https://console.cloud.tencent.com/beian

2. 準備資料：
   - 身份證
   - 域名證書
   - 網站資訊
   - 核驗單（騰訊雲提供）

3. 等待審核（約 15-20 個工作天）

4. 備案完成後才能使用 80/443 端口

臨時方案：
- 使用 Cloudflare Tunnel（不需要備案）
- 使用非標準端口（如 8080）
- 使用海外伺服器
```

### Q5: 騰訊雲 vs 阿里雲如何選擇？

**A:** 根據業務需求選擇

**選擇騰訊雲如果：**
- ✅ 需要整合微信/QQ 生態
- ✅ 開發小程式或遊戲
- ✅ 需要混元大模型 API
- ✅ 預算稍緊（比阿里雲便宜 15%）

**選擇阿里雲如果：**
- ✅ 需要整合淘寶/釘釘生態
- ✅ 開發電商或企業應用
- ✅ 需要通義千問 API
- ✅ 需要更成熟的企業級服務

---

## 📚 相關文件

- **混合部署指南**：`docs/deployment/HYBRID_DEPLOYMENT_GUIDE.md`
- **阿里雲部署**：`docs/deployment/ALIYUN_DEPLOYMENT_GUIDE.md`
- **快速部署**：`HYBRID_DEPLOYMENT_QUICKSTART.md`
- **雲端部署總覽**：`README_CLOUD_DEPLOYMENT.md`

---

## ✨ 騰訊雲部署總結

### 優勢
- ✅ **價格最優**：比阿里雲便宜 15-20%
- ✅ **速度極快**：中國大陸訪問極快
- ✅ **微信生態**：深度整合微信、QQ、小程式
- ✅ **混元大模型**：騰訊自研 AI 大模型
- ✅ **學生優惠**：¥10/月超值方案
- ✅ **代金券多**：新用戶最高 ¥5,000 代金券

### 成本
- **基礎方案**：¥90/月（2核4GB）
- **學生方案**：¥10/月（首年）
- **混合部署**：¥90/月 + 本地電費
- **年付優惠**：¥75/月（節省 ¥180/年）

### 適用場景
- 🎯 需要整合微信/QQ 生態
- 🎯 開發小程式或遊戲
- 🎯 預算有限（比阿里雲便宜）
- 🎯 需要混元大模型 API
- 🎯 主要用戶在中國大陸

**開始部署：** 登入 [騰訊雲控制台](https://console.cloud.tencent.com/cvm) 建立您的第一台 CVM 實例！

**新用戶福利：** 領取 [騰訊雲代金券](https://cloud.tencent.com/act/pro/free) 最高 ¥5,000！

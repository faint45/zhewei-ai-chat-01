# 🚀 自動化部署系統

## 概述

現在你不需要每次新增項目都手動配置域名和路由了！只需要在一個配置檔案中添加新服務，運行一個腳本，所有配置都會自動生成。

## 📋 核心檔案

### 1. `services.json` - 服務配置檔案（你只需要編輯這個）

```json
{
  "services": [
    {
      "name": "新服務名稱",
      "subdomain": "subdomain",
      "domain": "zhe-wei.net",
      "port": 8080,
      "target": "host.docker.internal:8080",
      "description": "服務描述",
      "enabled": true
    }
  ]
}
```

### 2. `scripts/auto_deploy.py` - 自動部署腳本

自動生成：
- ✅ Nginx 配置
- ✅ Cloudflare Tunnel 配置
- ✅ Portal 服務列表

### 3. `scripts/sync_cloudflare.py` - Cloudflare 同步腳本（可選）

如果有 API Token，可以自動同步到 Cloudflare。

---

## 🎯 使用方式

### 方式 1：完全自動化（推薦）

#### 步驟 1：添加新服務到 `services.json`

```json
{
  "name": "我的新項目",
  "subdomain": "myproject",
  "domain": "zhe-wei.net",
  "port": 9000,
  "target": "host.docker.internal:9000",
  "description": "我的新項目描述",
  "enabled": true
}
```

#### 步驟 2：運行自動部署腳本

```bash
python scripts/auto_deploy.py
```

這會自動：
- ✅ 生成新的 Nginx 配置
- ✅ 生成 Cloudflare 配置清單
- ✅ 更新 Portal 服務列表

#### 步驟 3：重啟 Gateway

```bash
docker compose restart gateway
```

#### 步驟 4：添加域名到 Cloudflare

**選項 A：手動添加（2分鐘）**

1. 訪問 https://one.dash.cloudflare.com/
2. Access → Tunnels → Configure
3. 添加腳本輸出的域名

**選項 B：自動同步（需要 API Token）**

```bash
# 設定 API Token
set CLOUDFLARE_API_TOKEN=your_token_here

# 運行同步
python scripts/sync_cloudflare.py
```

---

### 方式 2：純手動（不推薦）

如果你想完全手動，仍然可以：
1. 編輯 `gateway/nginx.conf`
2. 在 Cloudflare 控制台添加域名
3. 手動更新 Portal 配置

但這樣很麻煩，不建議。

---

## 📝 配置欄位說明

| 欄位 | 說明 | 範例 |
|------|------|------|
| `name` | 服務名稱 | "My Project" |
| `subdomain` | 子域名（留空=主域名） | "myproject" |
| `domain` | 主域名 | "zhe-wei.net" |
| `port` | 服務端口 | 9000 |
| `target` | 內部目標地址 | "host.docker.internal:9000" |
| `description` | 服務描述 | "我的新項目" |
| `enabled` | 是否啟用 | true/false |

---

## 🎨 範例：添加新項目

### 1. 編輯 `services.json`

```json
{
  "name": "Blog",
  "subdomain": "blog",
  "domain": "zhe-wei.net",
  "port": 3000,
  "target": "host.docker.internal:3000",
  "description": "個人部落格",
  "enabled": true
}
```

### 2. 運行部署

```bash
python scripts/auto_deploy.py
docker compose restart gateway
```

### 3. 添加域名

在 Cloudflare 添加：
- `blog.zhe-wei.net` → `gateway:80`

### 4. 完成！

訪問 https://blog.zhe-wei.net

---

## 🔧 進階功能

### 禁用服務

將 `enabled` 設為 `false`：

```json
{
  "name": "舊項目",
  "enabled": false
}
```

再次運行 `auto_deploy.py`，該服務會從所有配置中移除。

### 使用 Docker 容器名稱

如果服務在 Docker 內：

```json
{
  "target": "container_name:8000"
}
```

如果服務在主機：

```json
{
  "target": "host.docker.internal:8000"
}
```

---

## 📊 當前服務列表

運行以下命令查看當前所有服務：

```bash
python -c "import json; print(json.dumps(json.load(open('services.json'))['services'], indent=2))"
```

---

## 🆘 故障排除

### 問題：Gateway 重啟後 404

**原因**：Nginx 配置有誤

**解決**：
```bash
# 檢查 Nginx 配置
docker compose exec gateway nginx -t

# 查看日誌
docker compose logs gateway
```

### 問題：域名無法訪問

**原因**：未在 Cloudflare 添加域名

**解決**：
1. 檢查 `cloudflare_tunnel_config.json`
2. 確認域名已添加到 Cloudflare Zero Trust

### 問題：Portal 沒有顯示新服務

**原因**：Portal 未重啟

**解決**：
```bash
docker compose restart portal
```

---

## ✨ 優勢

### 之前（手動）：
1. ❌ 編輯 `nginx.conf`（容易出錯）
2. ❌ 登入 Cloudflare 控制台
3. ❌ 手動添加域名
4. ❌ 更新 Portal 配置
5. ❌ 重啟多個服務
6. ⏱️ 需要 10-15 分鐘

### 現在（自動化）：
1. ✅ 編輯 `services.json`（一個檔案）
2. ✅ 運行 `auto_deploy.py`（一個命令）
3. ✅ 重啟 Gateway（一個命令）
4. ✅ 在 Cloudflare 添加域名（或自動同步）
5. ⏱️ 只需要 2-3 分鐘

---

## 🎯 總結

**以後新增項目只需要 3 步：**

```bash
# 1. 編輯配置
code services.json

# 2. 自動部署
python scripts/auto_deploy.py

# 3. 重啟服務
docker compose restart gateway
```

**完成！** 🎉

不用再每次都手動配置域名和路由了！

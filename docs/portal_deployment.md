# Portal 服務入口網站部署指南

## 概述

Portal 是築未科技的統一服務入口網站，整合所有 AI 服務的快速訪問。

## 功能特色

- **6 個核心服務整合**：Jarvis AI、Smart Bridge、Dify、營建管理、AI 視覺、代碼模擬器
- **即時狀態監控**：自動檢測所有服務在線狀態
- **美觀的卡片式 UI**：漸層色彩、懸浮效果、響應式設計
- **快速連結**：登入、管理、推播、付款等常用功能
- **系統統計**：正常運行率、響應時間、服務數量

## 檔案結構

```
zhe-wei-tech/
├── portal_server.py              # FastAPI 後端服務
├── portal/
│   └── index.html                # 前端頁面
├── scripts/
│   └── start_portal.bat          # Windows 啟動腳本
├── docker-compose.yml            # Docker 編排 (已添加 portal 服務)
└── gateway/
    └── nginx.conf                # Nginx 配置 (已添加主域名路由)
```

## 本地啟動

### 方法 1: 直接啟動

```bash
# Windows
scripts\start_portal.bat

# 或直接執行
python portal_server.py
```

訪問：http://localhost:8888

### 方法 2: Docker Compose

```bash
# 啟動 Portal 服務
docker compose up -d portal

# 查看日誌
docker compose logs -f portal
```

## API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/` | GET | 入口網站首頁 |
| `/health` | GET | 健康檢查 |
| `/api/services` | GET | 取得所有服務列表 |
| `/api/services/status` | GET | 檢查所有服務狀態 |
| `/api/stats` | GET | 系統統計資訊 |

## 整合的服務

### 核心 AI 服務

1. **Jarvis AI Brain** (Port 8000)
   - 域名：https://jarvis.zhe-wei.net
   - 功能：AI 對話、知識庫、工作流

2. **Smart Bridge** (Port 8003)
   - 域名：https://bridge.zhe-wei.net
   - 功能：成本優化、即時對話、本地學習

3. **Dify AI Platform** (Port 8080)
   - 域名：https://dify.zhe-wei.net
   - 功能：工作流、低代碼、插件

### 專業應用服務

4. **營建管理系統** (Port 8020)
   - 域名：https://cms.zhe-wei.net
   - 功能：工程管理、語音辨識、文件搜尋

5. **AI 視覺辨識** (Port 8030)
   - 域名：https://vision.zhe-wei.net
   - 功能：物件偵測、OCR、安全檢測

6. **代碼模擬器** (Port 8001)
   - 域名：https://codesim.zhe-wei.net
   - 功能：代碼執行、AI 分析、項目管理

## 外網訪問配置

### Nginx 配置

已自動添加主域名路由到 `gateway/nginx.conf`：

```nginx
server {
    listen 80;
    server_name zhe-wei.net www.zhe-wei.net;

    location / {
        proxy_pass http://host.docker.internal:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
    }
}
```

### Cloudflare Tunnel 配置

需要在 Cloudflare Zero Trust 控制台添加主域名：

1. 登入：https://one.dash.cloudflare.com/
2. Access → Tunnels → Configure
3. 添加 Public Hostname：
   - Subdomain: (留空)
   - Domain: zhe-wei.net
   - Service: HTTP
   - URL: gateway:80

4. 同時添加 www 子域名：
   - Subdomain: www
   - Domain: zhe-wei.net
   - Service: HTTP
   - URL: gateway:80

### 重啟服務

```bash
# 重啟 Gateway 以載入新配置
docker compose restart gateway

# 重啟 Portal
docker compose restart portal
```

## 服務狀態檢測

Portal 會自動檢測所有服務的在線狀態：

- **檢測頻率**：每 30 秒
- **檢測方式**：優先本地 health endpoint，失敗則嘗試外網
- **狀態顯示**：
  - 🟢 綠色：在線
  - 🔴 紅色：離線
  - 🟡 黃色：檢測中

## 環境變數

```bash
PORTAL_PORT=8888  # Portal 服務端口
```

## 測試

### 本地測試

```bash
# 健康檢查
curl http://localhost:8888/health

# 服務列表
curl http://localhost:8888/api/services

# 服務狀態
curl http://localhost:8888/api/services/status

# 系統統計
curl http://localhost:8888/api/stats
```

### 外網測試

設定完成後訪問：
- https://zhe-wei.net
- https://www.zhe-wei.net

## 自訂修改

### 修改服務列表

編輯 `portal_server.py` 中的 `SERVICES` 字典：

```python
SERVICES = {
    "service_id": {
        "name": "服務名稱",
        "url": "https://service.zhe-wei.net",
        "health": "https://service.zhe-wei.net/health",
        "local": "http://localhost:PORT/health",
        "icon": "font-awesome-icon-name",
        "color": "tailwind-color"
    }
}
```

### 修改前端樣式

編輯 `portal/index.html`：
- 修改顏色：搜尋 `gradient-bg` 或 `from-xxx-500`
- 修改卡片：搜尋 `service-card`
- 修改圖標：搜尋 `fas fa-xxx`

## 完整域名列表

設定完成後的所有域名：

| 域名 | 服務 | 說明 |
|------|------|------|
| **zhe-wei.net** | **Portal** | **主入口網站** |
| jarvis.zhe-wei.net | Jarvis AI | AI 大腦系統 |
| bridge.zhe-wei.net | Smart Bridge | 智慧對話橋接 |
| dify.zhe-wei.net | Dify | AI 工作流平台 |
| cms.zhe-wei.net | CMS | 營建管理系統 |
| vision.zhe-wei.net | Vision | AI 視覺辨識 |
| codesim.zhe-wei.net | CodeSim | 代碼模擬器 |

## 故障排除

### Portal 無法啟動

**檢查 Port 8888 是否被佔用**：
```bash
netstat -ano | findstr :8888
```

**解決方案**：
```bash
# 修改環境變數
set PORTAL_PORT=8889
python portal_server.py
```

### 服務狀態顯示離線

**可能原因**：
1. 服務未啟動
2. Health endpoint 路徑錯誤
3. CORS 限制

**檢查方法**：
```bash
# 直接測試 health endpoint
curl http://localhost:PORT/health
```

### 外網無法訪問

**檢查項目**：
1. Cloudflare Tunnel 是否添加主域名
2. Gateway 是否重啟
3. DNS 是否生效

```bash
# 檢查 DNS
nslookup zhe-wei.net

# 檢查 Gateway
docker compose logs gateway
```

## 後續優化

- [ ] 添加用戶認證（整合現有 auth_manager）
- [ ] 服務使用統計儀表板
- [ ] 服務健康歷史記錄
- [ ] 自動告警（服務離線通知）
- [ ] 深色模式切換
- [ ] 多語言支援

## 授權

© 2026 築未科技 Zhe-Wei Tech. All rights reserved.

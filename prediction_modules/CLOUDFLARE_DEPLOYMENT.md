# 🌐 Cloudflare Tunnel 外網部署指南

## 系統外網域名

已配置兩個域名用於易經預測與國家級警報系統：

- 🔮 **predict.zhe-wei.net** - 易經科學預測系統
- 🚨 **alert.zhe-wei.net** - 國家級警報系統

兩個域名都指向同一個服務 (Port 8025)，可根據域名顯示不同內容。

---

## 📋 部署步驟

### 步驟 1: 確認 Nginx Gateway 配置

✅ 已在 `gateway/nginx.conf` 添加配置：

```nginx
# Prediction System (易經預測系統)
server {
    listen 80;
    server_name predict.zhe-wei.net;

    location / {
        proxy_pass http://host.docker.internal:8025;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
    }
}

# National Alert System (國家級警報系統)
server {
    listen 80;
    server_name alert.zhe-wei.net;

    location / {
        proxy_pass http://host.docker.internal:8025;
        # ... 同上配置
    }
}
```

### 步驟 2: 重啟 Nginx Gateway

```bash
# 重啟 Gateway 容器以載入新配置
docker restart zhewei_gateway

# 或重新建立
docker compose up -d zhewei_gateway
```

### 步驟 3: 在 Cloudflare Zero Trust 添加域名

1. 登入 **Cloudflare Zero Trust Dashboard**
2. 進入 **Access** → **Tunnels**
3. 找到你的 Tunnel (ID: `546fffc1-eb7d-4f9a-a3df-d30a1940aa0c`)
4. 點擊 **Configure**
5. 在 **Public Hostname** 添加兩個新路由：

#### 預測系統路由
```
Subdomain: predict
Domain: zhe-wei.net
Service: http://localhost:8888
```

#### 警報系統路由
```
Subdomain: alert
Domain: zhe-wei.net
Service: http://localhost:8888
```

**注意**: 兩個都指向 `localhost:8888` (Nginx Gateway)，由 Nginx 根據 `server_name` 分流到 `host.docker.internal:8025`

### 步驟 4: 啟動預測服務

```bash
# 啟動預測與警報系統
scripts\start_prediction_system.bat
```

### 步驟 5: 驗證部署

測試外網訪問：

```bash
# 測試預測系統
curl https://predict.zhe-wei.net/api/prediction/health

# 測試警報系統
curl https://alert.zhe-wei.net/api/prediction/health
```

---

## 🌍 外網訪問地址

### 易經預測系統
- 🖥️ **管理後台**: https://predict.zhe-wei.net/static/prediction_dashboard.html
- 📖 **API 文檔**: https://predict.zhe-wei.net/docs
- 🔌 **WebSocket**: wss://predict.zhe-wei.net/ws/predictions

### 國家級警報系統
- 📱 **手機接收器**: https://alert.zhe-wei.net/static/alert_receiver.html
- 🖥️ **管理後台**: https://alert.zhe-wei.net/static/prediction_dashboard.html
- 📖 **API 文檔**: https://alert.zhe-wei.net/docs

---

## 📱 手機端使用

### iOS 安裝 PWA

1. Safari 開啟: https://alert.zhe-wei.net/static/alert_receiver.html
2. 點擊「分享」按鈕 (底部中間)
3. 向下滾動，選擇「加入主畫面」
4. 點擊「加入」
5. 完成！現在可以從主畫面啟動

### Android 安裝 PWA

1. Chrome 開啟: https://alert.zhe-wei.net/static/alert_receiver.html
2. 點擊右上角選單 (三個點)
3. 選擇「安裝應用程式」或「加到主畫面」
4. 點擊「安裝」
5. 完成！

### PWA 特色
- ✅ 全螢幕顯示（無瀏覽器 UI）
- ✅ 離線可用
- ✅ 推播通知
- ✅ 像原生 APP 一樣

---

## 🔧 Cloudflare Tunnel 架構

```
使用者
  ↓ HTTPS
Cloudflare Edge (全球 CDN)
  ↓ 加密隧道
Cloudflare Tunnel (本地)
  ↓ localhost:8888
Nginx Gateway (Docker)
  ↓ 根據 server_name 分流
  ├─ predict.zhe-wei.net → host.docker.internal:8025
  └─ alert.zhe-wei.net → host.docker.internal:8025
       ↓
Prediction Service (FastAPI)
  ├─ 易經預測引擎
  ├─ 科學數據收集器
  └─ 國家級警報管理器
```

---

## 🔐 安全性配置

### 1. HTTPS 自動啟用
Cloudflare Tunnel 自動提供 HTTPS，無需手動配置 SSL 證書。

### 2. 訪問控制（可選）

在 Cloudflare Zero Trust 設定存取規則：

```yaml
# 僅允許台灣 IP 訪問
Rules:
  - Name: Taiwan Only
    Action: Allow
    Include:
      - Country: Taiwan (TW)
```

### 3. 速率限制

在 Nginx 添加速率限制：

```nginx
limit_req_zone $binary_remote_addr zone=prediction_limit:10m rate=10r/s;

server {
    server_name predict.zhe-wei.net;
    
    location /api/ {
        limit_req zone=prediction_limit burst=20;
        proxy_pass http://host.docker.internal:8025;
    }
}
```

---

## 📊 監控與日誌

### Cloudflare Analytics

在 Cloudflare Dashboard 可查看：
- 訪問流量統計
- 地理位置分布
- 請求延遲
- 錯誤率

### Nginx 日誌

```bash
# 查看訪問日誌
docker exec zhewei_gateway tail -f /var/log/nginx/access.log

# 查看錯誤日誌
docker exec zhewei_gateway tail -f /var/log/nginx/error.log

# 篩選預測系統請求
docker exec zhewei_gateway grep "predict.zhe-wei.net" /var/log/nginx/access.log
```

### 預測服務日誌

```bash
# 查看服務日誌
tail -f prediction_modules/logs/prediction_service.log
```

---

## 🚀 性能優化

### 1. Gzip 壓縮

Nginx 已啟用 Gzip，可節省 60-80% 流量：

```nginx
gzip on;
gzip_comp_level 5;
gzip_types text/plain text/css application/javascript application/json;
```

### 2. Cloudflare 快取

在 Cloudflare Page Rules 設定：

```
URL: predict.zhe-wei.net/static/*
Cache Level: Standard
Browser Cache TTL: 4 hours
```

### 3. WebSocket 優化

已配置 WebSocket 支援：

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
```

---

## 🔄 更新部署

### 更新服務

```bash
# 1. 停止服務
# Ctrl+C 停止 start_prediction_system.bat

# 2. 更新代碼
git pull

# 3. 重啟服務
scripts\start_prediction_system.bat
```

### 更新 Nginx 配置

```bash
# 1. 修改 gateway/nginx.conf

# 2. 重啟 Gateway
docker restart zhewei_gateway

# 3. 驗證配置
docker exec zhewei_gateway nginx -t
```

---

## 🐛 故障排除

### 問題 1: 無法訪問外網

**檢查清單:**
- [ ] Cloudflare Tunnel 是否運行？
  ```bash
  docker ps | grep zhewei_tunnel
  ```
- [ ] Nginx Gateway 是否運行？
  ```bash
  docker ps | grep zhewei_gateway
  ```
- [ ] 預測服務是否運行？
  ```bash
  netstat -ano | findstr :8025
  ```
- [ ] DNS 是否生效？
  ```bash
  nslookup predict.zhe-wei.net
  ```

### 問題 2: 502 Bad Gateway

**原因**: 預測服務未啟動或端口錯誤

**解決**:
```bash
# 確認服務運行在 8025
scripts\start_prediction_system.bat

# 測試本地訪問
curl http://localhost:8025/api/prediction/health
```

### 問題 3: WebSocket 連線失敗

**原因**: Nginx 未正確配置 WebSocket

**解決**: 確認 nginx.conf 包含：
```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
```

### 問題 4: 推播通知不工作

**原因**: HTTPS 環境下需要用戶授權

**解決**:
1. 確保使用 HTTPS (Cloudflare 自動提供)
2. 瀏覽器會提示授權通知
3. 用戶需點擊「允許」

---

## 📈 擴展建議

### 1. 多區域部署

使用 Cloudflare Load Balancing 分流：

```
predict.zhe-wei.net
  ├─ Asia Pool (主要)
  │   └─ Taiwan Server
  └─ Global Pool (備援)
      └─ US Server
```

### 2. CDN 加速

靜態資源使用 Cloudflare CDN：

```nginx
location /static/ {
    proxy_pass http://host.docker.internal:8025;
    proxy_cache_valid 200 1h;
    add_header Cache-Control "public, max-age=3600";
}
```

### 3. API 版本控制

```nginx
location /api/v1/ {
    proxy_pass http://host.docker.internal:8025/api/;
}

location /api/v2/ {
    proxy_pass http://host.docker.internal:8026/api/;
}
```

---

## 📞 技術支援

如遇問題，請提供以下資訊：

1. **錯誤訊息**
   ```bash
   docker logs zhewei_gateway
   docker logs zhewei_tunnel
   ```

2. **訪問日誌**
   ```bash
   docker exec zhewei_gateway tail -100 /var/log/nginx/access.log
   ```

3. **系統狀態**
   ```bash
   docker ps
   netstat -ano | findstr :8025
   ```

---

## ✅ 部署檢查清單

部署前確認：

- [ ] Nginx 配置已更新 (`gateway/nginx.conf`)
- [ ] Nginx Gateway 已重啟
- [ ] Cloudflare Tunnel 已添加域名路由
- [ ] 預測服務已啟動 (Port 8025)
- [ ] 本地測試通過 (`http://localhost:8025`)
- [ ] 外網測試通過 (`https://predict.zhe-wei.net`)
- [ ] WebSocket 連線正常
- [ ] 手機 PWA 可安裝
- [ ] 推播通知可用

---

## 🎉 部署完成

現在你的易經預測與國家級警報系統已成功部署到外網！

**訪問地址:**
- 🔮 預測系統: https://predict.zhe-wei.net
- 🚨 警報系統: https://alert.zhe-wei.net

**分享給用戶:**
- 📱 手機用戶: 直接訪問 https://alert.zhe-wei.net/static/alert_receiver.html
- 💻 桌面用戶: 訪問 https://predict.zhe-wei.net/static/prediction_dashboard.html

---

© 2026 築未科技 Zhewei Tech - Cloudflare Tunnel 部署指南

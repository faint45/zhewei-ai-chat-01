# Cloudflare Tunnel 添加域名指南

## 當前狀態

已配置的域名：
1. ✅ brain.zhe-wei.net → http://brain_server:8000
2. ✅ codesim.zhe-wei.net → http://localhost:8001
3. ✅ ufocam.zhe-wei.net → http://localhost:8035
4. ✅ bridge.zhe-wei.net → http://gateway:80

## 需要添加的域名

### 1. Portal 主域名 (zhe-wei.net)

**步驟**：

1. 點擊 "Add a published application route" 按鈕

2. 填寫配置：
   ```
   Subdomain: (留空)
   Domain: zhe-wei.net
   Path: (留空)
   
   Service:
   - Type: HTTP
   - URL: gateway:80
   ```

3. 點擊 "Save hostname"

### 2. WWW 子域名 (www.zhe-wei.net)

**步驟**：

1. 再次點擊 "Add a published application route"

2. 填寫配置：
   ```
   Subdomain: www
   Domain: zhe-wei.net
   Path: (留空)
   
   Service:
   - Type: HTTP
   - URL: gateway:80
   ```

3. 點擊 "Save hostname"

## 完整域名列表 (添加後)

| # | 域名 | 服務 | 說明 |
|---|------|------|------|
| 1 | **zhe-wei.net** | **Portal** | **主入口網站** |
| 2 | **www.zhe-wei.net** | **Portal** | **WWW 別名** |
| 3 | brain.zhe-wei.net | Brain Server | AI 大腦 (舊) |
| 4 | jarvis.zhe-wei.net | Jarvis AI | AI 大腦 (新) |
| 5 | bridge.zhe-wei.net | Smart Bridge | 智慧對話橋接 |
| 6 | codesim.zhe-wei.net | Code Simulator | 代碼模擬器 |
| 7 | dify.zhe-wei.net | Dify | AI 工作流 |
| 8 | cms.zhe-wei.net | CMS | 營建管理 |
| 9 | vision.zhe-wei.net | Vision | AI 視覺辨識 |
| 10 | ufocam.zhe-wei.net | UFO Cam | 監控系統 |

## 注意事項

### 為什麼使用 gateway:80 而不是 localhost:8888？

因為：
1. **Tunnel 在 Docker 容器內運行**，無法訪問 host 的 localhost
2. **Gateway 容器**作為統一入口，已配置好所有路由
3. **Gateway** 會根據域名自動轉發到對應服務

### Gateway 路由配置

Gateway (Nginx) 已配置：
- `zhe-wei.net` → `host.docker.internal:8888` (Portal)
- `bridge.zhe-wei.net` → `host.docker.internal:8003` (Smart Bridge)
- `jarvis.zhe-wei.net` → `brain_server:8000` (Jarvis)
- 其他域名類似...

## 驗證步驟

添加完成後：

1. **等待 DNS 生效** (通常 10-30 秒)

2. **檢查 Tunnel 日誌**：
   ```bash
   docker compose logs -f tunnel
   
   # 應該看到：
   # INF Updated to new configuration config="{...\"zhe-wei.net\"...}"
   ```

3. **測試訪問**：
   ```bash
   # 主域名
   curl -I https://zhe-wei.net
   
   # WWW 子域名
   curl -I https://www.zhe-wei.net
   ```

4. **瀏覽器測試**：
   - 訪問 https://zhe-wei.net
   - 應該看到 Portal 服務入口網站

## 故障排除

### 404 Not Found

**原因**：Gateway 未配置該域名路由

**解決**：
```bash
# 檢查 Nginx 配置
docker compose exec gateway cat /etc/nginx/nginx.conf | grep zhe-wei.net

# 重啟 Gateway
docker compose restart gateway
```

### 502 Bad Gateway

**原因**：Portal 服務未運行

**解決**：
```bash
# 檢查 Portal 狀態
curl http://localhost:8888/health

# 啟動 Portal
docker compose up -d portal
# 或
python portal_server.py
```

### DNS 未解析

**原因**：Cloudflare DNS 記錄未自動創建

**解決**：
1. 進入 Cloudflare Dashboard
2. 選擇 zhe-wei.net 域名
3. DNS 設定
4. 確認有 CNAME 記錄指向 Tunnel

## 下一步

添加完成後，你就可以：

1. ✅ 訪問 https://zhe-wei.net → 看到 Portal 入口網站
2. ✅ 從 Portal 快速跳轉到所有服務
3. ✅ 即時監控所有服務狀態
4. ✅ 使用統一的品牌域名

完成！🎉

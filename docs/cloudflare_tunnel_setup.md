# Cloudflare Tunnel 設定指南 - 添加 bridge.zhe-wei.net

## 當前狀態

Cloudflare Tunnel 已運行，但 `bridge.zhe-wei.net` 尚未配置。

**已配置的域名**：
- jarvis.zhe-wei.net → gateway:80
- dify.zhe-wei.net → gateway:80
- cms.zhe-wei.net → gateway:80
- vision.zhe-wei.net → gateway:80

**需要添加**：
- bridge.zhe-wei.net → gateway:80

## 設定步驟

### 方法 1: Cloudflare Zero Trust 控制台 (推薦)

1. **登入 Cloudflare Zero Trust**
   - 訪問：https://one.dash.cloudflare.com/
   - 選擇你的帳戶

2. **進入 Tunnel 設定**
   - 左側選單：Access → Tunnels
   - 找到你的 Tunnel (名稱應該類似 "zhewei-tunnel")
   - 點擊 "Configure"

3. **添加 Public Hostname**
   - 切換到 "Public Hostname" 標籤
   - 點擊 "Add a public hostname"

4. **填寫配置**
   ```
   Subdomain: bridge
   Domain: zhe-wei.net
   Path: (留空)
   
   Service:
   - Type: HTTP
   - URL: gateway:80
   ```

5. **儲存**
   - 點擊 "Save hostname"
   - Cloudflare 會自動推送配置到 Tunnel

6. **等待生效**
   - 通常 10-30 秒內生效
   - 可以在 tunnel 日誌中看到 "Updated to new configuration" 訊息

### 方法 2: cloudflared CLI (進階)

如果你有 cloudflared CLI 和 Tunnel 配置檔案：

```yaml
# config.yml
tunnel: <your-tunnel-id>
credentials-file: /path/to/credentials.json

ingress:
  - hostname: jarvis.zhe-wei.net
    service: http://gateway:80
  - hostname: dify.zhe-wei.net
    service: http://gateway:80
  - hostname: cms.zhe-wei.net
    service: http://gateway:80
  - hostname: vision.zhe-wei.net
    service: http://gateway:80
  - hostname: bridge.zhe-wei.net  # 新增
    service: http://gateway:80
  - service: http://gateway:80
```

然後執行：
```bash
cloudflared tunnel route dns <tunnel-name> bridge.zhe-wei.net
```

## 驗證設定

### 1. 檢查 DNS 記錄

```bash
# Windows
nslookup bridge.zhe-wei.net

# 應該看到 CNAME 指向 Cloudflare Tunnel
```

### 2. 檢查 Tunnel 日誌

```bash
docker compose logs -f tunnel

# 應該看到類似：
# INF Updated to new configuration config="{...\"bridge.zhe-wei.net\"...}"
```

### 3. 測試訪問

```bash
# 從外網測試
curl -I https://bridge.zhe-wei.net/health

# 應該返回 200 OK
```

## 完整的 Public Hostname 列表

設定完成後，你應該有以下域名：

| 域名 | 服務 | 端口 | 說明 |
|------|------|------|------|
| jarvis.zhe-wei.net | Brain Server | 8000 | 主要 AI 服務 |
| dify.zhe-wei.net | Dify | 8080 | AI 工作流平台 |
| cms.zhe-wei.net | CMS | 8020 | 營建管理系統 |
| vision.zhe-wei.net | Vision | 8030 | AI 視覺辨識 |
| **bridge.zhe-wei.net** | **Smart Bridge** | **8003** | **智慧對話橋接** |

## 故障排除

### DNS 未生效

**問題**：`ERR_NAME_NOT_RESOLVED`

**解決方案**：
1. 確認已在 Cloudflare Zero Trust 添加 hostname
2. 等待 DNS 傳播 (最多 5 分鐘)
3. 清除本地 DNS 快取：
   ```bash
   # Windows
   ipconfig /flushdns
   
   # Mac
   sudo dscacheutil -flushcache
   
   # Linux
   sudo systemd-resolve --flush-caches
   ```

### 502 Bad Gateway

**問題**：域名解析成功但無法連接服務

**檢查項目**：
1. Smart Bridge 是否運行：
   ```bash
   curl http://localhost:8003/health
   ```

2. Gateway 是否正常：
   ```bash
   docker compose ps gateway
   ```

3. Nginx 配置是否正確：
   ```bash
   docker compose exec gateway nginx -t
   ```

### Tunnel 未更新配置

**問題**：添加 hostname 後 tunnel 日誌沒有更新

**解決方案**：
1. 重啟 tunnel 容器：
   ```bash
   docker compose restart tunnel
   ```

2. 檢查 Cloudflare Token 是否有效

## 安全建議

1. **啟用 Access Policy** (選填)
   - 在 Cloudflare Zero Trust 中為 bridge.zhe-wei.net 設定存取控制
   - 限制特定 IP 或需要登入

2. **啟用 WAF 規則**
   - 防止 DDoS 攻擊
   - 限制請求速率

3. **監控流量**
   - 在 Cloudflare Analytics 查看流量統計
   - 設定異常告警

## 下一步

設定完成後：

1. ✅ 訪問 https://bridge.zhe-wei.net
2. ✅ 測試 WebSocket 連接
3. ✅ 測試兩階段生成 API
4. ✅ 測試 Ollama 學習控制

完成後你就可以從任何地方訪問 Smart Bridge 了！

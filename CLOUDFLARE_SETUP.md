# Cloudflare 完整配置指南

## ✅ 已配置資訊

- **Zone ID**: 8ba45d8905b38792b061bdcadac6dd39
- **API Token**: JS6dXN0-fQ4efSgUbunBTBMYM83bZKPND6872Rrc
- **域名**: zhe-wei.net
- **子域名**: www.zhe-wei.net

---

## 🚀 快速開始（3 步驟）

### 1️⃣ 設定 Cloudflare DDNS 自動更新
以**管理員身分**執行：
```batch
setup_cloudflare_ddns.bat
```

### 2️⃣ 啟動多代理服務
```batch
start_multi_agent.bat
```

### 3️⃣ 設定 Cloudflare SSL/TLS

登入 [Cloudflare Dashboard](https://dash.cloudflare.com/)：

1. 選擇你的網域 `zhe-wei.net`
2. 點擊 **SSL/TLS** → **Overview**
3. 加密模式選擇 **Flexible**
4. 點擊 **Save**

---

## 📋 詳細配置步驟

### 步驟 1: 設定環境變數

執行以下腳本設定系統環境變數：
```batch
set_cloudflare_env.bat
```

或手動設定：
```powershell
# 設定系統環境變數（需要管理員權限）
setx CLOUDFLARE_ZONE_ID "8ba45d8905b38792b061bdcadac6dd39" /M
setx CLOUDFLARE_API_TOKEN "JS6dXN0-fQ4efSgUbunBTBMYM83bZKPND6872Rrc" /M
setx CLOUDFLARE_DOMAIN "zhe-wei.net" /M
```

### 步驟 2: 設定工作排程器

執行自動設定腳本：
```batch
setup_cloudflare_ddns.bat
```

這會建立一個工作排程器任務，每 5 分鐘自動更新 DDNS。

### 步驟 3: 配置 Cloudflare DNS

#### 3.1 登入 Cloudflare
訪問 https://dash.cloudflare.com/ 並登入

#### 3.2 選擇網域
選擇 `zhe-wei.net`

#### 3.3 新增或編輯 DNS 記錄

**新增 CNAME 記錄（推薦）：**

| 設定項 | 值 |
|--------|-----|
| 類型 | CNAME |
| 名稱 | www |
| 目標 | zhuwei-tech.duckdns.org |
| TTL | Auto |
| Proxy 狀態 | 已代理（橙色雲朵）✅ |

**或新增 A 記錄：**

| 設定項 | 值 |
|--------|-----|
| 類型 | A |
| 名稱 | www |
| IPv4 地址 | 36.236.34.48（當前公網 IP）|
| TTL | Auto |
| Proxy 狀態 | 已代理（橙色雲朵）✅ |

### 步驟 4: 設定 SSL/TLS

1. 在 Cloudflare Dashboard 中，點擊 **SSL/TLS** → **Overview**
2. 加密模式選擇 **Flexible**
3. 點擊 **Save**

**為什麼選擇 Flexible？**
- Flexible 模式：Cloudflare 到你的服務器使用 HTTP（80/8001）
- Full 模式：需要你的服務器配置 HTTPS 證書
- Full (Strict) 模式：需要有效且受信任的 HTTPS 證書

### 步驟 5: 設定路由器埠轉發

參考 `ROUTER_PORT_FORWARD_GUIDE.md`

**使用 Cloudflare 後，路由器設定：**

| 外部埠 | 內部埠 | 內部 IP | 協議 |
|--------|--------|---------|------|
| 443 | 8001 | 192.168.0.207 | TCP |

或

| 外部埠 | 內部埠 | 內部 IP | 協議 |
|--------|--------|---------|------|
| 80 | 8001 | 192.168.0.207 | TCP |

### 步驟 6: 測試配置

```batch
# 測試本地服務
curl http://localhost:8001

# 測試 Cloudflare 域名
curl https://www.zhe-wei.net
```

或在瀏覽器中訪問：
- https://www.zhe-wei.net
- http://www.zhe-wei.net

---

## 🔧 修改子域名

如果需要使用不同的子域名（例如 `api.zhe-wei.net`），編輯 `cloudflare_ddns_update.ps1`：

```powershell
# 修改這行
$SUBDOMAIN = "api"  # 改為你想要的子域名
```

然後重新執行 `setup_cloudflare_ddns.bat`

---

## 📊 日誌檢查

### Cloudflare DDNS 日誌
```batch
type %USERPROFILE%\Cloudflare_DDNS_Log.txt
```

### 工作排程器日誌
1. 開啟「工作排程器」
2. 找到 `Cloudflare DDNS 每5分鐘更新` 任務
3. 右鍵 → 「內容」→ 「歷史記錄」

---

## ❓ 常見問題

### Q1: DDNS 更新失敗
**檢查:**
1. API Token 是否正確
2. Zone ID 是否正確
3. 網路連接是否正常
4. DNS 記錄名稱是否存在

### Q2: Cloudflare 顯示 5xx 錯誤
**可能原因:**
- 多代理服務未運行 → 執行 `start_multi_agent.bat`
- 路由器埠轉發未設定 → 參考 `ROUTER_PORT_FORWARD_GUIDE.md`
- 防火牆未開放埠 8001 → 執行 `setup_firewall_8001.bat`

### Q3: HTTPS 重定向失敗
**解決方法:**
1. 確認 SSL/TLS 模式為 Flexible
2. 檢查 DNS 記錄是否已代理（橙色雲朵）
3. 等待 DNS 傳播（通常 5-10 分鐘）

### Q4: 想要使用 Full SSL 模式
**需要的額外設定:**
1. 安裝並配置 Nginx 或 Apache
2. 配置 SSL 證書（使用 Let's Encrypt）
3. 將服務代理到 HTTPS (443)
4. Cloudflare SSL/TLS 模式改為 Full

---

## ✅ 完成檢查清單

- [ ] 環境變數已設定（CLOUDFLARE_ZONE_ID, API_TOKEN, DOMAIN）
- [ ] 工作排程器任務已建立（每 5 分鐘）
- [ ] DNS 記錄已新增/編輯（www.zhe-wei.net）
- [ ] DNS 記錄已啟用代理（橙色雲朵）
- [ ] SSL/TLS 模式設定為 Flexible
- [ ] 多代理服務正在運行（PORT=8001）
- [ ] 路由器埠轉發已設定（443 → 192.168.0.207:8001）
- [ ] 防火牆已開放埠 8001
- [ ] 外部可訪問 https://www.zhe-wei.net

---

## 🎯 網址總覽

配置完成後，你可以透過以下網址訪問：

- **HTTPS (推薦)**: https://www.zhe-wei.net
- **HTTP**: http://www.zhe-wei.net
- **直接 IP**: http://36.236.34.48:8001
- **DuckDNS**: http://zhuwei-tech.duckdns.org:8001

---

**最後更新**: 2026-02-09

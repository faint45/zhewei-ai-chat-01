# 路由器埠轉發設定指南

## 📋 你的網路資訊

- **本機 IP**: 192.168.0.207 (Wi-Fi)
- **公網 IP**: 36.236.34.48
- **服務埠**: 8001
- **DDNS 域名**: zhuwei-tech.duckdns.org

---

## 🔧 路由器設定步驟

### 步驟 1: 登入路由器

1. 開啟瀏覽器，訪問以下其中一個地址：
   - `http://192.168.0.1` (常見)
   - `http://192.168.1.1` (常見)
   - `http://192.168.1.254` (常見)

2. 輸入管理員帳號和密碼登入
   - 帳號: 通常是 `admin`
   - 密碼: 可能在路由器背面標籤上

### 步驟 2: 找到埠轉發設定

不同路由器的菜單名稱可能不同，尋找以下其中一個：
- **Port Forwarding** (埠轉發)
- **Virtual Server** (虛擬服務器)
- **NAT / NAT Port Mapping**
- **Gaming / Applications**

### 步驟 3: 新增埠轉發規則

#### 方式 A: 標準埠轉發（推薦）

| 選項 | 設定值 |
|------|--------|
| 服務名稱/描述 | MultiAgent 或築未科技AI |
| 外部埠 (External Port) | 8001 |
| 內部埠 (Internal Port) | 8001 |
| 內部 IP (Internal IP) | 192.168.0.207 |
| 協議 (Protocol) | TCP |
| 狀態 (Status) | 啟用/Enabled |

#### 方式 B: 透過 HTTP/HTTPS（如果使用 Cloudflare）

| 選項 | 設定值 |
|------|--------|
| 外部埠 | 80, 443 |
| 內部埠 | 8001 |
| 內部 IP | 192.168.0.207 |
| 協議 | TCP |
| 狀態 | 啟用 |

### 步驟 4: 儲存並重啟路由器

- 點擊「儲存」或「套用」
- 建議重啟路由器使設定生效

---

## 🧪 測試埠轉發

### 方法 1: 使用本機測試

```batch
# 測試本地服務
curl http://localhost:8001

# 測試透過公網 IP 訪問
curl http://36.236.34.48:8001
```

### 方法 2: 使用 DDNS 域名

```batch
# 測試透過 DDNS 訪問
curl http://zhuwei-tech.duckdns.org:8001
```

### 方法 3: 使用線上工具

訪問以下網站檢查埠是否開放：
- https://www.yougetsignal.com/tools/open-ports/
- 輸入 `zhuwei-tech.duckdns.org` 或 `36.236.34.48`
- 埠號: `8001`
- 應該顯示「Open」或「開啟」

---

## 🔍 常見路由器品牌設定

### ASUS 華碩
1. 登入: `http://192.168.50.1` 或 `http://router.asus.com`
2. Advanced Settings → WAN → Virtual Server/Port Forwarding
3. 新增規則

### D-Link 友訊
1. 登入: `http://192.168.0.1`
2. Advanced → Port Forwarding / Virtual Server
3. 新增規則

### TP-Link
1. 登入: `http://192.168.1.1`
2. Advanced → NAT Forwarding → Port Forwarding
3. 新增規則

### NETGEAR
1. 登入: `http://routerlogin.net`
2. Advanced → Advanced Setup → Port Forwarding/Port Triggering
3. 新增規則

### 小米路由器
1. 登入: `http://192.168.31.1`
2. 高級設置 → 端口轉發
3. 新增規則

---

## ❓ 常見問題

### Q1: 設定後仍無法從外部訪問
**可能原因:**
- 防火牆未開放埠 8001 → 執行 `setup_firewall_8001.bat`
- 多代理服務未運行 → 執行 `start_multi_agent.bat`
- 路由器設定未儲存或未重啟
- IP 地址變更（重新啟動路由器或網路中斷）

**解決方法:**
1. 檢查 DDNS 是否已更新
2. 重新確認本機 IP: `ipconfig`
3. 如果 IP 變更，更新路由器埠轉發設定

### Q2: 不知道路由器登入密碼
**解決方法:**
- 查看路由器背面標籤（預設帳號密碼）
- 重置路由器（長按重置按鈕 10 秒）
- 聯繫網路服務商

### Q3: 外部 IP 可能是 CGNAT
**症狀:** 埠轉發設定正確但仍無法從外部訪問

**解決方法:**
1. 檢查公網 IP 是否為私有 IP 段:
   - 100.64.0.0/10 (CGNAT)
   - 192.168.0.0/16
   - 10.0.0.0/8

2. 如果是 CGNAT，需要:
   - 聯繫網路服務商申請公網 IP
   - 或使用 Cloudflare Tunnel
   - 或使用 Ngrok 等隧道服務

---

## ✅ 完成檢查清單

- [ ] 防火牆已開放埠 8001
- [ ] 路由器已設定埠轉發 (8001 → 192.168.0.207:8001)
- [ ] 多代理服務正在運行
- [ ] 本機可訪問 http://localhost:8001
- [ ] 外部可訪問 http://zhuwei-tech.duckdns.org:8001
- [ ] DDNS 每 5 分鐘自動更新已設定

---

## 📞 技術支持

如需進一步協助，請提供:
1. 路由器品牌和型號
2. 錯誤訊息截圖
3. 測試結果（本機/外部）

---

**最後更新**: 2026-02-09

# DDNS 配置完成後的完整設置指南

## 📋 已完成
✅ DuckDNS Token 已配置
✅ 域名: zhuwei-tech.duckdns.org
✅ API Token: 553407dd-d7c9-40e9-be8a-bbdaa71c24b0

---

## 1️⃣ 設置每 5 分鐘自動更新 DDNS

### 創建工作排程器任務

1. **開啟工作排程器**
   - 按 `Win + R`，輸入 `taskschd.msc`，按 Enter

2. **建立基本工作**
   - 右側點擊「建立基本工作」
   - 名稱輸入: `DuckDNS 每5分鐘更新`
   - 描述: `自動更新 DuckDNS IP 地址`
   - 點擊「下一步」

3. **設定觸發程序**
   - 選擇「每日」
   - 開始時間: 設為當前時間
   - 點擊「下一步」

4. **設定動作**
   - 選擇「啟動程式」
   - 程式或腳本: `powershell.exe`
   - 新增引數:
     ```
     -ExecutionPolicy Bypass -WindowStyle Hidden -File "c:\Users\user\CodeBuddy\20260202120952\run-ddns-with-env.ps1"
     ```
   - 起始於: `c:\Users\user\CodeBuddy\20260202120952`
   - 點擊「下一步」→「完成」

5. **設定重複執行**
   - 在工作排程器中找到剛剛建立的工作
   - 右鍵 → 「內容」
   - 切換到「觸發程序」分頁
   - 選中觸發程序 → 點擊「編輯」
   - 勾選「重複工作間隔」
   - 設定為: `5 分鐘`
   - 持續時間: `無限期`
   - 點擊「確定」→「確定」

### 測試工作
- 右鍵該工作 → 「執行」
- 檢查日誌文件: `%USERPROFILE%\DDNS_Update_Log.txt`

---

## 2️⃣ 確認多代理系統運行

### 啟動多代理服務

開啟命令提示字元或 PowerShell，執行:

```powershell
cd c:\Users\user\CodeBuddy\20260202120952
$env:PORT = "8001"
.\venv\Scripts\python.exe main.py
```

**重要:**
- 此視窗必須保持開啟
- 服務運行後，本機可訪問: `http://localhost:8001`
- 如需後台運行，可使用 `start /B .\venv\Scripts\python.exe main.py`

### 驗證服務
```powershell
# 測試本地服務
curl http://localhost:8001

# 或使用瀏覽器訪問
start http://localhost:8001
```

---

## 3️⃣ 路由器埠轉發配置

### 步驟一：取得本機 IP
執行以下命令獲取本機 IP:
```powershell
ipconfig | findstr "IPv4"
```
記錄你的 IPv4 地址（例如: 192.168.1.100）

### 步驟二：登入路由器
- 在瀏覽器訪問路由器管理頁面（通常是: `192.168.1.1` 或 `192.168.0.1`）
- 輸入管理員帳號密碼登入

### 步驟三：設定埠轉發（Port Forwarding）

#### 方式 A: 標準 HTTP/HTTPS
| 外部埠 | 內部埠 | 內部 IP | 協議 |
|--------|--------|---------|------|
| 80 | 8000 | 192.168.x.x | TCP |
| 443 | 8000 | 192.168.x.x | TCP |

#### 方式 B: 直接使用應用埠（推薦）
| 外部埠 | 內部埠 | 內部 IP | 協議 |
|--------|--------|---------|------|
| 8001 | 8001 | 192.168.x.x | TCP |

### 步驟四：測試埠轉發
```powershell
# 檢查外部埠是否開放
# 訪問你的 DuckDNS 域名
curl http://zhuwei-tech.duckdns.org:8001
```

---

## 4️⃣ Cloudflare SSL 配置（可選）

### 設定 Cloudflare
如果你使用 Cloudflare 作為 DNS 代理:

1. **登入 Cloudflare**
   - 訪問 https://dash.cloudflare.com/
   - 選擇你的網域

2. **設定 DNS**
   - DNS → 新增 CNAME 記錄
   - 名稱: `zhuwei-tech` (或你想要的子域名)
   - 目標: `zhuwei-tech.duckdns.org`
   - 代理狀態: 已代理（橙色雲朵）

3. **設定 SSL/TLS**
   - SSL/TLS → 概覽
   - 加密模式選擇: **Flexible**
   - 這樣 Cloudflare 會處理 HTTPS，後端使用 HTTP

### 測試 HTTPS 訪問
- 瀏覽器訪問: `https://你的網域名稱`
- 應該會自動重定向到 HTTPS 並顯示安全鎖

---

## 5️⃣ 驗證完整部署

### 本地測試
```powershell
# 測試服務
curl http://localhost:8001
start http://localhost:8001
```

### 外部測試
```powershell
# 測試 DDNS 域名
curl http://zhuwei-tech.duckdns.org:8001

# 或在瀏覽器中訪問
start http://zhuwei-tech.duckdns.org:8001
```

### 檢查 DDNS 日誌
```powershell
notepad $env:USERPROFILE\DDNS_Update_Log.txt
```

---

## 📊 部署檢查清單

- [ ] DuckDNS Token 已配置
- [ ] 工作排程器已建立（每 5 分鐘）
- [ ] 多代理服務正在運行（PORT=8001）
- [ ] 本機可訪問 http://localhost:8001
- [ ] 路由器埠轉發已設定（8001 → 本機 IP）
- [ ] 外部可訪問 http://zhuwei-tech.duckdns.org:8001
- [ ] （可選）Cloudflare SSL 已設定（Flexible 模式）

---

## 🔧 常見問題排查

### 問題 1: 無法從外部訪問
- 檢查路由器埠轉發是否正確
- 確認防火牆允許端口 8001
- 驗證 DDNS 是否更新成功（查看日誌）

### 問題 2: DDNS 更新失敗
- 檢查 Token 是否正確
- 確認網絡連接正常
- 查看 DDNS 更新日誌

### 問題 3: 工作排程器未執行
- 確認已以管理員權限建立任務
- 檢查任務歷史記錄
- 手動執行任務測試

### 問題 4: Cloudflare SSL 錯誤
- 確認加密模式為 Flexible
- 檢查 DNS 記錄是否正確
- 等待 DNS 傳播（最多 24 小時）

---

## 📞 技術支持

如遇到問題，請檢查:
1. DDNS 日誌: `%USERPROFILE%\DDNS_Update_Log.txt`
2. 服務日誌: `system_health_report.json`
3. 工作排程器歷史記錄

---

**最後更新**: 2026-02-09

# DuckDNS 配置指南

## 第一步：註冊 DuckDNS

1. 打開瀏覽器，訪問：https://www.duckdns.org/
2. 使用以下方式之一註冊：
   - 使用 Google、GitHub 等社交帳號登錄
   - 使用 Email 註冊新帳號
3. 登錄後，您會看到 DuckDNS 控制面板

## 第二步：創建子域名

1. 在 DuckDNS 控制面板中，找到「Add a domain」區域
2. 輸入您的子域名（例如：`zhuwei-tech`）
3. 創建後，您的完整域名將是：`zhuwei-tech.duckdns.org`

## 第三步：獲取 Token

1. 在 DuckDNS 控制面板頂部，找到「Your Token」
2. 複製 Token（類似：`a1b2c3d4-e5f6-7890-abcd-ef1234567890`）
3. **重要**：妥善保管 Token，不要洩露給他人

## 第四步：配置本地更新腳本

打開文件：`ddns_update.bat`

找到以下兩行並替換為您的實際值：

```batch
set DOMAIN=zhuwei-tech      :: 您的子域名
set TOKEN=your-token-here    :: 您的 DuckDNS Token
```

**示例**：
```batch
set DOMAIN=zhuwei-tech
set TOKEN=a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

## 第五步：測試 DDNS 更新

雙擊運行：`ddns_update.bat`

如果看到以下輸出，說明配置成功：
```
✅ DDNS 更新成功！
DuckDNS 響應: OK

您的網站現在可以通過以下地址訪問：
  網站首頁:  http://zhuwei-tech.duckdns.org:8000
  AI 對話:    http://zhuwei-tech.duckdns.org:8000/chat
  管理後台:  http://zhuwei-tech.duckdns.org:8000/admin
  聯繫我們:  http://zhuwei-tech.duckdns.org:8000/contact
  遠程控制:  http://zhuwei-tech.duckdns.org:8005
```

## 第六步：配置路由器端口轉發

### 方法1：使用配置腳本

運行：`get_network_info.bat`

腳本會顯示：
- 您的本機 IP 地址（如：192.168.1.100）
- 路由器地址（如：192.168.1.1）
- 公網 IP 地址
- 端口轉發配置表

### 方法2：手動配置

1. 登錄路由器管理頁面（通常是 192.168.1.1）
2. 找到「端口轉發」或「虛擬服務器」設置
3. 添加以下規則：

| 外部端口 | 內部端口 | 內部 IP 地址 | 協議 | 描述 |
|---------|---------|-------------|------|------|
| 8000 | 8000 | 192.168.1.100 | TCP | 網站服務器 |
| 8005 | 8005 | 192.168.1.100 | TCP | 遠程控制 |

**注意**：將 `192.168.1.100` 替換為您的實際本機 IP

## 第七步：測試外部訪問

### 1. 測試本機訪問
```
http://localhost:8000
```

### 2. 測試內網訪問
```
http://192.168.1.100:8000
```

### 3. 測試外網訪問（使用 DDNS 域名）
```
http://zhuwei-tech.duckdns.org:8000
```

### 4. 測試外網訪問（使用公網 IP）
```
http://123.45.67.89:8000
```

## 第八步：設置定時自動更新

運行 `ddns_update.bat` 時，系統會詢問是否創建定時任務。

選擇「Y」，腳本會自動創建每小時運行一次的任務。

手動創建定時任務：
```batch
schtasks /Create /TN "築未科技DDNS更新" /TR "ddns_update.bat" /SC HOURLY /F
```

查看任務：
```batch
schtasks /Query /TN "築未科技DDNS更新"
```

刪除任務：
```batch
schtasks /Delete /TN "築未科技DDNS更新" /F
```

---

## 常見問題

### Q: DuckDNS 更新失敗，響應是 "KO"

**原因**：
- Token 錯誤
- 子域名不存在
- 網絡連接問題

**解決**：
1. 檢查 Token 是否正確複製
2. 確認子域名已在 DuckDNS 創建
3. 檢查網絡連接

### Q: 無法通過外網訪問

**檢查清單**：
1. 本地服務是否運行？運行 `test_all.py`
2. 端口轉發是否正確配置？
3. 防火牆是否允許端口訪問？
4. DDNS 是否更新成功？

### Q: 如何確保 DDNS 一直更新？

**解決**：
- 創建定時任務（每小時運行）
- 或將 `ddns_update.bat` 添加到啟動項
- 或使用 DuckDNS 提供的其他客戶端

### Q: 可以使用其他 DDNS 服務嗎？

可以！常見的 DDNS 服務：
- DuckDNS（免費，推薦）
- No-IP（免費/付費）
- DynDNS（付費）
- Namecheap（付費）

---

## 安全建議

1. **不要在公開場合分享 Token**
   - Token 相當於您的密碼
   - 任何人都可以用 Token 修改您的域名

2. **使用強密碼保護管理後台**
   - 避免使用默認密碼
   - 定期更換密碼

3. **配置防火牆規則**
   ```batch
   netsh advfirewall firewall add rule name="築未科技-網站" dir=in action=allow protocol=TCP localport=8000
   netsh advfirewall firewall add rule name="築未科技-遠程" dir=in action=allow protocol=TCP localport=8005
   ```

4. **限制管理後台訪問**
   - 只允許特定 IP 訪問 /admin
   - 在防火牆中阻止不明訪問

---

## 部署完成後的完整 URL

假設您的 DuckDNS 子域名是 `zhuwei-tech`：

| 服務 | URL |
|------|-----|
| 網站首頁 | http://zhuwei-tech.duckdns.org:8000 |
| AI 對話 | http://zhuwei-tech.duckdns.org:8000/chat |
| 管理後台 | http://zhuwei-tech.duckdns.org:8000/admin |
| 聯繫我們 | http://zhuwei-tech.duckdns.org:8000/contact |
| 遠程控制 | http://zhuwei-tech.duckdns.org:8005 |

恭喜！您現在已經擁有自己的域名，可以隨時隨地訪問您的築未科技系統！🎉

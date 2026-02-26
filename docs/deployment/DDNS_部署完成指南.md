# DDNS 部署完成指南

## 🎉 恭喜！DDNS 配置功能已就緒

您現在可以使用築未科技系統的 DDNS 自動配置功能了！

---

## 🚀 快速開始（3 步完成）

### 第一步：註冊 DuckDNS

1. 打開瀏覽器，訪問：https://www.duckdns.org/
2. 登錄或註冊帳號（支持 Google、GitHub 等社交帳號）
3. 創建一個子域名（例如：`zhuwei-tech`）
4. 在頁面頂部複製您的 Token

### 第二步：運行自動配置

雙擊運行：

```batch
setup_ddns.bat
```

系統會引導您完成：
- ✅ 檢測本機和公網 IP
- ✅ 輸入 DuckDNS 子域名和 Token
- ✅ 測試 DDNS 連接
- ✅ 自動更新配置文件
- ✅ 創建定時更新任務（可選）
- ✅ 顯示完整的訪問地址

### 第三步：配置路由器端口轉發

運行：

```batch
get_network_info.bat
```

按照顯示的配置表，在路由器中設置端口轉發：
- 外部端口 8000 → 內部端口 8000 → 本機 IP
- 外部端口 8005 → 內部端口 8005 → 本機 IP

---

## 📋 完整部署流程

### 方案 A：使用自動配置（推薦）

```batch
1. setup_ddns.bat
   - 按照提示輸入子域名和 Token
   - 自動完成所有配置

2. get_network_info.bat
   - 獲取路由器配置信息

3. 配置路由器端口轉發
   - 在路由器管理頁面添加規則

4. 測試訪問
   - http://yourdomain.duckdns.org:8000
```

### 方案 B：手動配置

```batch
1. 註冊 DuckDNS 帳號
   - https://www.duckdns.org/

2. 編輯 ddns_update.bat
   - 修改 DOMAIN 和 TOKEN 變量

3. 運行更新腳本
   - ddns_update.bat

4. 配置端口轉發
   - get_network_info.bat

5. 測試訪問
   - http://yourdomain.duckdns.org:8000
```

---

## 🛠️ 可用工具

| 工具 | 功能 | 使用場景 |
|------|------|----------|
| **setup_ddns.bat** | DDNS 自動配置向導 | 首次配置，自動化 |
| **ddns_update.bat** | 手動更新 DDNS | 手動更新 IP |
| **get_network_info.bat** | 網絡配置信息 | 端口轉發設置 |
| **快速部署向導.bat** | 部署方案選擇 | 選擇最適合的方案 |

---

## 📖 詳細文檔

- **duckdns_setup_guide.md** - DuckDNS 詳細配置指南
- **網絡部署指南.md** - 三種部署方案詳細說明
- **網絡部署總結.md** - 部署方案總結和對比

---

## 🌐 部署後訪問地址

假設您的 DuckDNS 子域名是 `zhuwei-tech`：

### 本地訪問
```
http://localhost:8000
http://192.168.1.100:8000
```

### 內網訪問
```
http://192.168.1.100:8000
```

### 外網訪問（使用 DDNS 域名）
```
http://zhuwei-tech.duckdns.org:8000
```

### 外網訪問（使用公網 IP）
```
http://123.45.67.89:8000
```

---

## 📊 完整服務訪問地址

| 服務 | 本地地址 | DDNS 域名 |
|------|---------|-----------|
| 網站首頁 | http://localhost:8000 | http://zhuwei-tech.duckdns.org:8000 |
| AI 對話 | http://localhost:8000/chat | http://zhuwei-tech.duckdns.org:8000/chat |
| 管理後台 | http://localhost:8000/admin | http://zhuwei-tech.duckdns.org:8000/admin |
| 聯繫我們 | http://localhost:8000/contact | http://zhuwei-tech.duckdns.org:8000/contact |
| 遠程控制 | http://localhost:8005 | http://zhuwei-tech.duckdns.org:8005 |

---

## 🔧 故障排除

### 問題：DDNS 更新失敗

**檢查清單**：
1. ✅ Token 是否正確？
2. ✅ 子域名是否存在？
3. ✅ 網絡連接是否正常？
4. ✅ curl 命令是否可用？

**解決方案**：
- 重新運行 `setup_ddns.bat`
- 檢查 DuckDNS 帳號設置
- 查看腳本輸出的錯誤信息

### 問題：無法從外網訪問

**檢查清單**：
1. ✅ 本地服務是否運行？運行 `test_all.py`
2. ✅ DDNS 是否更新成功？
3. ✅ 路由器端口轉發是否正確？
4. ✅ 防火牆是否允許端口？

**解決方案**：
```batch
# 測試本地服務
python test_all.py

# 檢查端口轉發配置
get_network_info.bat

# 手動更新 DDNS
ddns_update.bat
```

### 問題：端口被占用

**解決方案**：
```batch
# 查找占用端口的進程
netstat -ano | findstr ":8000"

# 殺死進程（將 PID 替換為實際值）
taskkill /F /PID [PID]

# 或停止服務
停止所有服務.bat
```

---

## 🔐 安全建議

### 1. 保護 Token
- ⚠️ 不要在公開場合分享 Token
- ⚠️ 不要提交到 Git 倉庫
- ⚠️ 定期更換 Token

### 2. 使用強密碼
- 管理後台必須使用強密碼
- 定期更換密碼
- 不要使用默認密碼

### 3. 配置防火牆
```batch
# 添加防火牆規則
netsh advfirewall firewall add rule name="築未科技-網站" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="築未科技-遠程" dir=in action=allow protocol=TCP localport=8005
```

### 4. 限制管理後台訪問
- 只允許特定 IP 訪問 `/admin`
- 使用 VPN 訪問管理後台
- 配置 IP 白名單

### 5. 使用 HTTPS
```bash
# 安裝 Let's Encrypt 免費 SSL 證書
# 或使用 Ngrok 自動提供的 HTTPS
```

---

## 📝 維護建議

### 定期檢查
- ✅ 每週檢查 DDNS 更新狀態
- ✅ 每月檢查路由器配置
- ✅ 定期更新系統和依賴

### 監控日誌
- 查看 DDNS 更新日誌
- 監控服務運行狀態
- 設置異常告警

### 備份配置
- 備份 DuckDNS 配置
- 保存路由器設置
- 記錄重要的訪問地址

---

## 🎉 部署完成清單

部署前確認：
- [ ] 已註冊 DuckDNS 帳號
- [ ] 已創建子域名
- [ ] 已獲取 Token
- [ ] 本地服務正常運行

配置階段：
- [ ] 運行 `setup_ddns.bat` 完成配置
- [ ] DDNS 更新成功（響應 OK）
- [ ] 已創建定時更新任務
- [ ] 已配置路由器端口轉發
- [ ] 防火牆規則已添加

測試階段：
- [ ] 本機訪問正常
- [ ] 內網訪問正常
- [ ] 外網訪問正常（DDNS 域名）
- [ ] 外網訪問正常（公網 IP）
- [ ] 所有功能正常測試

安全設置：
- [ ] 使用強密碼
- [ ] 防火牆規則已配置
- [ ] 管理後台訪問已限制
- [ ] SSL/HTTPS 已配置

---

## 📞 獲取幫助

### 測試系統
```bash
python test_all.py
```

### 查看文檔
- `duckdns_setup_guide.md` - 詳細配置指南
- `網絡部署指南.md` - 完整部署指南
- `快速參考.txt` - 快速參考

### 運行向導
```batch
快速部署向導.bat
```

---

## 🎯 開始部署

現在您可以開始配置 DDNS 了！

### 快速開始（3 步驟）

1. **註冊 DuckDNS**
   ```
   https://www.duckdns.org/
   ```

2. **運行自動配置**
   ```batch
   setup_ddns.bat
   ```

3. **配置端口轉發**
   ```batch
   get_network_info.bat
   ```

### 完成後訪問

```
http://yourdomain.duckdns.org:8000
```

---

**築未科技 © 2025 | 版本 2.0.0 | 系統狀態：✅ 正常**

祝您部署成功！🚀

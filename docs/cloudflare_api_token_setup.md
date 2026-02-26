# 🔑 Cloudflare API Token 完整設定指南

## 問題說明

當前的 API Token 缺少以下權限：
- ❌ Account 讀取權限（無法取得 Account ID）
- ❌ Zone 讀取權限（無法從 Zone 取得 Account ID）

這導致無法通過 API 自動添加域名到 Tunnel。

---

## ✅ 解決方案：創建新的 API Token

### 步驟 1：訪問 API Token 頁面

訪問：https://dash.cloudflare.com/profile/api-tokens

### 步驟 2：創建自定義 Token

點擊 **"Create Token"** → 選擇 **"Create Custom Token"**

### 步驟 3：設定 Token 名稱

```
Token name: Tunnel Management Full Access
```

### 步驟 4：設定權限（重要！）

在 **Permissions** 區域，點擊 **"+ Add more"** 添加以下 3 個權限：

#### 權限 1：Account - Cloudflare Tunnel - Edit
```
Account | Cloudflare Tunnel | Edit
```

#### 權限 2：Account - Account Settings - Read
```
Account | Account Settings | Read
```

#### 權限 3：Zone - Zone - Read
```
Zone | Zone | Read
```

### 步驟 5：設定 Account Resources

```
Account Resources:
  Include | All accounts
```

### 步驟 6：設定 Zone Resources

```
Zone Resources:
  Include | All zones
```

### 步驟 7：Client IP Address Filtering（可選）

可以點擊 **"Use my IP"** 限制只有你的 IP 可以使用此 token，增加安全性。

或留空允許任何 IP 使用。

### 步驟 8：TTL（有效期）

建議設定：
- **1 day** - 如果只是臨時使用
- **1 week** - 如果需要多次使用
- **Custom** - 自定義時間

### 步驟 9：檢查摘要

點擊 **"Continue to summary"**，確認權限設定：

```
✅ Account - Cloudflare Tunnel - Edit
✅ Account - Account Settings - Read  
✅ Zone - Zone - Read
```

### 步驟 10：創建 Token

點擊 **"Create Token"**

### 步驟 11：複製 Token

**重要**：Token 只會顯示一次！

複製完整的 Token（通常很長，類似：`abcdef1234567890...`）

---

## 🎯 使用新 Token

### 方法 1：直接提供給我

複製 Token 後，直接貼給我，我會立即使用它自動添加所有域名。

### 方法 2：使用腳本

```bash
# 設定環境變數
$env:CLOUDFLARE_API_TOKEN="your_new_token_here"

# 運行同步腳本
python scripts/sync_cloudflare.py
```

---

## 📋 權限對照表

| 權限 | 用途 | 必須 |
|------|------|------|
| Account - Cloudflare Tunnel - Edit | 編輯 Tunnel 配置 | ✅ 是 |
| Account - Account Settings - Read | 取得 Account ID | ✅ 是 |
| Zone - Zone - Read | 從 Zone 取得 Account ID | ✅ 是 |

---

## ❌ 常見錯誤

### 錯誤 1：只有 Tunnel Edit 權限

```
❌ Account - Cloudflare Tunnel - Edit
❌ 缺少 Account Settings Read
❌ 缺少 Zone Read
```

**結果**：無法取得 Account ID，無法自動添加域名

### 錯誤 2：只有 Read 權限

```
❌ Account - Cloudflare Tunnel - Read
✅ Account - Account Settings - Read
✅ Zone - Zone - Read
```

**結果**：可以讀取但無法編輯 Tunnel 配置

---

## ✅ 正確的權限設定

```
✅ Account - Cloudflare Tunnel - Edit
✅ Account - Account Settings - Read
✅ Zone - Zone - Read
```

**結果**：可以自動添加域名！

---

## 🔒 安全建議

1. **使用 IP 限制**：限制只有你的 IP 可以使用
2. **設定短期有效期**：例如 1 天或 1 週
3. **用完後刪除**：不需要時立即刪除 Token
4. **不要分享**：Token 等同於你的帳號權限

---

## 🆘 如果還是不行

如果創建新 Token 後還是無法自動添加，可能的原因：

1. **Account ID 問題**：某些帳號結構特殊
2. **API 限制**：Cloudflare 可能有 API 調用限制
3. **權限延遲**：新 Token 需要幾分鐘生效

**解決方案**：
- 等待 5-10 分鐘後重試
- 或使用手動方式添加域名（只需 5 分鐘）

---

## 📞 需要幫助？

創建好新 Token 後，直接貼給我，我會立即：
1. ✅ 驗證 Token 權限
2. ✅ 自動添加所有 8 個域名
3. ✅ 驗證域名生效
4. ✅ 測試所有服務

準備好了嗎？現在就去創建新 Token 吧！🚀

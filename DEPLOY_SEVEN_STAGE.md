# 七階段系統網路部署指南

## 快速部署

### 方式 1: Railway（推薦）

**特點**:
- ✅ 免費開始，按用量付費
- ✅ 支持長時間運行
- ✅ 自動 HTTPS
- ✅ 易於配置環境變量

**部署步驟**:

1. **安裝 Railway CLI**
   ```bash
   npm install -g @railway/cli
   ```

2. **登錄 Railway**
   ```bash
   railway login
   ```

3. **部署**
   ```bash
   # 運行部署腳本
   deploy_to_railway.bat

   # 或手動執行
   railway init
   railway up
   ```

4. **配置環境變量**
   在 Railway Dashboard 中添加：
   - `GEMINI_API_KEY=AIzaSyDthmqwPFbVvSECltanWKOo1O8p-KP_Rt0`
   - `ANTHROPIC_API_KEY=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`
   - `CURSOR_API_KEY=key_9c4a95d3000562a24a35048849eac00524b44ea547657d2b9dc2a19c4854f994`
   - `QIANWEN_API_KEY=sk-ab8f191deb8744618119023a57bde3dd`

5. **獲取部署 URL**
   ```bash
   railway domain
   ```

6. **測試部署**
   ```bash
   curl https://your-app-name.railway.app/health
   ```

---

### 方式 2: Vercel

**特點**:
- ✅ 全球 CDN
- ✅ 免費計劃
- ⚠️ 有執行時間限制（10秒免費版）

**部署步驟**:

1. **安裝 Vercel CLI**
   ```bash
   npm i -g vercel
   ```

2. **部署**
   ```bash
   vercel
   ```

3. **配置環境變量**
   在 Vercel Dashboard > Settings > Environment Variables 中添加所有 API 密鑰

---

### 方式 3: 腾讯云 CloudBase

**特點**:
- ✅ 國內訪問快
- ✅ 支持微信小程序
- ✅ 免費額度

**部署步驟**:

1. **安裝 CloudBase CLI**
   ```bash
   npm install -g @cloudbase/cli
   ```

2. **登錄**
   ```bash
   tcb login
   ```

3. **部署**
   ```bash
   tcb deploy
   ```

---

### 方式 4: Cloudflare Pages（免費）

**特點**:
- ✅ 完全免費
- ✅ 全球 CDN
- ⚠️ 主要適合靜態網站

**部署步驟**:

1. 訪問 https://pages.cloudflare.com/
2. 創建新項目
3. 上傳文件或連接 GitHub
4. 配置環境變量

---

## 本地部署遠程訪問

如果您已經有公網 IP 或 DDNS，可以本地運行服務：

1. **啟動 Ollama 服務**（在一個窗口）
   ```bash
   啟動_ollama_服務.bat
   ```

2. **啟動七階段 API**（在另一個窗口）
   ```bash
   啟動_七階段_API.bat
   ```

3. **配置端口轉發**
   - 路由器: 將 8006 端口轉發到內網 IP
   - 或使用 Cloudflare Tunnel / ngrok

4. **遠程訪問**
   - 本地: http://localhost:8006
   - 遠程: http://your-ddns-domain:8006

---

## 部署後測試

### 健康檢查
```bash
curl https://your-domain.com/health
```

### 執行任務
```bash
curl -X POST https://your-domain.com/execute \
  -H "Content-Type: application/json" \
  -d '{"input": "創建網頁", "priority": "high"}'
```

### API 文檔
訪問: https://your-domain.com/docs

---

## 注意事項

### Ollama 服務限制

**Ollama 無法部署到云端**，原因：
- 需要 GPU 加速（RTX 4060 Ti）
- 模型文件太大（幾 GB）
- 不適合 serverless 環境

**解決方案**:
1. 本地運行 Ollama 服務
2. 遠程部署主系統到 Railway
3. 系統通過 API 調用本地 Ollama（需要開放端口）
4. 或使用云端替換方案（如 DeepSeek API）

### 環境變量安全

部署時請注意：
- ✅ 不要將 API 密鑰提交到 Git
- ✅ 使用部署平台的環境變量功能
- ✅ 定期輪換 API 密鑰

### 成本控制

**Railway 免費計劃**:
- $5/月 免費額度
- 按用量付費
- 適合個人開發

**其他平台**:
- Vercel: 100GB 帶寬/月（免費）
- CloudBase: 免費套餐 + 付費升級
- Cloudflare Pages: 完全免費

---

## 推薦部署方案

### 開發測試
- 本地運行 + ngrok/Cloudflare Tunnel

### 個人項目
- Railway（推薦）
- Vercel

### 企業應用
- Railway 付費版
- 腾讯云 CloudBase

### 完全免費
- Cloudflare Pages
- Render

---

## 常見問題

**Q: 部署後 API 無法訪問？**
A: 檢查防火牆設置和環境變量配置

**Q: Ollama 連接失敗？**
A: Ollama 必須本地運行，檢查 `OLLAMA_API_BASE` 配置

**Q: 執行超時？**
A: Railway 長時間運行，Vercel 有 10 秒限制

**Q: 如何獲取公網地址？**
A: 使用 DDNS（如 DuckDNS）或部署到 Railway

---

## 總結

| 平台 | 適用場景 | 成本 | 推薦度 |
|------|---------|------|--------|
| Railway | 長時間運行 | 按用量 | ⭐⭐⭐⭐⭐ |
| Vercel | 短時間 API | 免費套餐 | ⭐⭐⭐ |
| CloudBase | 微信小程序 | 免費額度 | ⭐⭐⭐⭐ |
| Cloudflare Pages | 靜態網站 | 完全免費 | ⭐⭐⭐ |

**推薦**: 使用 Railway 部署，運行 `deploy_to_railway.bat`

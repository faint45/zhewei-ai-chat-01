# Railway 部署完整指南

## GitHub 倉庫信息

**倉庫地址**: https://github.com/faint45/zhewei-ai-chat-01.git
**分支**: main

---

## 部署到 Railway

### 步驟 1: 創建 Railway 項目

1. **訪問 Railway**: https://railway.app/new
2. **登錄帳號**（使用 GitHub 登錄最方便）
3. **點擊 "New Project"**
4. **選擇 "Deploy from GitHub repo"**
5. **在搜索框輸入**: `zhewei-ai-chat-01`
6. **選擇您的倉庫並點擊 "Import"**

---

### 步驟 2: 配置構建設置

在項目頁面點擊 "Settings" 或直接在部署頁面配置：

**Build Command**:
```bash
pip install -r requirements_seven_stage.txt
```

**Start Command**:
```bash
uvicorn seven_stage_api:app --host 0.0.0.0 --port $PORT
```

---

### 步驟 3: 配置環境變量

在項目 > Variables 中添加以下環境變量：

| 變量名稱 | 值 | 說明 |
|------------|------|--------|
| `GEMINI_API_KEY` | `AIzaSyDthmqwPFbVvSECltanWKOo1O8p-KP_Rt0` | 總指揮官 - Gemini Pro |
| `ANTHROPIC_API_KEY` | `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` | 首席開發官 - Claude Pro |
| `CURSOR_API_KEY` | `key_9c4a95d3000562a24a35048849eac00524b44ea547657d2b9dc2a19c4854f994` | 實體執行員 - Cursor Pro |
| `QIANWEN_API_KEY` | `sk-ab8f191deb8744618119023a57bde3dd` | 情報與驗證 - 通義千問 |
| `API_PORT` | `8006` | API 端口 |
| `PYTHONUNBUFFERED` | `1` | Python 輸出緩衝 |

**添加方式**:
1. 點擊 "New Variable"
2. 輸入變量名稱和值
3. 點擊 "Create Variable"
4. 重複直到所有變量添加完成

---

### 步驟 4: 部署

1. **返回 Deploy 標籤頁**
2. **點擊 "Deploy Now"** 按鈕
3. **等待部署完成**（約 2-3 分鐘）
4. **查看日誌**以確認無錯誤

---

### 步驟 5: 獲取部署 URL

部署成功後，Railway 會提供：
- **應用 URL**: `https://your-app-name-production.up.railway.app`

例如：`https://seven-stage-system-production.up.railway.app`

---

## 部署後測試

### 1. 健康檢查

```bash
curl https://your-app-name-production.up.railway.app/health
```

預期回應：
```json
{
  "status": "healthy",
  "system": "Seven-Stage Command Operations System",
  ...
}
```

### 2. 執行任務

```bash
curl -X POST https://your-app-name-production.up.railway.app/execute \
  -H "Content-Type: application/json" \
  -d '{"input": "創建網頁", "priority": "high"}'
```

### 3. 訪問 API 文檔

瀏覽器訪問：`https://your-app-name-production.up.railway.app/docs`

Swagger UI 界面可以直接測試所有 API 端點。

---

## 配置域名（可選）

如果 Railway 默認域名不夠好記憶，可以配置自定義域名：

1. **在項目頁面點擊 "Settings"**
2. **點擊 "Domains"**
3. **添加您的域名**
4. **配置 DNS** 指向 Railway 提供的 CNAME

---

## 注意事項

### Ollama 服務

**重要**: Ollama 無法在 Railway 運行，原因：
- 需要 GPU 支持的本地環境
- 模型文件太大
- 不適合 serverless 環境

**解決方案**:
1. 部署後系統會自動使用模擬模式
2. 或者替換為云端 API（如 DeepSeek）
3. 或本地運行 Ollama，遠程調用（需要開放端口）

### 成本控制

Railway 免費額度：$5/月

- 免費足夠開發測試
- 生產環境建議升級付費計劃
- 按實際使用量計費

### 日誌監控

在 Railway Dashboard 查看實時日誌：
- 點擊�項目
- 選擇 "View logs"
- 查看請求和錯誤日誌

---

## 故障排除

### 部署失敗

**問題**: 構建錯誤

**解決**:
1. 檢查 Start Command 是否正確
2. 確認 requirements_seven_stage.txt 包含所有依賴
3. 查看日誌找出具體錯誤

### API 無法訪問

**問題**: 404 或 500 錯誤

**解決**:
1. 確認環境變量已配置
2. 檢查 API 密鑰是否正確
3. 查看日誌確認服務啟動

### 環境變量未生效

**問題**: API 報錯誤密鑰

**解決**:
1. 重新部署一次
2. 或手動重啟部署

---

## 快速命令參考

### 使用 Railway CLI（可選）

如果已安裝 Railway CLI 且保持登錄：

```bash
# 連接現有項目
railway link

# 添加環境變量
railway variables set GEMINI_API_KEY=AIzaSyDthmqwPFbVvSECltanWKOo1O8p-KP_Rt0
railway variables set ANTHROPIC_API_KEY=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
railway variables set CURSOR_API_KEY=key_9c4a95d3000562a24a35048849eac00524b44ea547657d2b9dc2a19c4854f994
railway variables set QIANWEN_API_KEY=sk-ab8f191deb8744618119023a57bde3dd
railway variables set API_PORT=8006
railway variables set PYTHONUNBUFFERED=1

# 上傳並部署
railway up

# 查看日誌
railway logs

# 查看域名
railway domain
```

---

## 總結

部署到 Railway 後，您的七階段系統將：

✅ **24/7 在線運行**
✅ **自動 HTTPS**
✅ **全球 CDN 加速**
✅ **自動擴容**
✅ **實時日誌監控**

**開始部署**: https://railway.app/new

選擇 `zhewei-ai-chat-01` 倉庫，按照上述步驟配置即可！

---

**需要幫助?**
查看更多文檔：`DEPLOY_SEVEN_STAGE.md`

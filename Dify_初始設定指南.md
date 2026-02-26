# Dify 初始設定指南

根據測試結果，需要完成 Dify 的初始設定以啟用 `dify-mcp` 和 `weaviate-mcp`。

---

## 🎯 目標

1. ✅ 登入 Dify Web UI
2. ✅ 建立第一個應用
3. ✅ 取得 API Key
4. ✅ 建立知識庫（啟用 Weaviate）
5. ✅ 更新 `.cursor/mcp.json` 配置

---

## 📝 步驟 1：登入 Dify

### 1.1 開啟 Dify Web UI
```
http://localhost:8080
```

### 1.2 首次登入
如果是首次使用，需要建立管理員帳號：
- 輸入 Email
- 設定密碼
- 建立帳號

### 1.3 確認登入成功
應該會看到 Dify 的主控台

---

## 📝 步驟 2：建立第一個應用

### 2.1 點擊「建立應用」
在 Dify 主控台，點擊「建立應用」或「Create App」

### 2.2 選擇應用類型
建議選擇：
- **聊天助手（Chat Assistant）** - 適合對話場景
- 或 **Agent** - 適合工具呼叫場景

### 2.3 設定應用名稱
例如：
```
應用名稱：築未科技 AI 助手
描述：整合 MCP 工具的 AI 助手
```

### 2.4 選擇 AI 模型
- 如果已設定 Ollama：選擇 Ollama 模型
- 或使用 Dify 預設的模型

### 2.5 儲存應用

---

## 📝 步驟 3：取得 API Key

### 3.1 進入應用設定
點擊剛建立的應用 → 設定（Settings）

### 3.2 找到 API Access
在左側選單找到「API Access」或「API 存取」

### 3.3 建立 API Key
1. 點擊「建立 API Key」或「Create API Key」
2. 輸入名稱（例如：`MCP Integration`）
3. 複製生成的 API Key（格式：`app-xxxxxxxxxxxxxx`）

**重要：** API Key 只會顯示一次，請立即複製！

---

## 📝 步驟 4：建立知識庫（啟用 Weaviate）

### 4.1 進入知識庫頁面
在 Dify 主控台，點擊「知識庫」或「Knowledge」

### 4.2 建立新知識庫
1. 點擊「建立知識庫」
2. 輸入名稱（例如：`築未科技知識庫`）
3. 選擇向量資料庫：**Weaviate**（應該是預設）

### 4.3 上傳文件（可選）
可以上傳一些測試文件，例如：
- PDF 文件
- Markdown 文件
- 文字檔案

### 4.4 等待索引完成
Dify 會自動將文件切分並建立向量索引到 Weaviate

### 4.5 驗證 Weaviate 類別
建立知識庫後，再次測試：
```bash
curl http://localhost:8080/v1/schema
```
應該會看到新建立的類別（例如：`Dataset_xxxxx`）

---

## 📝 步驟 5：更新 MCP 配置

### 5.1 開啟 `.cursor/mcp.json`

### 5.2 更新 `dify-mcp` 的 API Key
```json
{
  "dify-mcp": {
    "command": "D:/zhe-wei-tech/Jarvis_Training/.venv312/Scripts/python.exe",
    "args": ["D:/zhe-wei-tech/mcp_servers/dify_mcp.py"],
    "env": {
      "DIFY_API_URL": "http://localhost:8080/v1",
      "DIFY_API_KEY": "app-xxxxxxxxxxxxxx"  // 替換為實際的 API Key
    }
  }
}
```

### 5.3 儲存檔案

### 5.4 重新載入 Cursor MCP
```
Cursor → Settings → Features → MCP → Reload
```

---

## ✅ 驗證設定

### 測試 dify-mcp
在 Cursor Composer 中執行：
```
用 dify-mcp 取得應用參數
```

**預期結果：** 應該回傳應用的參數設定，不再是 401 錯誤

### 測試 dify-mcp 對話
```
用 dify-mcp 與 AI 對話：你好，請介紹一下自己
```

**預期結果：** 應該回傳 AI 的回應

### 測試 weaviate-mcp
```
用 weaviate-mcp 列出所有類別
```

**預期結果：** 應該顯示知識庫建立的類別（例如：`Dataset_xxxxx`）

### 測試 weaviate-mcp 搜尋
```
用 weaviate-mcp 在 [ClassName] 中搜尋「測試」
```

**預期結果：** 應該回傳搜尋結果

---

## 🔧 常見問題

### 問題 1: Dify 無法開啟 http://localhost:8080
**解決方法：**
```bash
# 確認 Dify 容器正在運行
docker ps | findstr dify

# 如果沒有運行，啟動容器
docker start docker-web-1 docker-api-1 docker-worker-1
```

### 問題 2: 忘記 Dify 管理員密碼
**解決方法：**
```bash
# 重設密碼（需進入 PostgreSQL）
docker exec -it docker-db_postgres-1 psql -U postgres -d dify

# 查詢帳號
SELECT id, email FROM accounts;

# 重設密碼（需使用 bcrypt hash）
# 建議重新建立帳號或查看 Dify 官方文件
```

### 問題 3: API Key 建立後忘記複製
**解決方法：**
- API Key 無法再次查看
- 需要刪除舊的 API Key，重新建立新的

### 問題 4: Weaviate 類別名稱不知道
**解決方法：**
```bash
# 查詢 Weaviate schema
curl http://localhost:8080/v1/schema | jq '.classes[].class'

# 或在 Cursor 中使用
用 weaviate-mcp 列出所有類別
```

---

## 📊 完成檢查清單

- [ ] 成功登入 Dify Web UI
- [ ] 建立第一個應用
- [ ] 取得並複製 API Key
- [ ] 更新 `.cursor/mcp.json` 中的 `DIFY_API_KEY`
- [ ] 建立知識庫（啟用 Weaviate）
- [ ] 重新載入 Cursor MCP
- [ ] 測試 `dify-mcp` 取得參數（不再 401）
- [ ] 測試 `dify-mcp` 對話功能
- [ ] 測試 `weaviate-mcp` 列出類別（有資料）
- [ ] 測試 `weaviate-mcp` 搜尋功能

---

## 🎯 完成後的能力

完成設定後，你將可以：

### 使用 dify-mcp
- ✅ 與 Dify AI 對話
- ✅ 執行 Dify 工作流
- ✅ 查詢對話歷史
- ✅ 管理應用參數

### 使用 weaviate-mcp
- ✅ 搜尋知識庫內容
- ✅ 查詢向量資料庫統計
- ✅ 管理 schema 類別
- ✅ 語意搜尋文件

### 整合應用
- ✅ 在 Cursor 中直接呼叫 Dify AI
- ✅ 搜尋知識庫並取得相關文件
- ✅ 自動化工作流觸發
- ✅ 統一管理 AI 服務

---

**準備好了嗎？開始設定 Dify！** 🚀

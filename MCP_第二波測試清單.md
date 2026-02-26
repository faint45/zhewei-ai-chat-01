# MCP 第二波工具測試清單

## 📝 測試前準備

### 1. 安裝 Python 依賴（自建工具需要）
```bash
# 在終端機執行
cd D:/zhe-wei-tech/Jarvis_Training
.venv312/Scripts/activate
pip install weaviate-client httpx
```

### 2. 重新載入 Cursor MCP 設定
```
Cursor → Settings (Ctrl+,) → Features → Model Context Protocol → Reload
```
或直接重啟 Cursor

### 3. 確認工具已載入
在 Cursor Composer 中，輸入 `@` 應該會看到新增的工具：
- `@postgres-dify`
- `@redis-local`
- `@weaviate-mcp`
- `@dify-mcp`

---

## ✅ 測試項目

### Test 1: postgres-dify（PostgreSQL）
**在 Cursor Composer 中輸入：**
```
用 postgres-dify 列出所有資料表
```

**預期結果：**
- 顯示 Dify 資料庫中的所有資料表
- 應包含 `accounts`, `apps`, `datasets`, `documents` 等表

**進階測試：**
```
用 postgres-dify 查詢 SELECT version()
用 postgres-dify 查詢 SELECT count(*) FROM pg_tables WHERE schemaname = 'public'
用 postgres-dify 查詢 SELECT tablename FROM pg_tables WHERE schemaname = 'public' LIMIT 10
```

**如果失敗：**
- 確認 PostgreSQL 容器正在運行：`docker ps | findstr postgres`
- 測試連線：`docker exec docker-db_postgres-1 psql -U postgres -d dify -c "SELECT 1"`

---

### Test 2: redis-local（Redis）
**在 Cursor Composer 中輸入：**
```
用 redis-local 列出所有 key
```

**預期結果：**
- 顯示 Redis 中的所有 key（可能很多，Dify 會使用 Redis 做快取）
- 或顯示 key 的數量

**進階測試：**
```
用 redis-local 查詢 INFO server
用 redis-local 查詢 DBSIZE
用 redis-local 查詢 KEYS dify:*
```

**如果失敗：**
- 確認 Redis 容器正在運行：`docker ps | findstr redis`
- 測試連線：`docker exec docker-redis-1 redis-cli ping`

---

### Test 3: weaviate-mcp（Weaviate 向量資料庫）
**在 Cursor Composer 中輸入：**
```
用 weaviate-mcp 列出所有類別
```

**預期結果：**
- 顯示 Weaviate 中的所有 schema classes
- 可能包含 Dify 建立的知識庫類別

**進階測試：**
```
用 weaviate-mcp 取得統計資訊
用 weaviate-mcp 取得完整 schema
```

**如果失敗：**
- 確認 Weaviate 容器正在運行：`docker ps | findstr weaviate`
- 檢查 Python 依賴：`pip show weaviate-client`
- 測試連線：`curl http://localhost:8080/v1/.well-known/ready`

---

### Test 4: dify-mcp（Dify AI 平台）
**在 Cursor Composer 中輸入：**
```
用 dify-mcp 取得應用參數
```

**預期結果：**
- 顯示 Dify 應用的參數設定
- 或提示需要 API Key

**注意：** 此工具需要 Dify API Key，需先在 Dify Web UI 中建立：
1. 開啟 http://localhost:8080
2. 登入 Dify
3. 進入應用設定 → API Access
4. 建立 API Key
5. 更新 `.cursor/mcp.json` 中的 `DIFY_API_KEY`

**進階測試（需 API Key）：**
```
用 dify-mcp 與 AI 對話：測試訊息
用 dify-mcp 取得對話歷史
```

**如果失敗：**
- 確認 Dify 容器正在運行：`docker ps | findstr dify`
- 檢查 Python 依賴：`pip show httpx`
- 測試 Dify API：`curl http://localhost:8080/v1/parameters`

---

## 🐛 常見問題排查

### 問題 1: postgres-dify 連線失敗
**解決方法：**
```bash
# 測試 PostgreSQL 連線
docker exec docker-db_postgres-1 psql -U postgres -d dify -c "\dt"

# 如果密碼錯誤，檢查環境變數
docker exec docker-db_postgres-1 env | findstr POSTGRES
```

### 問題 2: redis-local 無法連接
**解決方法：**
```bash
# 測試 Redis 連線
docker exec docker-redis-1 redis-cli ping

# 應回傳 PONG
```

### 問題 3: weaviate-mcp 啟動失敗
**解決方法：**
```bash
# 確認 weaviate-client 已安裝
pip install weaviate-client

# 測試 Weaviate API
curl http://localhost:8080/v1/.well-known/ready
```

### 問題 4: dify-mcp 需要 API Key
**解決方法：**
1. 開啟 http://localhost:8080
2. 登入 Dify（預設帳號可能在 docker logs 中）
3. 建立應用並取得 API Key
4. 更新 `.cursor/mcp.json`：
```json
"dify-mcp": {
  "env": {
    "DIFY_API_KEY": "app-your-actual-api-key-here"
  }
}
```

### 問題 5: Python 模組找不到
**解決方法：**
```bash
# 確認虛擬環境路徑
D:/zhe-wei-tech/Jarvis_Training/.venv312/Scripts/python.exe --version

# 安裝依賴
D:/zhe-wei-tech/Jarvis_Training/.venv312/Scripts/pip.exe install weaviate-client httpx
```

---

## 📊 測試結果記錄

| 測試項目 | 狀態 | 備註 |
|---------|------|------|
| postgres-dify 列出資料表 | ⬜ 未測試 |  |
| redis-local 列出 key | ⬜ 未測試 |  |
| weaviate-mcp 列出類別 | ⬜ 未測試 |  |
| dify-mcp 取得參數 | ⬜ 未測試 | 需 API Key |
| postgres-dify 查詢版本 | ⬜ 未測試 |  |
| redis-local 查詢資訊 | ⬜ 未測試 |  |
| weaviate-mcp 統計資訊 | ⬜ 未測試 |  |

---

## 🎯 測試完成後

如果所有測試通過：
1. ✅ 更新 `MCP_測試結果記錄.md`
2. ✅ 第二波 MCP 工具部署成功
3. ✅ 可以開始使用這些工具改善工作流程
4. ✅ 準備第三波工具（qdrant-mcp, sentry-mcp, n8n-mcp）

如果有測試失敗：
- 記錄錯誤訊息
- 檢查上方的排查步驟
- 確認 Docker 容器狀態
- 檢查 Python 依賴安裝

---

## 💡 使用範例

### 範例 1: 查詢 Dify 資料庫中的應用數量
```
用 postgres-dify 查詢 SELECT count(*) as app_count FROM apps
```

### 範例 2: 查看 Redis 快取使用情況
```
用 redis-local 查詢 INFO memory
```

### 範例 3: 搜尋 Weaviate 向量資料庫
```
用 weaviate-mcp 在 [ClassName] 中搜尋「營建法規」
```

### 範例 4: 與 Dify AI 對話
```
用 dify-mcp 對話：請幫我分析最近的專案進度
```

---

## 🔧 下一步

1. **安裝 Python 依賴**（必要）
   ```bash
   pip install weaviate-client httpx
   ```

2. **重新載入 Cursor MCP**

3. **逐一測試四個新工具**

4. **取得 Dify API Key**（dify-mcp 需要）

5. **記錄測試結果**

6. **準備第三波工具安裝**

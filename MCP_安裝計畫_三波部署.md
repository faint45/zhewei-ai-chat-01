# 築未科技 MCP 工具三波部署計畫

## ✅ 第一波（本週）- 已完成

### 1. docker-mcp
**用途：** 管理 Docker 容器、查看日誌、重啟服務
**安裝狀態：** ✅ 已加入 `.cursor/mcp.json`
**驗證指令：**
```
用 docker-mcp 列出所有容器狀態
用 docker-mcp 查看 zhewei_brain 容器日誌
用 docker-mcp 重啟 zhe-wei-ollama
```

### 2. git
**用途：** 版本控制、分支管理、查看歷史
**安裝狀態：** ✅ 已加入 `.cursor/mcp.json`
**工作目錄：** `D:/zhe-wei-tech`
**驗證指令：**
```
用 git 查看目前分支狀態
用 git 顯示最近 5 次 commit
用 git 建立新分支 feature/mcp-tools
```

### 3. fetch
**用途：** 通用 HTTP 請求、API 呼叫
**安裝狀態：** ✅ 已加入 `.cursor/mcp.json`
**驗證指令：**
```
用 fetch 查詢 https://api.github.com/repos/modelcontextprotocol/servers
用 fetch POST 到 http://127.0.0.1:8002/api/health/summary
```

---

## 📋 第二波（下週）- 待安裝

### 4. postgres-local
**用途：** PostgreSQL 資料庫操作
**配置：**
```json
{
  "postgres-local": {
    "command": "npx",
    "args": [
      "-y",
      "@modelcontextprotocol/server-postgres",
      "postgresql://user:password@localhost:5432/zhewei_brain"
    ],
    "env": {}
  }
}
```
**前置作業：**
1. 確認 PostgreSQL 已在 `docker-compose.profiles.yml` 啟動（dev mode）
2. 建立資料庫：`docker exec -it postgres psql -U user -c "CREATE DATABASE zhewei_brain;"`
3. 更新連線字串中的 user/password

**驗證指令：**
```
用 postgres-local 列出所有資料表
用 postgres-local 查詢 SELECT * FROM projects LIMIT 5
```

---

### 5. slack
**用途：** Slack 訊息發送、頻道管理、檔案上傳
**配置：**
```json
{
  "slack": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-slack"],
    "env": {
      "SLACK_BOT_TOKEN": "xoxb-your-bot-token",
      "SLACK_TEAM_ID": "T01234567"
    }
  }
}
```
**前置作業：**
1. 前往 https://api.slack.com/apps 建立 Slack App
2. 啟用 Bot Token Scopes：
   - `chat:write`
   - `channels:read`
   - `files:write`
   - `users:read`
3. 安裝 App 到工作區
4. 複製 Bot User OAuth Token（xoxb-...）
5. 複製 Team ID（在工作區設定中）

**驗證指令：**
```
用 slack 列出所有頻道
用 slack 發送訊息到 #general：MCP 工具測試成功
用 slack 上傳檔案 reports/daily_summary.md 到 #project-updates
```

---

### 6. everything（Windows 檔案搜尋）
**用途：** 秒搜全硬碟檔案（PDF、DWG、圖檔）
**配置：**
```json
{
  "everything": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-everything"],
    "env": {}
  }
}
```
**前置作業：**
1. 下載安裝 Everything：https://www.voidtools.com/
2. 啟動 Everything 並確保索引完成
3. 啟用 HTTP Server：
   - 工具 → 選項 → HTTP Server
   - 勾選「啟用 HTTP Server」
   - 預設端口：80（或改成 8888）

**驗證指令：**
```
用 everything 搜尋所有 .pdf 檔案包含「營建法規」
用 everything 找 D:/Site_Data 下的 .dwg 檔案
用 everything 列出最近 7 天修改的 .xlsx 檔案
```

---

## 🔧 第三波（長期）- 自建工具

### 7. qdrant-mcp（自建）
**用途：** 向量資料庫操作、語意搜尋
**實作位置：** `mcp_servers/qdrant_mcp.py`
**參考範本：** `mcp_servers/construction_law_mcp.py`

**核心功能：**
- `qdrant_search(collection, query, top_k)` - 向量搜尋
- `qdrant_insert(collection, vectors, metadata)` - 插入向量
- `qdrant_list_collections()` - 列出所有集合
- `qdrant_stats(collection)` - 集合統計

**配置範例：**
```json
{
  "qdrant-mcp": {
    "command": "D:/zhe-wei-tech/Jarvis_Training/.venv312/Scripts/python.exe",
    "args": ["D:/zhe-wei-tech/mcp_servers/qdrant_mcp.py"],
    "env": {
      "QDRANT_URL": "http://localhost:6333"
    }
  }
}
```

---

### 8. sentry-mcp（自建）
**用途：** 錯誤監控、日誌查詢、異常追蹤
**實作位置：** `mcp_servers/sentry_mcp.py`

**核心功能：**
- `sentry_recent_errors(hours, severity)` - 查詢近期錯誤
- `sentry_error_detail(error_id)` - 錯誤詳情
- `sentry_log_search(keyword, limit)` - 日誌搜尋
- `sentry_stats()` - 錯誤統計

**資料來源：**
- `reports/*.log` 檔案
- `brain_system.log`
- `discord_bot_runtime.log`
- 可選：整合 Sentry.io API

**配置範例：**
```json
{
  "sentry-mcp": {
    "command": "D:/zhe-wei-tech/Jarvis_Training/.venv312/Scripts/python.exe",
    "args": ["D:/zhe-wei-tech/mcp_servers/sentry_mcp.py"],
    "env": {
      "LOG_DIR": "D:/zhe-wei-tech/reports",
      "SENTRY_DSN": "https://your-sentry-dsn@sentry.io/project-id"
    }
  }
}
```

---

### 9. notion
**用途：** Notion 文件管理、資料庫操作
**配置：**
```json
{
  "notion": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-notion"],
    "env": {
      "NOTION_API_KEY": "secret_your-notion-integration-token"
    }
  }
}
```
**前置作業：**
1. 前往 https://www.notion.so/my-integrations 建立整合
2. 授權整合存取特定頁面/資料庫
3. 複製 Internal Integration Token

**驗證指令：**
```
用 notion 列出所有頁面
用 notion 建立新頁面「MCP 工具部署記錄」
用 notion 查詢資料庫「專案進度」
```

---

## 📊 部署時程表

| 時間 | 工具 | 狀態 | 負責人 |
|------|------|------|--------|
| Week 1 | docker-mcp | ✅ 完成 | 系統 |
| Week 1 | git | ✅ 完成 | 系統 |
| Week 1 | fetch | ✅ 完成 | 系統 |
| Week 2 | postgres-local | ⏳ 待安裝 | - |
| Week 2 | slack | ⏳ 待安裝 | - |
| Week 2 | everything | ⏳ 待安裝 | - |
| Week 3-4 | qdrant-mcp | 📝 規劃中 | 開發 |
| Week 3-4 | sentry-mcp | 📝 規劃中 | 開發 |
| Week 4 | notion | ⏳ 待安裝 | - |

---

## 🔍 驗證清單

### 第一波驗證（現在可測試）
```bash
# 1. 重新載入 Cursor MCP 設定
# Cursor → Settings → Features → MCP → Reload

# 2. 確認新工具出現
# 應該看到：docker-mcp, git, fetch

# 3. 測試 Docker
用 docker-mcp 列出所有容器

# 4. 測試 Git
用 git 查看目前狀態

# 5. 測試 Fetch
用 fetch GET http://127.0.0.1:8002/health
```

### 第二波驗證（下週）
- [ ] PostgreSQL 連線成功
- [ ] Slack 訊息發送成功
- [ ] Everything 搜尋回傳結果

### 第三波驗證（長期）
- [ ] Qdrant 向量搜尋正常
- [ ] Sentry 日誌查詢正常
- [ ] Notion 頁面建立成功

---

## 📝 注意事項

1. **API Key 安全**
   - 所有 API Key 都存在 `.cursor/mcp.json`
   - 此檔案已在 `.gitignore` 中（確認！）
   - 不要 commit 含有真實 key 的檔案

2. **端口衝突**
   - Everything HTTP Server 預設 80（可能與 IIS 衝突）
   - 建議改用 8888 或 8889

3. **權限問題**
   - Docker 操作需要 Docker daemon 執行中
   - Git 操作需要工作目錄寫入權限
   - Everything 需要管理員權限（首次安裝）

4. **效能考量**
   - 不要同時啟用過多 MCP server（建議 < 15 個）
   - 自建 MCP 工具注意記憶體使用
   - 大量檔案搜尋可能影響 Everything 效能

---

## 🚀 快速啟用指令

### 第二波安裝（複製貼上到 `.cursor/mcp.json`）
```json
    "postgres-local": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://user:password@localhost:5432/zhewei_brain"],
      "env": {}
    },
    "slack": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "請填入你的SlackBotToken",
        "SLACK_TEAM_ID": "請填入你的TeamID"
      }
    },
    "everything": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-everything"],
      "env": {}
    }
```

記得在每個新增項目前加逗號 `,`！

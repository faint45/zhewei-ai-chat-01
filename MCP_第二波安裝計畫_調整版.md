# MCP 第二波安裝計畫（根據實際環境調整）

基於測試結果與 Docker 容器狀態，調整第二波安裝計畫。

---

## 📊 環境分析

### 已運行的服務（可直接整合）
| 服務 | 容器名稱 | 端口 | 狀態 |
|------|---------|------|------|
| PostgreSQL | docker-db_postgres-1 | 5432 | Up 31h |
| Redis | docker-redis-1 | 6379 | Up 31h |
| Weaviate | docker-weaviate-1 | 8080 | Up 31h |
| Qdrant | zhewei-qdrant | 6333 | Up 31h |

### 已停止的服務（需要時可啟動）
| 服務 | 容器名稱 | 用途 |
|------|---------|------|
| n8n | zhewei-n8n | 工作流自動化 |
| Open WebUI | open-webui | Ollama Web 介面 |
| OpenHands | openhands | AI 程式碼助手 |
| MCPO | webui-mcpo | MCP 管理介面 |

---

## ✅ 第二波工具（調整版）

### 1. postgres-local ⭐ 優先

**用途：** 操作 Dify 的 PostgreSQL 資料庫

**配置（調整後）：**
```json
{
  "postgres-dify": {
    "command": "npx",
    "args": [
      "-y",
      "@modelcontextprotocol/server-postgres",
      "postgresql://postgres:difyai123456@localhost:5432/dify"
    ],
    "env": {}
  }
}
```

**前置作業：**
1. 確認 PostgreSQL 連線資訊：
```bash
# 在終端機執行
docker exec -it docker-db_postgres-1 psql -U postgres -c "\l"
```

2. 查看環境變數（在 docker-compose.yml 或 .env 中）：
   - `POSTGRES_USER`（預設：postgres）
   - `POSTGRES_PASSWORD`（需確認）
   - `POSTGRES_DB`（預設：dify）

3. 更新上方 JSON 中的連線字串

**驗證指令：**
```
用 postgres-dify 列出所有資料表
用 postgres-dify 查詢 SELECT version()
用 postgres-dify 查詢 SELECT count(*) FROM pg_tables WHERE schemaname = 'public'
```

---

### 2. redis-mcp ⭐ 新增建議

**用途：** 操作 Redis 快取、查詢 key、監控記憶體

**配置：**
```json
{
  "redis-local": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-redis", "redis://localhost:6379"],
    "env": {}
  }
}
```

**驗證指令：**
```
用 redis-local 列出所有 key
用 redis-local 查詢 INFO server
用 redis-local 取得 key 的值
```

---

### 3. slack

**用途：** Slack 訊息發送、頻道管理

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
5. 複製 Team ID

**驗證指令：**
```
用 slack 列出所有頻道
用 slack 發送訊息到 #general：MCP 第二波測試成功
```

---

### 4. everything

**用途：** Windows 檔案快速搜尋

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
2. 啟動 Everything 並等待索引完成
3. 啟用 HTTP Server：
   - 工具 → 選項 → HTTP Server
   - 勾選「啟用 HTTP Server」
   - 端口：80（或 8888，避免與 Dify 的 8080 衝突）

**驗證指令：**
```
用 everything 搜尋所有 .pdf 檔案
用 everything 找 D:/zhe-wei-tech 下的 .py 檔案
用 everything 列出最近 7 天修改的檔案
```

---

## 🆕 額外建議工具（第 2.5 波）

### 5. weaviate-mcp（自建）⭐ 強烈建議

**為什麼需要：**
- 你已有 Weaviate 向量資料庫在運行（Dify 使用）
- 但 Brain Server 回報 `weaviate: False`（連線問題）
- 建立 MCP 工具可直接操作 Weaviate

**實作位置：** `mcp_servers/weaviate_mcp.py`

**核心功能：**
- `weaviate_search(class_name, query, limit)` - 語意搜尋
- `weaviate_list_classes()` - 列出所有類別
- `weaviate_get_schema()` - 取得 schema
- `weaviate_stats()` - 統計資訊

**配置：**
```json
{
  "weaviate-mcp": {
    "command": "D:/zhe-wei-tech/Jarvis_Training/.venv312/Scripts/python.exe",
    "args": ["D:/zhe-wei-tech/mcp_servers/weaviate_mcp.py"],
    "env": {
      "WEAVIATE_URL": "http://localhost:8080"
    }
  }
}
```

---

### 6. dify-mcp（自建）⭐ 強烈建議

**為什麼需要：**
- 你有完整的 Dify AI 平台在運行
- 可透過 MCP 呼叫 Dify API：
  - 觸發工作流
  - 查詢對話歷史
  - 管理知識庫
  - 執行 Agent

**實作位置：** `mcp_servers/dify_mcp.py`

**核心功能：**
- `dify_chat(message, conversation_id)` - 對話
- `dify_run_workflow(workflow_id, inputs)` - 執行工作流
- `dify_list_apps()` - 列出所有應用
- `dify_knowledge_search(query)` - 知識庫搜尋

**配置：**
```json
{
  "dify-mcp": {
    "command": "D:/zhe-wei-tech/Jarvis_Training/.venv312/Scripts/python.exe",
    "args": ["D:/zhe-wei-tech/mcp_servers/dify_mcp.py"],
    "env": {
      "DIFY_API_URL": "http://localhost:8080/v1",
      "DIFY_API_KEY": "app-your-api-key"
    }
  }
}
```

---

### 7. n8n-mcp（自建）

**為什麼需要：**
- 你有 n8n 工作流自動化工具（已停止）
- 可透過 MCP 觸發 n8n 工作流

**前置作業：**
```bash
# 啟動 n8n
docker start zhewei-n8n
```

**配置：**
```json
{
  "n8n-mcp": {
    "command": "D:/zhe-wei-tech/Jarvis_Training/.venv312/Scripts/python.exe",
    "args": ["D:/zhe-wei-tech/mcp_servers/n8n_mcp.py"],
    "env": {
      "N8N_URL": "http://localhost:5678",
      "N8N_API_KEY": "your-n8n-api-key"
    }
  }
}
```

---

## 📋 安裝優先順序（調整後）

### 立即安裝（本週）
1. **postgres-dify** - 已有資料庫，直接連接
2. **redis-local** - 已有 Redis，直接連接
3. **slack** - 需申請 Token（可選）

### 下週安裝
4. **everything** - 需安裝軟體
5. **weaviate-mcp**（自建）- 已有 Weaviate，建立 MCP 工具
6. **dify-mcp**（自建）- 整合 Dify 平台

### 長期規劃
7. **n8n-mcp**（自建）- 工作流自動化
8. **qdrant-mcp**（已建立模板）- 向量資料庫操作
9. **sentry-mcp**（已建立模板）- 錯誤監控

---

## 🚀 快速安裝指令

### 第二波核心工具（複製到 `.cursor/mcp.json`）
```json
    "postgres-dify": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://postgres:PASSWORD@localhost:5432/dify"],
      "env": {}
    },
    "redis-local": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-redis", "redis://localhost:6379"],
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

**注意：** 記得將 `PASSWORD` 替換為實際的 PostgreSQL 密碼！

---

## 🔧 下一步行動

1. **確認 PostgreSQL 密碼**
   ```bash
   # 查看 docker-compose.yml 或 .env
   grep -i postgres docker-compose.yml
   ```

2. **測試資料庫連線**
   ```bash
   docker exec -it docker-db_postgres-1 psql -U postgres -d dify -c "SELECT version();"
   ```

3. **安裝第二波工具**
   - 複製上方 JSON 到 `.cursor/mcp.json`
   - 更新密碼
   - 重新載入 Cursor MCP

4. **建立自建工具**
   - weaviate-mcp（參考 qdrant-mcp 模板）
   - dify-mcp（整合 Dify API）

5. **修正 Brain Server 依賴檢查**
   - 檢查 `brain_server.py` 中的 `_resolve_dependency_status()`
   - 確認 Weaviate/Redis/PostgreSQL 的連線字串正確

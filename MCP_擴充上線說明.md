# 築未科技 MCP 擴充上線說明

已完成以下 MCP 伺服器設定（見 `.cursor/mcp.json`）：

1. `brave-search`
2. `sequential-thinking`
3. `filesystem-restricted`
4. `sqlite-local`
5. `google-maps`
6. `construction-law-mcp`（自建，封裝現有 ChromaDB）
7. `osm-geocode-mcp`（自建，免費地理編碼）
8. `osrm-route-mcp`（自建，免費路線與 ETA）

## 一、你需要先填的 API Key

- `brave-search`：把 `.cursor/mcp.json` 中 `BRAVE_API_KEY` 改成你的金鑰
- `google-maps`：把 `.cursor/mcp.json` 中 `GOOGLE_MAPS_API_KEY` 改成你的金鑰

## 二、Filesystem 白名單（已限制）

`filesystem-restricted` 目前只允許以下路徑：

- `D:/Site_Data`
- `D:/brain_workspace/Reports`
- `D:/zhe-wei-tech/Jarvis_Training/reports`

這可避免 MCP 操作到系統目錄。

## 三、SQLite 路徑

`sqlite-local` 指向：

- `D:/zhe-wei-tech/Jarvis_Training/jarvis_ops.db`

若檔案不存在，SQLite server 啟動時可建立空 DB。

## 四、Construction Law MCP（自建）

檔案：

- `mcp_servers/construction_law_mcp.py`

可用工具：

- `construction_law_search(query, top_k=5)`
- `construction_law_stats()`

資料來源：

- `JARVIS_DB_PATH=D:/zhe-wei-tech/Jarvis_Training/chroma_db`
- `JARVIS_COLLECTION=jarvis_training`

## 五、在 Cursor 啟用方式

1. 打開 Cursor → Settings → Features → MCP
2. 重新載入 `.cursor/mcp.json`
3. 確認上述 servers 都顯示為可用
4. 在 Composer Agent 直接下指令呼叫（例如：搜尋法規、查地圖路線、SQL 查詢）

## 六、建議驗證指令

- Brave：
  - 「用 brave-search 查嘉義縣綠建築容積獎勵最新修正」
- Sequential Thinking：
  - 「用 sequential-thinking 分步分析地下水上浮處置方案」
- Construction Law：
  - 「用 construction-law-mcp 查限制性招標第22條風險」
- SQLite：
  - 「用 sqlite-local 查上月鋼筋工出工統計」
- Google Maps：
  - 「用 google-maps 估算高雄鋼廠到民雄工地避塞車到達時間」
- OSM Geocode（免費替代）：
  - 「用 osm-geocode-mcp 把嘉義縣民雄鄉轉成座標」
  - 「用 osm-geocode-mcp 反查 23.5200,120.4300 對應地址」
- OSRM Route（免費替代）：
  - 「用 osrm-route-mcp 估算起點到終點距離與分鐘數」


# 全系統健康報告

**測試時間**: 2026-02-27 02:28:01
**結果**: 27 ✅ / 1 ⚠️ / 0 ❌ / 28 項
**通過率**: 96%

| # | 測試項目 | 狀態 | 耗時 | 詳情 |
|---|---------|------|------|------|
| 01 | Brain Server API | ✅ PASS | 0.0s | HTTP 200 |
| 02 | Ollama 本地模型 | ✅ PASS | 0.0s | 10 models: deepseek-r1:14b, qwen3:32b, qwen3:30b, zhewei-agent:latest, zhewei-brain:latest |
| 03 | Ollama 推理 (qwen3:4b) | ✅ PASS | 0.8s | 回覆:  |
| 04 | Brain Server AI Chat | ✅ PASS | 0.0s | HTTP 200 chat/remote OK |
| 05 | Forge 生圖 | ✅ PASS | 0.3s | HTTP 200 |
| 06 | ComfyUI 生圖 | ✅ PASS | 0.3s | HTTP 200 |
| 07 | AI 視覺辨識 (YOLO+OCR) | ✅ PASS | 0.3s | HTTP 200 |
| 08 | 代碼模擬器 CodeSim (GW) | ✅ PASS | 0.0s | HTTP 200 |
| 08 | 代碼模擬器 CodeSim (GW) | ✅ PASS | 0.0s | via Gateway HTTP 302 |
| 09 | CMS 營建管理 | ✅ PASS | 0.3s | HTTP 404 |
| 10 | 預測/警報系統 | ✅ PASS | 0.3s | HTTP 404 |
| 11 | Dify | ✅ PASS | 0.0s | HTTP 307 |
| 12 | Bridge 工作空間 | ✅ PASS | 0.0s | HTTP 404 |
| 13 | Cloudflare 外網域名 | ✅ PASS | 2.2s | 主站=200 | Jarvis=200 | Bridge=200 | CodeSim=200 |
| 14 | Discord Bot (Jarvis) | ⚠️ WARN | 0.0s | status=alive, last=unknown |
| 15 | ComfyUI 影片 | ✅ PASS | 0.1s | HTTP 200 |
| 16 | Ollama Prompt 翻譯 | ✅ PASS | 0.0s | HTTP 200 |
| 17 | 知識庫 ChromaDB | ✅ PASS | 12.5s | 搜尋成功, 結果長度=155 |
| 18 | Phone Agent (模組) | ✅ PASS | 0.0s | HTTP 200 |
| 19 | MCP 伺服器 | ✅ PASS | 0.0s | 11 個: construction_law_mcp.py, dify_mcp.py, ffmpeg_video_mcp.py, ollama_local_mcp.py, osm_geocode_mcp.py |
| 20 | 認證系統 JWT | ✅ PASS | 0.0s | Auth 正確拒絕: 帳號不存在 |
| 21 | Ntfy 推播服務 | ✅ PASS | 0.0s | 本地容器 healthy |
| 22 | DeepDiagram 圖表 | ✅ PASS | 0.0s | HTTP 404 |
| 23 | Gateway Nginx | ✅ PASS | 0.0s | HTTP 200 |
| 24 | PWA 頁面 | ✅ PASS | 0.0s | HTTP 200 |
| 25 | PWA Manifest | ✅ PASS | 0.0s | HTTP 200 | found '築未' |
| 26 | PWA Service Worker | ✅ PASS | 0.0s | HTTP 200 |
| 27 | PWA 登入流程 | ✅ PASS | 0.1s | superadmin=True, role=superadmin |

## ⚠️ 注意事項 (1 項)

- **[14] Discord Bot (Jarvis)**: status=alive, last=unknown

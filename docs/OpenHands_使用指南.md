# 築未科技 — OpenHands (原 OpenDevin) 使用指南

**定位**：開源 AI 軟體工程師，自動寫程式、測試、修 Bug。

---

## 一、啟動

雙擊 **`Start_OpenHands.bat`** 或執行：

```powershell
cd D:\zhe-wei-tech
docker compose -f docker-compose.openhands.yml up -d
```

介面網址：**http://localhost:3001**

---

## 二、首次設定 LLM

打開 http://localhost:3001 後，點右上角 **Settings**（齒輪圖示）：

### 方案 A：使用本地 Ollama（免費）

| 欄位 | 填寫 |
|------|------|
| LLM Provider | `Ollama` |
| Model | `ollama/zhewei-brain:latest`（或 `ollama/llama3:8b-instruct`） |
| Base URL | `http://host.docker.internal:11434` |
| API Key | `local-key`（任意值即可） |

### 方案 B：使用 Gemini（更強、有免費額度）

| 欄位 | 填寫 |
|------|------|
| LLM Provider | `Google` |
| Model | `gemini/gemini-2.0-flash` |
| API Key | 你的 `GEMINI_API_KEY` |

### 方案 C：使用 Groq（免費額度、快速）

| 欄位 | 填寫 |
|------|------|
| LLM Provider | `Groq` |
| Model | `groq/llama-3.3-70b-versatile` |
| API Key | 你的 `GROQ_API_KEY` |

---

## 三、使用方式

1. 在左側對話框輸入任務，例如：
   - 「幫我建一個 Flask API，包含 /health 和 /users 路由，用 pytest 測試」
   - 「修復 brain_server.py 的 WebSocket 連線問題」
   - 「幫我寫一個 React 前端，有登入頁面和儀表板」

2. OpenHands 會自動：
   - 在右側沙盒中開啟編輯器
   - 寫程式碼
   - 執行指令（安裝依賴、跑測試）
   - 看到報錯 → 自動修正
   - 直到任務完成

3. 完成後，程式碼在 `/workspace` 中（對應你的 D:\zhe-wei-tech）

---

## 四、與現有系統整合

| 整合點 | 說明 |
|--------|------|
| **專案目錄** | D:\zhe-wei-tech 已掛載為 /workspace |
| **Ollama** | 透過 host.docker.internal:11434 連接 |
| **self_heal_web_loop** | 可用 OpenHands 取代手動修復 |
| **Discord Bot** | 可讓 `!autobuild` 指令改為呼叫 OpenHands API |

---

## 五、常用操作

| 操作 | 指令 |
|------|------|
| 啟動 | `docker compose -f docker-compose.openhands.yml up -d` |
| 停止 | `docker compose -f docker-compose.openhands.yml down` |
| 看日誌 | `docker logs openhands --tail 50` |
| 重啟 | `docker compose -f docker-compose.openhands.yml restart` |

---

## 六、注意事項

1. OpenHands 的沙盒會啟動額外的 Docker 容器，確保 Docker Desktop 記憶體分配足夠（建議至少 4GB）
2. 使用 Ollama 時，模型越大越準但越慢；建議 7B 以上
3. Port 3001（因 Open WebUI 已佔用 3000）

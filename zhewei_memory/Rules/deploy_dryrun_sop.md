# 部署前兵推 SOP + 模組化開發規範 (v1.0)

- 更新時間：2026-02-27T17:50:00
- 來源：Brain Server v2.0 模組化重構實戰經驗
- 適用：任何 Docker 容器 rebuild / 模組重構 / 大規模 import 變更

---

## 一、部署前兵推 — 六關流程

### 觸發條件（任一成立）
- 新增或修改 ≥3 個 .py
- 修改 Dockerfile / requirements / docker-compose.yml
- 拆分或合併模組
- 變更跨模組 import 路徑

### 第一關：語法檢查
`python -m py_compile <file.py>` 全過。

### 第二關：Import 鏈驗證
列出共用模組匯出符號 → 逐一比對每個消費端 import → 製表確認。

### 第三關：硬依賴存在性
找非 try/except 的 import → 確認 .py 存在 + class/function 名正確。
注意別名：GeminiService = AIService、AgentManager 在 agent_logic 不在 ai_service。

### 第四關：函式簽名匹配
class 實例化和函式呼叫 → 檢查 __init__ 必填參數 + 參數名。

### 第五關：Docker Context 優化
.dockerignore 排除大型目錄，目標 < 150MB。

### 第六關：Build & 啟動驗證
build → up -d → 驗 /healthz → 查 logs。一次只跑一個 build。

---

## 二、模組化開發規範

### 架構
- brain_server_v2.py：精簡主檔（app 初始化 + WebSocket + 啟動）
- routers/deps.py：共用依賴（認證、AI 服務、狀態、Pydantic 模型）
- routers/*.py：13 個功能 Router（auth/pages/system/commercial/usage/proxy/asset/host_phone/smart_chat/agent/jarvis/extras）

### 強制規則
- 新端點 → 對應 router，禁止直接改主檔
- POST/PUT body → Pydantic BaseModel
- 敏感端點 → _require_jwt / _require_admin
- 回應格式 → {"ok": bool, ...}
- 可選依賴 → try/except ImportError
- 日誌 → logger，禁止 print
- 單檔 ≤ 800 行
- 共用邏輯 → deps.py
- 部署前 → 必須過六關兵推

### 新增端點流程
1. 選擇或新建 router
2. 寫端點 + Pydantic model
3. 若需共用函式 → deps.py
4. brain_server_v2.py 加 include_router
5. 兵推六關
6. Docker rebuild

---

## 三、歷史教訓

| 日期 | 教訓 |
|------|------|
| 2026-02-27 | AgentManager 在 agent_logic.py 不在 ai_service.py，兵推攔截 |
| 2026-02-27 | Docker context 734MB → .dockerignore 優化後 ~95MB |
| 2026-02-27 | 多個 docker-compose build 並行阻塞，只能串行 |

---

## 四、執行原則

- 兵推未通過前，禁止 docker-compose build
- 發現 bug 必須修復後重跑該關
- 兵推結果寫入 brain_workspace/reports/ 供追蹤
- 所有 AI 代理人（Cursor / Windsurf / Claude / Ollama）均需遵守

# 🔍 架構研究報告：OpenHands + ECC → 築未科技平台借鑑

> 研究日期：2026-02-26
> 研究對象：OpenHands (All-Hands-AI, 60k+ ⭐) + Everything Claude Code (affaan-m, 38k+ ⭐)
> 目標：提煉可直接應用到築未科技平台的架構模式

---

## 一、兩個專案的核心架構對比

### OpenHands — AI 軟體工程 Agent 平台

```text
openhands/
├── agenthub/          ← Agent 註冊中心（CodeAct, Browsing, ReadOnly...）
├── controller/        ← AgentController 主迴圈 + StuckDetector 卡住偵測
├── core/              ← Config, Loop, Setup, Schema, Exceptions
├── events/            ← EventStream 事件匯流排（Action → Observation 模型）
├── memory/            ← Memory Condenser（LLM 摘要壓縮歷史）
├── llm/               ← LLM Registry + Metrics + Retry + Router
├── runtime/           ← Docker Sandbox 安全執行 + Plugin 系統
├── security/          ← SecurityAnalyzer（事件流安全審計）
├── integrations/      ← GitHub/GitLab/Azure DevOps/Bitbucket 多平台
├── microagent/        ← Microagent（Knowledge/Repo/Task 三類輕量 Agent）
├── storage/           ← FileStore 抽象（local/S3/GCS）
└── server/            ← Session + ConversationManager + WebSocket
```

**核心設計模式：**
1. **EventStream 事件匯流排** — 所有元件透過事件通訊，完全解耦
2. **Action-Observation 循環** — Agent 產生 Action → Runtime 執行 → 回傳 Observation → 更新 State
3. **StuckDetector** — 自動偵測 Agent 是否陷入迴圈
4. **Memory Condenser** — 上下文視窗滿了自動壓縮歷史
5. **LLM Metrics** — 追蹤每次呼叫的 cost、latency、token usage
6. **SecurityAnalyzer** — 插件式安全審計，Action 執行前攔截
7. **Microagent** — 輕量知識 Agent，用 trigger 關鍵字自動注入上下文

### Everything Claude Code — AI Coding 配置集合

```text
everything-claude-code/
├── agents/            ← 13 個專業 Agent（planner, tdd-guide, security-reviewer...）
├── skills/            ← 49 個技能模組（python-patterns, docker-patterns...）
├── commands/          ← 33 個 slash commands（/tdd, /plan, /e2e...）
├── hooks/             ← 自動化觸發器（session persistence, pre-tool）
├── rules/             ← 永遠遵守的規範（common/ + language-specific/）
└── mcp-configs/       ← MCP server 配置範本
```

**核心設計模式：**
1. **Agent 即 Markdown** — frontmatter 定義 name/tools/model，內文即 system prompt
2. **Skill 即知識庫** — 按需注入，觸發條件式載入
3. **Command 即工作流** — 用戶觸發的結構化流程
4. **Rule 即約束** — 永遠有效的編碼規範
5. **Hook 即自動化** — 事件驅動的 pre/post 處理
6. **Continuous Learning** — 從 session 自動提煉 pattern 變成新 skill

---

## 二、可借鑑到築未科技平台的 7 個關鍵模式

### 🔴 P1：EventStream 事件匯流排（來自 OpenHands）

**現狀：** 我們的模組之間是直接函數呼叫（tightly coupled）
**借鑑：** 建立輕量事件系統，所有感測器/決策/警報透過事件通訊

```python
# 新增: core/event_bus.py
class EventBus:
    """輕量事件匯流排 — 解耦感測器、決策引擎、警報系統"""
    _subscribers: dict[str, list[Callable]]
    
    def publish(event_type: str, data: dict)  # 發布事件
    def subscribe(event_type: str, callback)   # 訂閱事件
    def unsubscribe(event_type: str, callback) # 取消訂閱
```

**適用場景：**
- `water_alert`: 雷達讀數 → 事件 → 決策引擎 → 事件 → 警報系統 → 事件 → Ntfy/喇叭
- `construction_brain`: 語音輸入 → 事件 → 事件抽取 → 事件 → 日報/工安/進度
- 跨模組通訊：water_alert 水位告警 → construction_brain 工地停工通知

**預估收益：** 新增感測器或輸出管道時零改動現有程式碼

---

### 🔴 P2：LLM Metrics + Budget 控制（來自 OpenHands）

**現狀：** `usage_metering.py` 追蹤呼叫次數，但缺 token-level 追蹤
**借鑑：** OpenHands 的 `Metrics` 類追蹤每次 LLM 呼叫的 cost/latency/tokens

```python
# 增強: usage_metering.py
class LLMMetrics:
    accumulated_cost: float
    costs: list[Cost]          # per-call cost
    token_usages: list[TokenUsage]  # prompt/completion/cache tokens
    response_latencies: list[ResponseLatency]
    max_budget_per_task: float  # 預算上限
    
    def is_over_budget() -> bool
    def get_cost_summary() -> dict
```

**適用場景：**
- SmartAIService 每次呼叫記錄 model/tokens/cost/latency
- 商用方案依 tier 設定 budget 上限（free=0, pro=100次, enterprise=無限）
- Grafana 儀表板顯示 AI 用量趨勢

**預估收益：** 精準計費 + 防止 AI 用量失控

---

### 🔴 P3：Memory Condenser 記憶壓縮（來自 OpenHands）

**現狀：** construction_brain 的 knowledge base 用 ChromaDB，但工作記憶無壓縮
**借鑑：** OpenHands 的 Memory Condenser 在 context window 快滿時自動壓縮歷史

```python
# 新增: ai_modules/memory_condenser.py
class MemoryCondenser:
    """當對話歷史超過 token 上限時，自動壓縮舊訊息"""
    
    def condense(messages: list, max_tokens: int) -> list:
        # 1. 找到最舊的 agent 事件區塊
        # 2. 用 LLM 摘要該區塊
        # 3. 替換原始訊息為摘要
        # 4. 保留最近 N 輪完整對話
```

**適用場景：**
- brain_server 長對話 session（Jarvis 助理）
- construction_brain LINE 聊天記錄超長時自動壓縮
- water_alert 決策引擎歷史趨勢壓縮

**預估收益：** 解決長對話 context 爆炸問題

---

### 🟠 P4：Microagent 輕量知識注入（來自 OpenHands）

**現狀：** `ai_modules/ai_sop.py` 用 PromptTemplate，但是靜態的
**借鑑：** OpenHands Microagent 系統 — 根據 trigger 關鍵字自動注入專業知識

```python
# 三種類型:
# 1. RepoMicroagent — 專案層級，永遠載入（像我們的 CLAUDE.md）
# 2. KnowledgeMicroagent — 關鍵字觸發（如用戶提到「鋼筋」自動注入鋼筋規範）
# 3. TaskMicroagent — 用戶主動觸發（/daily-report, /safety-check）

# 格式: .md + YAML frontmatter
---
name: reinforcement-standards
triggers: ["鋼筋", "rebar", "配筋", "搭接"]
---
## 鋼筋施工規範
- 搭接長度 ≥ 40d...
```

**適用場景：**
- 營建知識庫：用戶提到特定工法/材料 → 自動注入相關規範
- water_alert：提到「水位」「雷達」→ 自動注入感測器操作手冊
- 比現在的 ChromaDB 語意搜尋更精準（exact trigger match）

**預估收益：** AI 回答品質大幅提升，不需用戶主動搜尋知識庫

---

### 🟠 P5：StuckDetector 卡住偵測（來自 OpenHands）

**現狀：** 我們的 Agent 沒有自動偵測卡住的機制
**借鑑：** OpenHands 的 `StuckDetector` 分析歷史事件，偵測是否陷入迴圈

```python
# 新增: ai_modules/stuck_detector.py
class StuckDetector:
    """偵測 AI 是否陷入重複迴圈"""
    
    def is_stuck(history: list) -> bool:
        # 檢查最近 N 個 action 是否重複
        # 偵測語法錯誤迴圈
        # 偵測 empty response 迴圈
```

**適用場景：**
- brain_server 自動化工作流卡住時自動切換策略
- mcp_workflow.py 步驟執行失敗重試超過 3 次時中斷
- water_alert 決策引擎連續產生矛盾決策時告警

---

### 🟡 P6：Agent as Markdown（來自 ECC）

**現狀：** 我們的 `ai_modules/multi_agent.py` 用 Python class 定義 Agent
**借鑑：** ECC 用 Markdown + YAML frontmatter 定義 Agent，更易維護

```markdown
# agents/construction-safety.md
---
name: construction-safety
description: 營建工安專家，自動偵測安全風險
tools: ["Read", "Search", "VisionPipeline"]
model: qwen3:32b
---
你是營建工安專家...
## 檢查項目
1. 個人防護具
2. 墜落防護
...
```

**適用場景：** 把我們的 13 個 Python agent 轉為 Markdown 格式，讓非工程師也能編輯

---

### 🟡 P7：Continuous Learning 持續學習（來自 ECC）

**現狀：** 我們手動更新知識庫
**借鑑：** ECC 的 `/learn` command 自動從工作 session 提煉可重用 pattern

```python
# hooks/post-session.py
# 每次 session 結束後：
# 1. 分析本次 session 的 action/observation 記錄
# 2. 提煉出可重用的 pattern（如：某類問題的最佳解法）
# 3. 自動存入 skills/ 目錄
# 4. 下次遇到類似問題時自動套用
```

**適用場景：**
- 營建現場重複出現的缺失 → 自動產生檢查清單
- water_alert 歷次洪水事件 → 自動更新決策權重
- 客戶反覆問的問題 → 自動產生 FAQ

---

## 三、築未科技平台 vs 兩大專案 功能矩陣

| 能力 | 築未現狀 | OpenHands | ECC | 建議 |
|------|---------|-----------|-----|------|
| 事件匯流排 | ❌ 直接呼叫 | ✅ EventStream | ❌ | **P1 建立** |
| LLM 成本追蹤 | 🟡 次數級 | ✅ Token 級 | ❌ | **P2 增強** |
| 記憶壓縮 | ❌ | ✅ Condenser | ✅ strategic-compact | **P3 建立** |
| 知識自動注入 | 🟡 ChromaDB | ✅ Microagent | ✅ Skills trigger | **P4 建立** |
| 卡住偵測 | ❌ | ✅ StuckDetector | ❌ | **P5 建立** |
| Agent 格式 | Python class | Python class | Markdown | **P6 遷移** |
| 持續學習 | ❌ 手動 | ❌ | ✅ /learn hook | **P7 建立** |
| 安全審計 | 🟡 基本驗證 | ✅ SecurityAnalyzer | ✅ AgentShield | 後續強化 |
| 多平台整合 | GitHub only | ✅ 5 平台 | ❌ | 不急 |
| Docker 沙箱 | ❌ | ✅ Runtime | ❌ | 後續考慮 |
| TDD 工作流 | ❌ | ❌ | ✅ /tdd | **已安裝 ECC** |
| Code Review | ❌ | ❌ | ✅ /code-review | **已安裝 ECC** |

---

## 四、建議實施路線圖

### 第一階段（1-2 週）— 立即可用
- [x] 安裝 ECC 到 `.windsurf/`（已完成，129 個配置檔）
- [ ] **P2** 增強 `usage_metering.py` 加入 token-level 追蹤
- [ ] **P6** 把營建/水情 agent prompt 轉為 Markdown 格式

### 第二階段（3-4 週）— 核心架構
- [ ] **P1** 建立 `core/event_bus.py` 事件匯流排
- [ ] **P3** 建立 `ai_modules/memory_condenser.py`
- [ ] **P4** 建立 Microagent 知識注入系統

### 第三階段（5-8 週）— 進階能力
- [ ] **P5** StuckDetector
- [ ] **P7** Continuous Learning hooks
- [ ] SecurityAnalyzer 安全審計

---

## 五、總結

| 專案 | 最大啟發 | 直接可用 |
|------|---------|---------|
| **OpenHands** | EventStream + Memory Condenser + StuckDetector | 架構模式概念 |
| **ECC** | Agent as Markdown + Continuous Learning + 129 個配置 | **已部署到 .windsurf/** |

**一句話總結：**
> OpenHands 教我們「如何讓 AI Agent 穩定可靠地工作」（事件驅動 + 記憶壓縮 + 卡住偵測），
> ECC 教我們「如何讓 AI Agent 持續進化」（知識注入 + 持續學習 + 結構化工作流）。
> 築未科技平台應該兩者兼取。

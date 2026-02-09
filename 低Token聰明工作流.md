# 最低 Token 聰明工作流 — 築未科技 Skills 運用指南

## 核心原則（3 條）

1. **一則訊息、一個意圖**：一次只問一件事，AI 只會載入匹配的那 1～2 個技能，不會整包塞進 Context。
2. **用關鍵字觸發技能，不要貼長文**：技能靠「名稱 + 描述」匹配；你寫對關鍵字，系統自動載入對應 SKILL.md，無須自己貼規範。
3. **能 @ 檔案就 @，不要整份貼上**：用 `@檔名` 或 `@資料夾` 讓 AI 讀檔，比把程式碼/報表貼在對話裡省 Token。

---

## 意圖 → 關鍵字速查（這樣寫就觸發對應技能）

| 你想做的事 | 建議這樣說（關鍵字） | 會觸發的技能 |
|------------|----------------------|---------------|
| 檢查/寫資料庫、SQL、Postgres | 「檢查這段**資料庫**存取」「**Supabase** 查詢效能」「**Postgres** 索引」 | supabase-postgres-best-practices |
| React/前端元件、效能 | 「這段 **React** 元件」「**前端**效能」「**useEffect** 依賴」 | vercel-react-best-practices |
| 整理點雲、LAS、工地數據 | 「**整理點雲**」「**LAS** 歸檔」「**point_cloud_config** 要改」 | zhewei-pointcloud-cli |
| 營造規範、品質手冊、標線 | 「依**公共工程品質**」「**標線規範**」「**查驗要項**」 | zhewei-construction-standards |
| 除錯、找 bug | 「**除錯**這段」「**root cause**」「重現步驟」 | systematic-debugging |
| 完成前再檢查一遍 | 「**完成前驗證**」「確認路徑/格式再回我」 | verification-before-completion |
| 先寫計畫再做 | 「**先寫計畫**」「拆任務再實作」 | writing-plans |
| 程式碼審查 | 「**code review**」「審這段改動」 | requesting-code-review |
| 寫測試 | 「**TDD**」「為這段加測試」 | test-driven-development |
| 找可用的 Skill | 「**找技能**」「有哪些 skill 可裝」 | find-skills |
| 自己做新技能 | 「**做一個 skill**」「幫我寫 SKILL.md」 | skill-creator |
| PDF/文件處理 | 「**PDF** 擷取/填表」「讀這份文件」 | pdf |
| 行銷文案、SEO | 「**文案**」「**SEO** 檢查」「**行銷**語氣」 | copywriting / seo-audit / marketing-psychology |
| 架構、錯誤處理 | 「**架構**建議」「**錯誤處理**模式」 | architecture-patterns / error-handling-patterns |

---

## 不要做的事（省 Token）

- **不要**每次開頭都貼一大段需求或規範 → 規範已在 SKILL 或 `.cursor/rules`，用關鍵字即可。
- **不要**一則訊息塞「順便幫我 A、B、C」→ 拆成三則，每則觸發不同技能，總 Token 反而更少。
- **不要**把整份檔案貼在對話裡 → 用 `@路徑` 讓 AI 自己讀。
- **不要**在對話裡重複說明架構（D/Z 分流、LaTeX 進度）→ 已在架構守則，alwaysApply 會帶入。

---

## 推薦流程（從窄到寬）

1. **先說清楚「一件事」**  
   例：「檢查 `report_generator.py` 裡寫入 Z 槽的那段是否符合架構守則」  
   → 觸發架構守則 + 可能 verification-before-completion，不會載入 React/點雲/行銷。

2. **需要時再加範圍**  
   同一則裡可加：「只改這檔，不要動 agent_tools 213–234 行」  
   → 減少 AI 讀取其他檔案的機會。

3. **多步驟任務：先要計畫**  
   例：「先寫計畫，再實作：把點雲整理流程接到大腦 API。」  
   → 先觸發 writing-plans，實作階段再觸發 zhewei-pointcloud-cli / 架構守則。

4. **新對話開頭可極簡**  
   例：「延續上一個需求，只做第 2 步。」  
   → 若上一個需求已把檔案/規則帶入，不必重複貼。

---

## 誰常駐、誰按需（Token 分配）

| 類型 | 位置 | 何時載入 | 建議 |
|------|------|----------|------|
| 全域規則 | `.cursorrules`、`.cursor/rules/*.mdc` | 每次對話 | 保持極短，只寫「禁止/必須」 |
| 技能 | `.agents/skills/*/SKILL.md` | 意圖匹配時 | 描述寫清楚關鍵字，細節放 references/ 按需載入 |

也就是說：**常駐的越短，按需的越精準**，整體 Token 最低。

---

## 一句話總結

**一次一件事 + 關鍵字觸發技能 + 用 @ 取代貼文 = 最低 Token 完成聰明工作流。**

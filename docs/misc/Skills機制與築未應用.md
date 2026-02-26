# Skills.sh 四大機制與築未科技應用

---

## 機制原文（版本控制用）

### 1. 智慧語意路由 (Intelligent Routing)

這是 Skills 最「聰明」的功能。您不需要顯式地告訴 AI 要用哪個技能，它會根據您的意圖自動配對。

- **無感觸發**：當您在 Discord 機器人開發中輸入「幫我檢查這段資料庫存取程式碼」，AI 會自動掃描您的技能庫，發現您安裝了 supabase-best-practices，並主動套用該技能中定義的安全與效能規則。
- **多技能協作**：它可以同時載入多個技能（例如同時加載「程式碼風格」與「自動測試生成」），讓 AI 在單次輸出的品質就達到專業標準。

### 2. 上下文持久化 (Context Persistence)

解決了 AI 「健忘」或「每次都要重複教」的問題。

- **版本控制的專業知識**：您可以將營造管理的規範（例如：台灣公共工程品質管理手冊、交通部標線規範）寫成一個 SKILL.md 檔案，放在專案根目錄並進入 Git 版控。
- **團隊一致性**：當您未來招募夥伴或將專案交給同事時，只要他們執行 git pull，他們的 AI 助手（Cursor 或 VS Code）也會立刻擁有與您相同專業水平的判斷能力，確保程式碼風格與業務邏輯的一致。

### 3. Progressive Disclosure (漸進式載入)

這是一項針對處理效能與成本優化的黑科技。

- **不佔用 Token 額度**：以往您要把長篇大論的規範丟進 Prompt，會吃掉大量的對話配額（Token）。
- **按需調度**：Skills.sh 採用三層加載機制。AI 平時只記住技能的「名稱與描述」（Level 1），只有當任務匹配時，才會將具體的指令細節（Level 2）與腳本範例（Level 3）載入 Context，讓您可以同時掛載上百個技能而不影響 AI 的反應速度。

### 4. 深度硬體整合與 CLI 封裝

這對您操作 LiDAR 或 GPS 設備非常有幫助。

- **封裝複雜 CLI**：您可以建立一個技能，內容是「如何操作 infsh 或自定義的 Python CLI 工具來處理 LiDAR 點雲數據」。
- **變成 AI 的「手」**：Skills.sh 本質上是將工具（Tools）與大腦（Skills）結合。它不只是幫您寫程式，還能「教」AI 在什麼時候該去執行您的自動化腳本來處理工地數據。

---

## 築未科技對應

| 機制 | 築未對應 |
|------|----------|
| **智慧語意路由** | 已安裝 supabase-postgres-best-practices、vercel-react-best-practices、架構守則；自建「營造管理規範」「點雲/LiDAR CLI」供語意路由匹配。 |
| **上下文持久化** | `.cursor/rules/架構守則.mdc` 已 alwaysApply；`.agents/skills/` 內自建技能一併版控，git pull 即同步團隊 AI 水準。 |
| **Progressive Disclosure** | 各技能 SKILL.md 僅 Level 1（名稱+描述）常駐；Level 2/3 任務匹配時才載入，可掛載多技能不拖慢反應。 |
| **硬體/CLI 封裝** | `organize_las_pointcloud.py`、`point_cloud_config.py` 已存在；自建技能「點雲/LiDAR CLI」讓 AI 在「整理點雲、LAS、工地數據」等意圖下自動調用。 |

---

*本文件供團隊理解 Skills 機制與專案內技能分工；實際技能定義見 `.agents/skills/` 下各目錄之 `SKILL.md`。*

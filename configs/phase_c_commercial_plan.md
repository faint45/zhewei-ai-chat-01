# Phase C：商用強化規劃

## 訂閱權限
- 依方案（Starter / Pro / Business）開關：butler 執行、各通道讀取、Smart GUI 次數、任務額度。
- 在 `GET /api/butler/inbox`、`POST /api/butler/run` 前加入 entitlement 檢查（讀取 users/subscriptions 表）。

## 審計報表
- butler 執行紀錄：每輪 run 寫入 `reports/task_butler/butler_runs.jsonl`（時間、inbox_count、auto_tasks_created、pending_confirm_count）。
- 自動/待確認統計：可從 pending_confirm 與 agent_tasks 彙整週報。

## SLA 與客戶成功儀表板
- 回應時間：從訊息 timestamp 到首次派工/回覆的時間。
- 漏件率：待確認逾 N 小時未處理筆數。
- 每週節省工時：依任務完成數與預估人工分鐘數計算。
- 儀表板頁：可新增 `brain_workspace/static/butler_dashboard.html` 或接既有 health_dashboard。

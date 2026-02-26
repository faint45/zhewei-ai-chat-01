# Business Playbooks（五套商用模板）

用途：
- 用固定模板把「一句話需求」轉成可執行任務鏈，避免每次重打流程。
- 透過 `POST /api/playbooks/{playbook_id}/run` 直接建立任務。

檔案：
- `procurement_monitor_daily.json`
- `excel_report_automation.json`
- `line_notification_workflow.json`
- `web_form_fill_evidence.json`
- `one_sentence_dispatch_center.json`

執行 API：
- `GET /api/playbooks`：列出模板
- `GET /api/playbooks/{id}`：看模板內容
- `POST /api/playbooks/{id}/run`：執行模板

`run` payload 範例：
```json
{
  "auto_run": true,
  "context": "今天先跑嘉義區域",
  "overrides": {
    "keyword": "嘉義",
    "target_url": "https://example.com"
  }
}
```


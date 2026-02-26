# 全通訊通道規劃（Phase A / B / C）

## Phase A（已接）
- **Email**：快取 `reports/email_inbox_cache.json`（由排程或 webhook 寫入）
- **Discord**：快取 `reports/discord_inbox_cache.json`（由 Jarvis Discord Bot 或 brain 回寫）
- **Telegram**：快取 `reports/telegram_inbox_cache.json`（由 Bot 或排程寫入）

## Phase B（擴平台，待接）
- **WeChat**：官方 API 或 GUI 自動化代理，寫入 `reports/wechat_inbox_cache.json`
- **IG / 臉書 / Threads**：Meta API 或代理，寫入 `reports/ig_inbox_cache.json`、`reports/facebook_inbox_cache.json`、`reports/threads_inbox_cache.json`

各適配器格式與 `brain_modules/message_adapters/` 一致，輸出統一欄位：channel, sender, text, thread_id, message_id, timestamp, priority, attachments。

## Phase C（商用強化）
- 訂閱權限：依方案開關 butler 與各通道
- 審計報表：butler 執行紀錄、自動/待確認統計
- SLA 與客戶成功儀表板：回應時間、漏件率、每週節省工時

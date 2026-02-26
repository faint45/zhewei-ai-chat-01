# 築未科技大腦

## 啟動

| 方式 | 說明 |
|------|------|
| `啟動.bat` | Docker 模式（預設） |
| `啟動.bat local` | 本機模式（無 Docker） |
| **PM2** | `啟動_PM2.bat` 或 `npm run pm2:start` |

**Brain API**：http://127.0.0.1:8002

## PM2

```bash
npm run pm2:start        # 本機全服務（brain + bot + monitor + dashboard + remote-control）
npm run pm2:start:docker # Docker 模式（僅 bot + monitor，brain 在容器內）
npm run pm2:stop
npm run pm2:logs
```

或雙擊 `啟動_PM2.bat` / `停止_PM2.bat`。需先 `npm install` 或 `npm i -g pm2`。

## 診斷

- `診斷外網連線.bat` — 外網連線
- `Jarvis_Training\診斷BOT.bat` — Discord Bot

## 架構

- brain_server：核心 API（port 8002）
- docker-compose：brain + tunnel + ollama + qdrant
- Monitor + Discord Bot：PM2 或 scripts/start_runtime_monitor.bat、Jarvis_Training/run_discord_bot_autostart.bat

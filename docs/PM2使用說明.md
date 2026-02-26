# 築未科技大腦 — PM2 使用說明

## 安裝

```bash
npm install
# 或全域安裝
npm install -g pm2
```

## 啟動

| 指令 | 說明 |
|------|------|
| `啟動_PM2.bat` | 本機全服務 |
| `啟動_PM2.bat docker` | Docker 模式（brain 在容器內） |
| `npm run pm2:start` | 本機全服務 |
| `npm run pm2:start:docker` | Docker 模式 |

## PM2 管理服務

| 服務 | 模式 | 說明 |
|------|------|------|
| brain | 本機 | brain_server.py（port 8002） |
| discord-bot | 兩者 | jarvis_discord_bot.py |
| monitor | 兩者 | scripts/monitor_loop.py（每 60 秒執行一次 monitor_runtime_and_notify） |
| monitoring-dashboard | 本機 | monitoring_dashboard.py（port 8001） |
| remote-control | 本機 | remote_control_server.py（port 8005） |

## 常用指令

```bash
pm2 status
pm2 logs
pm2 restart all
pm2 stop all
pm2 delete all
```

## 前置條件

- Python 已安裝
- `Jarvis_Training/.venv312` 已建立
- ` reports` 目錄會自動建立

## Docker 模式

使用 `ecosystem.docker.config.cjs` 時，需先啟動 Docker 容器：

```bash
docker start zhewei_brain zhe-wei-tech-tunnel-1 zhe-wei-ollama zhewei-qdrant
```

然後執行 `pm2 start ecosystem.docker.config.cjs`。

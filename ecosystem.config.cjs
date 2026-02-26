/**
 * 築未科技大腦 — PM2 生態配置
 * 啟動：pm2 start ecosystem.config.cjs
 * 停止：pm2 stop all
 * 日誌：pm2 logs
 */
const path = require("path");
const ROOT = path.resolve(__dirname);
const PY = path.join(ROOT, "Jarvis_Training", ".venv312", "Scripts", "python.exe");

module.exports = {
  apps: [
    {
      name: "brain",
      script: "brain_server.py",
      interpreter: PY,
      cwd: ROOT,
      instances: 1,
      autorestart: true,
      watch: false,
      env: { PORT: "8002" },
      error_file: path.join(ROOT, "reports", "brain-err.log"),
      out_file: path.join(ROOT, "reports", "brain-out.log"),
    },
    {
      name: "discord-bot",
      script: "jarvis_discord_bot.py",
      interpreter: PY,
      cwd: path.join(ROOT, "Jarvis_Training"),
      instances: 1,
      autorestart: true,
      watch: false,
      error_file: path.join(ROOT, "reports", "discord-bot-err.log"),
      out_file: path.join(ROOT, "reports", "discord-bot-out.log"),
    },
    {
      name: "monitor",
      script: "scripts/monitor_loop.py",
      interpreter: PY,
      cwd: ROOT,
      instances: 1,
      autorestart: true,
      watch: false,
      error_file: path.join(ROOT, "reports", "monitor-err.log"),
      out_file: path.join(ROOT, "reports", "monitor-out.log"),
    },
    {
      name: "monitoring-dashboard",
      script: "monitoring_dashboard.py",
      interpreter: PY,
      cwd: ROOT,
      instances: 1,
      autorestart: true,
      watch: false,
      error_file: path.join(ROOT, "reports", "dashboard-err.log"),
      out_file: path.join(ROOT, "reports", "dashboard-out.log"),
    },
    {
      name: "remote-control",
      script: "remote_control_server.py",
      interpreter: PY,
      cwd: ROOT,
      instances: 1,
      autorestart: true,
      watch: false,
      error_file: path.join(ROOT, "reports", "remote-control-err.log"),
      out_file: path.join(ROOT, "reports", "remote-control-out.log"),
    },
  ],
};

/**
 * 築未科技 — PM2（Docker 模式）
 * Brain 在容器內，PM2 僅管理 monitor + discord-bot
 */
const path = require("path");
const ROOT = path.resolve(__dirname);
const PY = path.join(ROOT, "Jarvis_Training", ".venv312", "Scripts", "python.exe");

module.exports = {
  apps: [
    {
      name: "discord-bot",
      script: "jarvis_discord_bot.py",
      interpreter: PY,
      cwd: path.join(ROOT, "Jarvis_Training"),
      instances: 1,
      autorestart: true,
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
      error_file: path.join(ROOT, "reports", "monitor-err.log"),
      out_file: path.join(ROOT, "reports", "monitor-out.log"),
    },
  ],
};

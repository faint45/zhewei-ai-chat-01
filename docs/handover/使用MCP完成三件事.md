# 築未科技 — 使用 MCP／終端完成三件事

**用途**：對應「git push、完整跑八階段、外網 brain.zhe-wei.net」三項；哪些已由終端／腳本完成、哪些需你手動補齊。

---

## 一、git push

| 項目 | 狀態 | 說明 |
|------|------|------|
| **remote** | 需你提供 URL | 專案目前無 `git remote origin`，無法代你填寫 GitHub repo URL。 |
| **腳本** | ✅ 已建立 | 請在專案根目錄執行：`scripts\git_push.bat https://github.com/你的帳號/你的repo.git`（將 URL 換成你的）。會執行 `git remote add origin <URL>`、`git branch -M main`、`git push -u origin main`。 |

**你要做的**：執行 `scripts\git_push.bat <你的 GitHub repo URL>`（或手動 `git remote add origin <URL>` 後 `git push -u origin main`）。

---

## 二、完整跑八階段

| 項目 | 狀態 | 說明 |
|------|------|------|
| **GEMINI_API_KEY** | ✅ 已加變數，值需你填 | 已在 `.env` 加上 `GEMINI_API_KEY=`（空值）。請用編輯器開啟 `.env`，在 `GEMINI_API_KEY=` 後填入你的 key 並存檔。 |
| **Ollama** | 需本機啟動 | Ollama 未在 PATH 或未安裝時無法代為啟動。若已安裝，請本機執行 Ollama（或「Ollama」應用），讓 `http://localhost:11434` 可用。 |

**你要做的**：在 `.env` 填入 `GEMINI_API_KEY=你的key`；本機啟動 Ollama。之後雙擊 **啟動完整跑.bat** 或執行 `python scripts/run_full_system.py` 即可完整跑八階段。

---

## 三、外網 brain.zhe-wei.net

| 項目 | 狀態 | 說明 |
|------|------|------|
| **Docker Desktop** | ✅ 已嘗試啟動 | 已透過指令啟動 Docker Desktop。 |
| **CLOUDFLARE_TOKEN** | ✅ 已存在於 .env | `.env` 內已有 `CLOUDFLARE_TOKEN`（你先前設定）。 |
| **docker compose up -d** | ✅ 已執行 | 已執行 `docker compose up -d`；容器 `zhewei_brain`、`zhe-wei-tech-tunnel-1`（tunnel）已啟動。 |

**你要做的**：確認本機可連線 https://brain.zhe-wei.net。若 tunnel 容器一直 Restarting，日誌會顯示「Provided Tunnel token is not valid」：**.env 的 CLOUDFLARE_TOKEN 須為「完整 Token」**（從 Cloudflare Zero Trust → Networks → Tunnels → 你的隧道 → **Install connector** 或 **Reinstall** 複製的整段，通常為長字串），不是 tunnel ID（UUID）。更新後執行 `docker compose down` 再 `docker compose up -d`。

---

## 四、摘要

- **git push**：執行 `scripts\git_push.bat <你的 GitHub repo URL>` 完成。
- **完整跑八階段**：在 `.env` 填入 `GEMINI_API_KEY`、本機啟動 Ollama 後，用 **啟動完整跑.bat** 或 `python scripts/run_full_system.py`。
- **外網 brain.zhe-wei.net**：Docker Desktop 已啟動、`docker compose up -d` 已執行；請自行確認 https://brain.zhe-wei.net 可連。

---

*本文件為「使用 MCP 完成」三項對應之執行紀錄與後續手動步驟。*

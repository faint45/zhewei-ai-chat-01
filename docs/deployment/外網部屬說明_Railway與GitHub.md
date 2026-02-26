# 外網部屬說明 — Railway 與 GitHub

## Railway 要錢嗎？

**要。** Railway 已改為付費制（有試用額度），長期跑 brain_server 會產生費用。

---

## 外網「部署到 GitHub」就好？

**不行。** GitHub 只負責**存放程式碼**（版控），**不會幫你跑** brain_server（Python + WebSocket 後端）。

- **GitHub Pages**：只能放**靜態網站**（HTML/JS/CSS），不能跑 Python、不能維持 WebSocket 連線。
- **GitHub Actions**：是做 CI/CD，不是 24 小時掛在網上的伺服器。

所以：**程式碼放 GitHub = 備份與版控**；要讓外網能「連到你的 brain」還是要有一個**真的在跑的服務**＋對外網址。

---

## 建議：外網用 Cloudflare Tunnel，不必用 Railway

| 做法 | 費用 | 說明 |
|------|------|------|
| **Cloudflare Tunnel** | **免費** | brain_server 在你本機跑（或你自己的電腦），Tunnel 把流量轉進來，外網用 https://brain.zhe-wei.net 連。不必租雲端主機。 |
| **Railway** | 付費 | 把 brain_server 部署到 Railway 雲端跑；要錢且需配合他們的環境。 |
| **GitHub** | 免費 | 只放程式碼；外網訪問還是要靠 Tunnel 或 Railway 等「有在跑的服務」。 |

**結論**：  
- **外網部屬**：用 **Cloudflare Tunnel** 即可，不用 Railway。  
- **程式碼**：照常 **push 到 GitHub** 做版控與備份。  
- 流程：本機跑「啟動完整跑.bat」＋ Docker 跑 Tunnel → 外網開 https://brain.zhe-wei.net 。

---

## 操作摘要

1. **GitHub**：`git push` 到你的 repo（例如 faint45/zhewei-ai-chat-01）— 僅版控，不負責外網連線。
2. **外網**：.env 填好 **CLOUDFLARE_TOKEN**（完整 Token），執行 `docker compose up -d`，讓 Tunnel 把 brain.zhe-wei.net 指到你本機的 brain_server。
3. **不必**為了外網去開 Railway 或付費雲端，除非你之後想改成「伺服器在雲端跑、本機不開機」。

詳細 Tunnel 步驟見 **剩下的如何處理.md** 第三節。

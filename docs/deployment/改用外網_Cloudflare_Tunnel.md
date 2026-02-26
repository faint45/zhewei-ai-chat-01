# 改用外網：Cloudflare Tunnel

**目的**：外網用 https://brain.zhe-wei.net 連到你的 brain_server，不必用 Railway。

---

## 一、確認 .env 的 CLOUDFLARE_TOKEN

- **必須是「完整 Token」**：從 Cloudflare 複製時是一大段字串，通常以 **`eyJ...`** 開頭（JWT 格式）。
- **不是隧道 ID**：若目前是 `ceb56784-ec47-43fe-84d9-cb5157828ca0` 這種 UUID，Tunnel 會報錯 `Provided Tunnel token is not valid`，需換成完整 Token。

**取得完整 Token**：
1. 開啟 https://one.dash.cloudflare.com → **Networks** → **Tunnels**。
2. 點你的隧道（或新建一個）。
3. 點 **Reinstall connector** 或 **Install and run a connector**。
4. 畫面上會顯示一段很長的 **Token**（通常以 **`eyJ...`** 開頭的 JWT），**整段**複製貼到 `.env` 的 `CLOUDFLARE_TOKEN=` 後面，存檔。
5. **不要**用隧道 ID（UUID，例如 `ceb56784-ec47-43fe-84d9-cb5157828ca0`）— 用那個會出現 Error 1033 或「origin cert」錯誤。

---

## 二、兩種跑法（擇一）

### 做法 A：全部用 Docker（推薦給外網）

brain_server 與 Tunnel 都在 Docker 跑，本機不用開「啟動完整跑.bat」。

```powershell
cd c:\Users\user\Desktop\zhe-wei-tech
docker compose down
docker compose up -d
```

- 本機：http://localhost:8002 可連 brain_server（埠 8002 對應容器內 8000）。
- 外網：https://brain.zhe-wei.net 經 Tunnel 連到容器內 brain_server。

**Cloudflare 設定**：在該隧道的 **Public Hostname** 新增一筆：
- 子網域／主機名稱：`brain`（或你用的子網域）
- 網域：`zhe-wei.net`（或你的網域）
- 服務類型：**HTTP**
- URL：**brain_server:8000**（因為在 Docker 內網，用服務名 `brain_server`，埠 8000）

若你的 Tunnel 是用「Quick Tunnel」或已用 Token 綁好主機名，可能已設好，只要 Token 正確即可。

### 做法 B：本機跑 brain_server，Docker 只跑 Tunnel

1. 本機雙擊 **啟動完整跑.bat**（brain_server 在 8002）。
2. Docker 只跑 Tunnel，且 Tunnel 要指到本機 8002：
   - 在 Cloudflare 該隧道的 **Public Hostname** 設：URL = **http://host.docker.internal:8002**（Windows/Mac 用 host.docker.internal 指本機）。

若用做法 B，需單獨起 tunnel 容器（不起 brain_server 容器），例如：

```powershell
docker run -d --name cloudflared --restart always -e CLOUDFLARE_TOKEN=你的完整Token cloudflare/cloudflared:latest tunnel --no-autoupdate run --token 你的完整Token
```

或另寫一份只含 `tunnel` 的 docker-compose 使用。

---

## 三、確認成功

- `docker compose ps`：`brain_server` 與 `tunnel` 皆 **Up**。
- 本機：開 http://localhost:8002/health。
- 外網：開 https://brain.zhe-wei.net/health 或 /login。

---

**總結**：外網用 **Cloudflare Tunnel** 就夠；`.env` 的 **CLOUDFLARE_TOKEN** 必須是從「Install connector」複製的**完整 Token**（eyJ... 開頭），**不是**隧道 ID（UUID）。改好後執行 `docker compose up -d` 即可（做法 A）。若曾用 UUID，會出現 Error 1033 或「Cannot determine default origin certificate path」。

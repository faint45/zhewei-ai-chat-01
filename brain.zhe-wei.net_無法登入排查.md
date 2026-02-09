# https://brain.zhe-wei.net 無法登入 — 排查步驟

「登入」指 **Cloudflare Zero Trust Access** 的 OTP 驗證；brain_server 本身無帳密。

---

## 〇、DNS 錯誤：DNS_PROBE_FINISHED_NXDOMAIN

若瀏覽器顯示 **「無法連線到此頁面」** 且錯誤碼為 **DNS_PROBE_FINISHED_NXDOMAIN**，代表 **brain.zhe-wei.net 無法被解析**（網域不存在或 DNS 未設定），請先做以下檢查：

1. **Cloudflare 主儀表板 → 選擇 zhe-wei.net → DNS → Records**
   - 確認有一筆 **CNAME** 或 **A/AAAA** 指向 `brain`（或主機名 `brain.zhe-wei.net`）。
   - 使用 **Tunnel** 時，通常會有一筆：  
     **Name** = `brain`，**Target** = `<你的隧道 ID>.cfargotunnel.com`（或 Zero Trust 建立 Public Hostname 時自動產生的目標）。
   - 若沒有這筆，請在 Zero Trust → **Networks → Tunnels** → 選你的隧道 → **Configure → Public Hostname** 確認已新增 **Subdomain: brain、Domain: zhe-wei.net**；儲存後 Cloudflare 會自動建立對應 DNS（或需手動在 DNS 加一筆 CNAME 指向隧道）。

2. **確認網域在 Cloudflare**
   - 同一 Cloudflare 帳號下，**zhe-wei.net** 必須已加入且 **DNS 由 Cloudflare 代管**（Nameservers 已改為 Cloudflare 提供的）。

3. **稍等或清除 DNS 快取**
   - 剛改 DNS 可等數分鐘；本機清除快取：  
     Windows：`ipconfig /flushdns`；或換網路／用無痕模式再試一次。

---

## 〇‑2. 錯誤 1033：Cloudflare Tunnel error

若畫面顯示 **Error 1033**、說明「Cloudflare is currently unable to resolve it」或「Ensure that cloudflared is running」：

- **原因**：DNS 已指向隧道，但 **cloudflared（隧道程式）沒在本機執行或未連上 Cloudflare**。
- **處理**：
  1. **啟動 cloudflared**  
     - 若用 **Docker Compose**：在專案根目錄執行 `docker compose up -d`（會同時跑 brain_server 與 tunnel）。  
     - 若用 **本機**：先確認 `python brain_server.py` 或 Windows 服務已在 8000 埠跑，再執行  
       `cloudflared tunnel --no-autoupdate run --token <你的CLOUDFLARE_TOKEN>`  
       （Token 在 Zero Trust → Networks → Tunnels → 你的隧道 → 可複製）。
  2. 確認 **brain_server** 在 **localhost:8000** 有回應（本機開 `http://localhost:8000/health` 有 JSON）。
  3. 等約 30 秒讓隧道連線建立，再重新整理 https://brain.zhe-wei.net 。

---

## 〇‑3. Tunnel Token 無效：Provided Tunnel token is not valid

若執行 `docker compose logs tunnel` 看到 **"Provided Tunnel token is not valid"**：

- **原因**：`.env` 內的 **CLOUDFLARE_TOKEN** 為空、打錯或已過期。
- **處理**：
  1. 開啟 **https://one.dash.cloudflare.com** → **Networks** → **Tunnels** → 點你的隧道（例如 ID: 9d65a17a-9915-475b-9499-7508e457d0e1）。
  2. 畫面上有 **Reinstall connector** 或 **Install and run a connector**，點進去後複製**新的 Token**（格式通常為 `eyJ...` 開頭）。
  3. 編輯專案根目錄 **`.env`**，將 `CLOUDFLARE_TOKEN=` 後面改為剛複製的 Token，儲存。
  4. 重啟容器：`docker compose down` → `docker compose up -d`。
  5. 約 30 秒後再開 https://brain.zhe-wei.net/health 測試。

---

## 一、確認地端服務正常

1. **brain_server 是否在跑**
   - 本機瀏覽器開：`http://localhost:8000/health`
   - 應回傳 `{"status":"healthy", ...}`。若無法連線，先啟動大腦（`python brain_server.py` 或 Windows 服務 ZheweiBrain）。

2. **隧道 (cloudflared) 是否在跑**
   - Docker Compose：`docker compose ps` 看 `brain_server`、`tunnel` 是否 Up。
   - 本機 tunnel：確認執行 `cloudflared tunnel run --token <TOKEN>` 的視窗/程序還在，且無錯誤。

---

## 二、Cloudflare Access（OTP 登入）

1. **是否有出現 Cloudflare 登入頁**
   - **沒有**：可能是隧道未對應到 brain.zhe-wei.net，或 Access 未套用在此網域。
   - **有**：請確認輸入的 **信箱** 與 Zero Trust 裡 Ah-Kai-Only 設定的 **Emails** 一致。

2. **OTP 驗證碼**
   - 收信（含垃圾郵件）取得一次性驗證碼。
   - 若沒收到：到 Zero Trust → **Settings → Authentication → Login methods** 確認 **One-time PIN** 已啟用，且 SMTP 或 Cloudflare 郵件設定正確。

3. **Access 應用是否套用在 brain.zhe-wei.net**
   - Zero Trust → **Access → Applications** → 新增或編輯應用。
   - **Application domain** 填：`brain.zhe-wei.net`（或 `*.zhe-wei.net` 依需求）。
   - **Access policy** 選 **Ah-Kai-Only**（Include: Emails = 你的信箱，認證方式：One-time PIN）。

---

## 三、Public Hostname（隧道對應）

- Zero Trust → **Networks → Tunnels** → 選 **Zhewei_Brain_Home** → **Configure → Public Hostname**。
- 確認有一筆：**Subdomain** = `brain`，**Domain** = `zhe-wei.net`，**URL** = `localhost:8000`。
- 若沒有或網域錯，遠端打 https://brain.zhe-wei.net 會連不到地端 8000。

---

## 四、WebSocket（管理介面對話)

- 若網頁能開但「發送指令」無反應，多半是 WebSocket 被關閉。
- Cloudflare 主儀表板 → **zhe-wei.net** → **Network** → **WebSockets** 設為 **On**。

---

## 五、快速檢查表

| 項目 | 檢查方式 |
|------|----------|
| 地端 8000 | 本機開 `http://localhost:8000/health` 有 JSON |
| 隧道程序 | Docker 或 cloudflared 程序在跑、無報錯 |
| Public Hostname | brain.zhe-wei.net → localhost:8000 |
| Access 應用 | brain.zhe-wei.net 套用 Ah-Kai-Only，OTP 開啟 |
| 信箱 | 與 Access 政策內 Emails 一致，收得到 OTP |
| WebSockets | Cloudflare 主儀表板 → zhe-wei.net → Network → On |

若仍無法登入，請描述：是「完全打不開網址」、「有 Cloudflare 登入頁但驗證失敗」、還是「登入後頁面空白/錯誤」？方便對應到上述哪一段排查。

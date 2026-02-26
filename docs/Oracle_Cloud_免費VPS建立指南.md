# 築未科技 — Oracle Cloud 免費 VPS 建立指南

**目的**：建立免費雲端備援伺服器，本地故障時可接手 brain.zhe-wei.net。

---

## 一、申請帳號

1. 前往 https://signup.oraclecloud.com/
2. 填寫 Email、國家、姓名
3. 驗證 Email 後完成註冊
4. 需信用卡驗證（免費方案不會扣款，僅驗證身份）

---

## 二、建立 VM 實例

### 步驟 1：進入 Compute

1. 登入 Oracle Cloud Console
2. 左上選單 → **Compute** → **Instances**

### 步驟 2：建立 Instance

1. 點 **Create instance**
2. **Name**：`zhewei-backup`（自訂）
3. **Placement**：保持預設
4. **Image and shape**：
   - Image：**Ubuntu 22.04**
   - Shape：展開 **Change shape**
   - 選 **VM.Standard.E2.1.Micro**（1 vCPU、1GB RAM，免費 tier）
   - 若 ARM 地區有 **VM.Standard.A1.Flex**，可選 2 vCPU、1GB（免費）
5. **Networking**：
   - 若無 VCN：選 **Create new virtual cloud network**，其餘預設
   - 若有 VCN：選既有 VCN
   - **Assign a public IPv4 address**：勾選
6. **Add SSH keys**：
   - 選 **Generate a key pair for me** 或上傳既有公鑰
   - 下載私鑰（.key）妥善保存
7. 點 **Create**

### 步驟 3：開放防火牆

1. 實例建立後，點實例名稱
2. 左側 **Subnet** → 點進去的 VCN → **Security Lists** → **Default Security List**
3. **Add Ingress Rules**：
   - Source CIDR：`0.0.0.0/0`
   - IP Protocol：TCP
   - Destination Port：22（SSH）、8002（brain_server）
4. 儲存

### 步驟 4：取 SSH 連線資訊

1. 實例頁面顯示 **Public IP address**
2. 預設使用者：`ubuntu`（Ubuntu 映像）
3. 連線指令：
   ```bash
   ssh -i /path/to/your-key.key ubuntu@<PUBLIC_IP>
   ```

---

## 三、首次登入後必做

```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 登出再登入後 docker 才生效

# 安裝 Rclone
curl https://rclone.org/install.sh | sudo bash
```

---

## 四、複製 Rclone 設定（含 gdrive）

在本機 PowerShell：

```powershell
# 檢視本機 rclone config 路徑
# Windows: %APPDATA%\rclone\rclone.conf
scp -i C:\path\to\your-key.key "$env:APPDATA\rclone\rclone.conf" ubuntu@<PUBLIC_IP>:~/.config/rclone/rclone.conf
```

或於 VPS 上執行 `rclone config` 重新建立 gdrive 遠端（需瀏覽器 OAuth）。

---

## 五、部署備援腳本

請依 `雲端備援切換操作手冊.md` 執行 `deploy_failover_to_vps.sh` 或手動複製腳本至 `/opt/zhewei/`。

---

## 六、免費 tier 限制

| 項目 | 限制 |
|------|------|
| E2.1.Micro | 2 個實例（總計） |
| 儲存 | 200GB Block Volume |
| 流量 | 每月 10TB 出站 |
| ARM A1.Flex | 4 vCPU、24GB RAM 總計（視地區） |

注意：建立實例時勿選付費 shape，否則會產生費用。

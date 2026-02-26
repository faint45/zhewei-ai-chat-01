# Oracle Cloud VM 設定指南（繁體中文）

## 📋 目錄
1. [取得連線資訊](#取得連線資訊)
2. [方法一：自動化部署（推薦）](#方法一自動化部署推薦)
3. [方法二：手動設定](#方法二手動設定)
4. [驗證部署](#驗證部署)

---

## 取得連線資訊

### 步驟 1：找到公用 IP

1. 登入 https://cloud.oracle.com
2. 點擊左側選單 ☰ → **運算** → **執行處理**
3. 點擊您的 VM 名稱（例如：`zhewei-hybrid-cloud`）
4. 複製 **公用 IP 位址**（格式：`132.145.xxx.xxx`）

### 步驟 2：找到 SSH 私鑰

您在建立 VM 時下載的私鑰檔案，通常在：
```
C:\Users\您的使用者名稱\Downloads\ssh-key-2025-02-16.key
```

---

## 方法一：自動化部署（推薦）

### 使用 PowerShell 一鍵部署

**在專案根目錄開啟 PowerShell，執行：**

```powershell
# 替換成您的實際資訊
$IP = "132.145.xxx.xxx"  # 您的公用 IP
$KEY = "C:\Users\您的使用者名稱\Downloads\ssh-key-xxxx.key"  # 您的私鑰路徑

# 執行部署腳本
.\scripts\oracle_quick_deploy.ps1 -PublicIP $IP -PrivateKeyPath $KEY
```

**腳本會自動完成：**
- ✅ 測試 SSH 連線
- ✅ 上傳設定腳本
- ✅ 安裝 Docker
- ✅ 建立 8GB Swap
- ✅ 設定防火牆
- ✅ 記憶體優化

**預計時間：5-10 分鐘**

---

## 方法二：手動設定

### 步驟 1：SSH 連線

**Windows PowerShell：**
```powershell
# 設定私鑰權限
icacls "C:\Users\...\ssh-key-xxxx.key" /inheritance:r
icacls "C:\Users\...\ssh-key-xxxx.key" /grant:r "$($env:USERNAME):(R)"

# SSH 連線
ssh -i "C:\Users\...\ssh-key-xxxx.key" opc@132.145.xxx.xxx
```

### 步驟 2：執行設定腳本

**連線成功後，在 VM 中執行：**

```bash
# 下載設定腳本
curl -o /tmp/setup.sh https://raw.githubusercontent.com/您的repo/main/scripts/oracle_vm_setup.sh

# 執行腳本
sudo bash /tmp/setup.sh
```

**或手動執行以下命令：**

```bash
# 1. 系統更新
sudo apt update && sudo apt upgrade -y

# 2. 安裝 Docker
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker opc

# 3. 建立 8GB Swap（重要！）
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 4. 記憶體優化
sudo apt install -y earlyoom
sudo systemctl enable earlyoom
sudo systemctl start earlyoom
echo 'vm.swappiness=80' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# 5. 設定時區
sudo timedatectl set-timezone Asia/Taipei

# 6. 建立專案目錄
sudo mkdir -p /opt/zhewei
sudo chown opc:opc /opt/zhewei

# 7. 設定防火牆
sudo apt install -y ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 11434/tcp
echo "y" | sudo ufw enable
```

### 步驟 3：驗證設定

```bash
# 檢查記憶體（應該看到 8GB Swap）
free -h

# 檢查 Docker
docker --version

# 檢查防火牆
sudo ufw status
```

---

## 驗證部署

### 檢查系統狀態

```bash
# 在 VM 中執行
sudo /opt/zhewei/health_check.sh
```

**應該看到：**
```
=== Zhewei Hybrid Health Check ===
時間: 2025-02-16 14:00:00

--- 記憶體使用 ---
              total        used        free      shared  buff/cache   available
Mem:          948Mi       200Mi       500Mi       1.0Mi       248Mi       650Mi
Swap:         8.0Gi       0.0Gi       8.0Gi

--- 磁碟使用 ---
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        46G  5.0G   39G  12% /

--- Docker 狀態 ---
Docker version 24.0.7, build afdd53b

=== 檢查完成 ===
```

---

## 🎯 下一步

基礎設定完成後，請繼續：

1. **上傳專案程式碼**
2. **設定環境變數**
3. **部署 Docker 服務**
4. **設定 Cloudflare Tunnel**

詳細步驟請參考：`docs/deployment/ORACLE_CLOUD_HYBRID_GUIDE.md`

---

## 🚨 常見問題

### Q1: SSH 連線失敗
**檢查：**
- 公用 IP 是否正確
- 防火牆是否開放 22 端口（Oracle 安全性清單）
- 私鑰權限是否正確

### Q2: 記憶體不足
**解決：**
- 確認 Swap 已建立：`free -h`
- 如果沒有，執行：`sudo swapon /swapfile`

### Q3: Docker 無法啟動
**解決：**
```bash
sudo systemctl status docker
sudo journalctl -u docker -n 50
```

---

## 📞 需要協助？

如果遇到問題，請提供：
1. 錯誤訊息
2. `free -h` 輸出
3. `docker ps` 輸出

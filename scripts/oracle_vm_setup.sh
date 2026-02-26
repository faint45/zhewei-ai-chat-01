#!/bin/bash
# Oracle Cloud VM 自動設定腳本
# 在 VM 建立後執行此腳本

set -e

echo "=========================================="
echo "Oracle Cloud VM 自動設定腳本"
echo "針對 1GB RAM 免費方案優化"
echo "=========================================="

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 檢查是否為 root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}請使用 sudo 執行此腳本${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/8] 系統更新...${NC}"
apt update && apt upgrade -y

echo -e "${YELLOW}[2/8] 安裝必要套件...${NC}"
apt install -y curl wget git vim htop docker.io docker-compose net-tools

# 啟動 Docker
systemctl enable docker
systemctl start docker
usermod -aG docker opc

echo -e "${GREEN}✓ Docker 安裝完成${NC}"
docker --version

echo -e "${YELLOW}[3/8] 建立 8GB Swap（重要！）...${NC}"
if [ ! -f /swapfile ]; then
    fallocate -l 8G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo -e "${GREEN}✓ Swap 建立完成${NC}"
else
    echo -e "${GREEN}✓ Swap 已存在${NC}"
fi

# 顯示記憶體狀態
echo ""
echo "記憶體狀態："
free -h
echo ""

echo -e "${YELLOW}[4/8] 記憶體優化設定...${NC}"
# 安裝 early OOM killer
apt install -y earlyoom
systemctl enable earlyoom
systemctl start earlyoom

# 設定 swappiness
echo 'vm.swappiness=80' >> /etc/sysctl.conf
sysctl -p

echo -e "${GREEN}✓ 記憶體優化完成${NC}"

echo -e "${YELLOW}[5/8] 設定時區...${NC}"
timedatectl set-timezone Asia/Taipei
echo -e "${GREEN}✓ 時區設定為台灣時間${NC}"
timedatectl

echo -e "${YELLOW}[6/8] 建立專案目錄...${NC}"
mkdir -p /opt/zhewei
cd /opt/zhewei
chown opc:opc /opt/zhewei

echo -e "${GREEN}✓ 專案目錄建立完成${NC}"

echo -e "${YELLOW}[7/8] 設定防火牆...${NC}"
# Oracle Cloud 使用安全性清單，這裡安裝 UFW 作為第二層保護
apt install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw allow 8000/tcp # Brain Server
ufw allow 8001/tcp # CodeSim
ufw allow 8003/tcp # Smart Bridge
ufw allow 8020/tcp # CMS
ufw allow 8025/tcp # Prediction
ufw allow 11434/tcp # Ollama

echo "y" | ufw enable
systemctl enable ufw

echo -e "${GREEN}✓ 防火牆設定完成${NC}"

echo -e "${YELLOW}[8/8] 建立健康檢查腳本...${NC}"
cat > /opt/zhewei/health_check.sh << 'EOF'
#!/bin/bash
# 健康檢查腳本

echo "=== Zhewei Hybrid Health Check ==="
echo "時間: $(date)"
echo ""

# 檢查記憶體
echo "--- 記憶體使用 ---"
free -h

# 檢查磁碟
echo ""
echo "--- 磁碟使用 ---"
df -h /

# 檢查 Docker
echo ""
echo "--- Docker 狀態 ---"
if command -v docker &> /dev/null; then
    docker ps --format "table {{.Names}}\t{{.Status}}"
else
    echo "Docker 未安裝"
fi

echo ""
echo "=== 檢查完成 ==="
EOF

chmod +x /opt/zhewei/health_check.sh
chown opc:opc /opt/zhewei/health_check.sh

echo -e "${GREEN}✓ 健康檢查腳本建立完成${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}VM 基礎設定完成！${NC}"
echo "=========================================="
echo ""
echo "請執行以下步驟繼續："
echo "1. 上傳專案程式碼到 /opt/zhewei"
echo "2. 設定 .env 檔案"
echo "3. 執行 docker-compose up -d"
echo ""
echo "公用 IP: $(curl -s ifconfig.me)"
echo ""

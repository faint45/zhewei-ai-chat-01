#!/bin/bash
# Zhe-Wei Tech — Contabo Tokyo VPS Setup (8GB RAM)
# Run: ssh root@<VPS_IP> 'bash -s' < contabo_vps_setup.sh
# Or:  scp contabo_vps_setup.sh root@<IP>:/tmp/ && ssh root@<IP> 'bash /tmp/contabo_vps_setup.sh'

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

WORK_DIR="/opt/zhewei"
PROJECT_DIR="$WORK_DIR/zhe-wei-tech"

echo "=========================================="
echo " Contabo Tokyo VPS Setup (8GB)"
echo " Zhe-Wei Tech Failover System"
echo "=========================================="

# ── 1. System update ──
echo -e "${YELLOW}[1/8] System update...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt update && apt upgrade -y -q

# ── 2. Install essentials ──
echo -e "${YELLOW}[2/8] Installing packages...${NC}"
apt install -y -q \
    curl wget git vim htop \
    docker.io docker-compose-plugin \
    net-tools rclone ufw fail2ban

systemctl enable docker
systemctl start docker

echo -e "${GREEN}OK Docker $(docker --version)${NC}"

# ── 3. Swap (2GB extra for safety) ──
echo -e "${YELLOW}[3/8] Setting up 2GB swap...${NC}"
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo -e "${GREEN}OK Swap created${NC}"
else
    echo -e "${GREEN}OK Swap exists${NC}"
fi

# ── 4. System tuning ──
echo -e "${YELLOW}[4/8] System tuning...${NC}"
cat >> /etc/sysctl.conf << 'EOF'
vm.swappiness=30
vm.vfs_cache_pressure=100
net.core.somaxconn=1024
net.ipv4.tcp_tw_reuse=1
EOF
sysctl -p 2>/dev/null || true
echo -e "${GREEN}OK Tuned${NC}"

# ── 5. Timezone ──
echo -e "${YELLOW}[5/8] Setting timezone...${NC}"
timedatectl set-timezone Asia/Taipei
echo -e "${GREEN}OK Asia/Taipei${NC}"

# ── 6. Create project directory ──
echo -e "${YELLOW}[6/8] Creating project directory...${NC}"
mkdir -p "$WORK_DIR" "$PROJECT_DIR" "$PROJECT_DIR/logs"
echo -e "${GREEN}OK $WORK_DIR${NC}"

# ── 7. Firewall ──
echo -e "${YELLOW}[7/8] Firewall setup...${NC}"
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable
systemctl enable ufw
echo -e "${GREEN}OK Firewall configured${NC}"

# ── 8. Failover cron + log rotation ──
echo -e "${YELLOW}[8/8] Setting up failover cron...${NC}"

# Copy health check script (will be synced via rclone later)
cat > "$WORK_DIR/failover_health_check.sh" << 'HEALTH_SCRIPT'
#!/bin/bash
set -euo pipefail

WORK_DIR="${ZHEWEI_WORK_DIR:-/opt/zhewei}"
PROJECT_DIR="$WORK_DIR/zhe-wei-tech"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.failover.yml"
STATE_FILE="$WORK_DIR/.failover_state"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"
LOCAL_HEALTH_URL="${LOCAL_HEALTH_URL:-https://zhe-wei.net/health}"
HEALTH_TIMEOUT=10
FAIL_THRESHOLD=3
FAIL_COUNT_FILE="$WORK_DIR/.fail_count"

log() { echo "$LOG_PREFIX $1"; }
get_state() { [ -f "$STATE_FILE" ] && cat "$STATE_FILE" || echo "standby"; }
set_state() { echo "$1" > "$STATE_FILE"; log "State -> $1"; }
get_fail_count() { [ -f "$FAIL_COUNT_FILE" ] && cat "$FAIL_COUNT_FILE" || echo "0"; }
reset_fail_count() { echo "0" > "$FAIL_COUNT_FILE"; }
increment_fail_count() { echo $(( $(get_fail_count) + 1 )) > "$FAIL_COUNT_FILE"; }

check_local_health() {
    local code
    code=$(curl -sf -o /dev/null -w "%{http_code}" --connect-timeout $HEALTH_TIMEOUT "$LOCAL_HEALTH_URL" 2>/dev/null) || code="000"
    [ "$code" = "200" ]
}

start_failover() {
    log ">>> ACTIVATING FAILOVER <<<"
    cd "$PROJECT_DIR"

    if command -v rclone &>/dev/null; then
        RCLONE_REMOTE="${RCLONE_REMOTE:-gdrive}"
        if rclone listremotes 2>/dev/null | grep -q "^${RCLONE_REMOTE}:$"; then
            log "Syncing from cloud..."
            rclone sync "${RCLONE_REMOTE}:Zhewei_Brain/tech_repo_backup" "$PROJECT_DIR" \
                --exclude ".venv312/" --exclude "venv*/" --exclude "node_modules/" \
                --exclude "ComfyUI/" --exclude "**/__pycache__/" --exclude ".git/" \
                --quiet 2>/dev/null || log "[WARN] code sync failed"
            rclone sync "${RCLONE_REMOTE}:Zhewei_Brain/workspace_backup" "$PROJECT_DIR/brain_workspace" \
                --quiet 2>/dev/null || true
            rclone copy "${RCLONE_REMOTE}:Zhewei_Brain/env_backup/.env" "$PROJECT_DIR/" \
                --quiet 2>/dev/null || true
            rclone sync "${RCLONE_REMOTE}:Zhewei_Brain/memory_backup" "$PROJECT_DIR/zhewei_memory" \
                --quiet 2>/dev/null || true
        fi
    fi

    docker compose -f "$COMPOSE_FILE" up -d 2>&1 || { log "[ERROR] compose up failed"; return 1; }
    set_state "active"
    log "Failover ACTIVE"

    [ -n "${NTFY_TOPIC:-}" ] && curl -sf -d "FAILOVER ACTIVATED $(date)" \
        "https://notify.zhewei.tech/$NTFY_TOPIC" 2>/dev/null || true
}

stop_failover() {
    log ">>> DEACTIVATING FAILOVER <<<"
    cd "$PROJECT_DIR"
    docker compose -f "$COMPOSE_FILE" down 2>&1 || true
    set_state "standby"
    log "Failover STANDBY"

    [ -n "${NTFY_TOPIC:-}" ] && curl -sf -d "Local recovered, failover off $(date)" \
        "https://notify.zhewei.tech/$NTFY_TOPIC" 2>/dev/null || true
}

state=$(get_state)

if check_local_health; then
    reset_fail_count
    [ "$state" = "active" ] && stop_failover
else
    increment_fail_count
    fc=$(get_fail_count)
    log "Health FAIL ($fc/$FAIL_THRESHOLD)"
    if [ "$state" = "standby" ] && [ "$fc" -ge "$FAIL_THRESHOLD" ]; then
        start_failover
        reset_fail_count
    elif [ "$state" = "active" ]; then
        docker compose -f "$COMPOSE_FILE" ps --status running 2>/dev/null | grep -q "zhewei_brain" || {
            log "Restarting failed containers..."
            docker compose -f "$COMPOSE_FILE" up -d 2>&1 || true
        }
    fi
fi
HEALTH_SCRIPT

chmod +x "$WORK_DIR/failover_health_check.sh"

# Cron every 2 minutes
CRON_LINE="*/2 * * * * $WORK_DIR/failover_health_check.sh >> $WORK_DIR/failover.log 2>&1"
(crontab -l 2>/dev/null | grep -v "failover_health_check"; echo "$CRON_LINE") | crontab -

# Log rotation
cat > /etc/logrotate.d/zhewei-failover << EOF
$WORK_DIR/failover.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
EOF

echo -e "${GREEN}OK Cron installed${NC}"

# ── Pre-pull Docker images ──
echo ""
echo -e "${YELLOW}Pre-pulling Docker images...${NC}"
docker pull nginx:alpine &
docker pull cloudflare/cloudflared:latest &
docker pull ollama/ollama:latest &
wait
echo -e "${GREEN}OK Images pulled${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN} Setup complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Setup rclone (Google Drive):"
echo "     rclone config"
echo "     # Create remote named 'gdrive' → Google Drive"
echo ""
echo "  2. Initial sync from Google Drive:"
echo "     rclone sync gdrive:Zhewei_Brain/tech_repo_backup $PROJECT_DIR \\"
echo "       --exclude '.venv312/' --exclude 'venv*/' --exclude 'node_modules/' \\"
echo "       --exclude 'ComfyUI/' --exclude '**/__pycache__/' --exclude '.git/'"
echo "     rclone sync gdrive:Zhewei_Brain/workspace_backup $PROJECT_DIR/brain_workspace"
echo "     rclone copy gdrive:Zhewei_Brain/env_backup/.env $PROJECT_DIR/"
echo ""
echo "  3. Add CLOUDFLARE_FAILOVER_TOKEN to .env:"
echo "     echo 'CLOUDFLARE_FAILOVER_TOKEN=<token>' >> $PROJECT_DIR/.env"
echo ""
echo "  4. Pull Ollama models:"
echo "     docker run --rm -v ollama_models:/root/.ollama ollama/ollama pull qwen2.5:3b"
echo "     docker run --rm -v ollama_models:/root/.ollama ollama/ollama pull nomic-embed-text"
echo ""
echo "  5. Test failover:"
echo "     cd $PROJECT_DIR && docker compose -f docker-compose.failover.yml up -d"
echo ""
echo "System info:"
echo "  IP:     $(curl -s ifconfig.me 2>/dev/null || echo 'unknown')"
echo "  RAM:    $(free -h | awk '/Mem:/{print $2}')"
echo "  Disk:   $(df -h / | awk 'NR==2{print $4}') free"
echo ""

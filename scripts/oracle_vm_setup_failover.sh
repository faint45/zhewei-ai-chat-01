#!/bin/bash
# Zhe-Wei Tech — Oracle Cloud VM Failover Setup
# One-click setup for Oracle Cloud Always Free (1GB RAM)
# Run: curl -sL <url> | sudo bash
# Or:  sudo bash oracle_vm_setup_failover.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

WORK_DIR="/opt/zhewei"
PROJECT_DIR="$WORK_DIR/zhe-wei-tech"

echo "=========================================="
echo "Oracle Cloud Failover Setup"
echo "1GB RAM optimized for Zhe-Wei Tech"
echo "=========================================="

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run with sudo${NC}"
    exit 1
fi

# ── 1. System update ──
echo -e "${YELLOW}[1/9] System update...${NC}"
apt update && apt upgrade -y -q

# ── 2. Install essentials ──
echo -e "${YELLOW}[2/9] Installing packages...${NC}"
apt install -y -q curl wget git vim htop docker.io docker-compose-plugin net-tools rclone

systemctl enable docker
systemctl start docker

REAL_USER="${SUDO_USER:-ubuntu}"
usermod -aG docker "$REAL_USER" 2>/dev/null || true

echo -e "${GREEN}OK Docker $(docker --version)${NC}"

# ── 3. Swap (critical for 1GB RAM) ──
echo -e "${YELLOW}[3/9] Setting up 4GB swap...${NC}"
if [ ! -f /swapfile ]; then
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo -e "${GREEN}OK Swap created${NC}"
else
    echo -e "${GREEN}OK Swap exists${NC}"
fi

# ── 4. Memory optimization ──
echo -e "${YELLOW}[4/9] Memory optimization...${NC}"
apt install -y -q earlyoom
systemctl enable earlyoom
systemctl start earlyoom

# Aggressive swapping for 1GB
cat >> /etc/sysctl.conf << 'EOF'
vm.swappiness=80
vm.vfs_cache_pressure=200
vm.min_free_kbytes=32768
EOF
sysctl -p 2>/dev/null || true

echo -e "${GREEN}OK Memory optimized${NC}"

# ── 5. Timezone ──
echo -e "${YELLOW}[5/9] Setting timezone...${NC}"
timedatectl set-timezone Asia/Taipei
echo -e "${GREEN}OK Asia/Taipei${NC}"

# ── 6. Create project directory ──
echo -e "${YELLOW}[6/9] Creating project directory...${NC}"
mkdir -p "$WORK_DIR" "$PROJECT_DIR" "$PROJECT_DIR/logs"
chown -R "$REAL_USER:$REAL_USER" "$WORK_DIR"
echo -e "${GREEN}OK $WORK_DIR${NC}"

# ── 7. Firewall ──
echo -e "${YELLOW}[7/9] Firewall setup...${NC}"
apt install -y -q ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable
systemctl enable ufw
echo -e "${GREEN}OK Firewall configured${NC}"

# ── 8. Failover health check cron ──
echo -e "${YELLOW}[8/9] Setting up failover cron...${NC}"

cat > "$WORK_DIR/failover_health_check.sh" << 'HEALTH_EOF'
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

    # Sync from cloud storage
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

    docker compose -f "$COMPOSE_FILE" up -d --build 2>&1 || { log "[ERROR] compose up failed"; return 1; }
    set_state "active"
    log "Failover ACTIVE"

    # Notify
    [ -n "${NTFY_TOPIC:-}" ] && curl -sf -d "FAILOVER ACTIVATED $(date)" \
        "https://notify.zhewei.tech/$NTFY_TOPIC" 2>/dev/null || true
}

stop_failover() {
    log ">>> DEACTIVATING FAILOVER (local recovered) <<<"
    cd "$PROJECT_DIR"
    docker compose -f "$COMPOSE_FILE" down 2>&1 || true
    set_state "standby"
    log "Failover STANDBY"

    [ -n "${NTFY_TOPIC:-}" ] && curl -sf -d "Local recovered, failover off $(date)" \
        "https://notify.zhewei.tech/$NTFY_TOPIC" 2>/dev/null || true
}

# ── Main ──
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
HEALTH_EOF

chmod +x "$WORK_DIR/failover_health_check.sh"
chown "$REAL_USER:$REAL_USER" "$WORK_DIR/failover_health_check.sh"

# Add cron (every 2 minutes)
CRON_LINE="*/2 * * * * $WORK_DIR/failover_health_check.sh >> $WORK_DIR/failover.log 2>&1"
(crontab -u "$REAL_USER" -l 2>/dev/null | grep -v "failover_health_check"; echo "$CRON_LINE") | crontab -u "$REAL_USER" -

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

echo -e "${GREEN}OK Cron installed (every 2 min)${NC}"

# ── 9. Summary ──
echo -e "${YELLOW}[9/9] Docker image pre-pull...${NC}"
docker pull nginx:alpine 2>/dev/null || true
docker pull cloudflare/cloudflared:latest 2>/dev/null || true
echo -e "${GREEN}OK Base images pulled${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}Setup complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Setup rclone (Google Drive):"
echo "     sudo -u $REAL_USER rclone config"
echo "     # Create remote named 'gdrive' with Google Drive"
echo ""
echo "  2. Create Cloudflare failover tunnel:"
echo "     Go to Cloudflare Zero Trust > Tunnels"
echo "     Create a NEW tunnel named 'zhewei-failover'"
echo "     Copy the token to .env as CLOUDFLARE_FAILOVER_TOKEN"
echo ""
echo "  3. Copy .env to VPS:"
echo "     scp .env $REAL_USER@$(curl -s ifconfig.me 2>/dev/null || echo '<VPS_IP>'):/opt/zhewei/zhe-wei-tech/"
echo ""
echo "  4. Initial sync (run from local Windows):"
echo "     powershell -File scripts/sync_to_oracle.ps1"
echo ""
echo "  5. Test failover manually:"
echo "     sudo -u $REAL_USER $WORK_DIR/failover_health_check.sh"
echo ""
echo "Public IP: $(curl -s ifconfig.me 2>/dev/null || echo 'unknown')"
echo "Memory:    $(free -h | awk '/Mem:/{print $2}') RAM + $(free -h | awk '/Swap:/{print $2}') Swap"
echo ""

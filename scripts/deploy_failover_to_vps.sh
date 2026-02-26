#!/bin/bash
# 築未科技 — 部署備援腳本到 Oracle Cloud VPS
# 在「本機」執行，透過 SCP 將腳本與配置上傳至 VPS
# 用法：./deploy_failover_to_vps.sh <VPS_IP> [SSH_KEY_PATH]
# 例：  ./deploy_failover_to_vps.sh 123.45.67.89 ~/.ssh/oracle_key

set -e

VPS_IP="${1:?Usage: $0 <VPS_IP> [SSH_KEY_PATH]}"
SSH_KEY="${2:-}"
SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10)
[ -n "$SSH_KEY" ] && SSH_OPTS+=(-i "$SSH_KEY")

REMOTE_USER="${REMOTE_USER:-ubuntu}"
WORK_DIR="/opt/zhewei"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "[1/4] Checking SSH connection..."
ssh "${SSH_OPTS[@]}" "${REMOTE_USER}@${VPS_IP}" "echo OK" || { echo "SSH failed"; exit 1; }

echo "[2/4] Creating work dir on VPS..."
ssh "${SSH_OPTS[@]}" "${REMOTE_USER}@${VPS_IP}" "sudo mkdir -p $WORK_DIR $WORK_DIR/zhe-wei-tech && sudo chown -R \$USER:\$USER $WORK_DIR"

echo "[3/4] Uploading failover script..."
scp "${SSH_OPTS[@]}" "$SCRIPT_DIR/cloud_server_sync_and_run.sh" "${REMOTE_USER}@${VPS_IP}:$WORK_DIR/sync_and_run.sh"
scp "${SSH_OPTS[@]}" "$PROJECT_ROOT/docker-compose.cloud.yml" "${REMOTE_USER}@${VPS_IP}:$WORK_DIR/zhe-wei-tech/" 2>/dev/null || true

echo "[4/4] Setting permissions..."
ssh "${SSH_OPTS[@]}" "${REMOTE_USER}@${VPS_IP}" "chmod +x $WORK_DIR/sync_and_run.sh"

echo ""
echo "=== Deploy done ==="
echo "Next steps on VPS:"
echo "  1. Copy rclone config: scp -i KEY ~/.config/rclone/rclone.conf ${REMOTE_USER}@${VPS_IP}:~/.config/rclone/"
echo "  2. Ensure gdrive remote works: ssh ${REMOTE_USER}@${VPS_IP} 'rclone lsd gdrive:'"
echo "  3. Create .env in $WORK_DIR/zhe-wei-tech with CLOUDFLARE_TOKEN, GEMINI_API_KEY, etc."
echo "  4. Run failover: ssh ${REMOTE_USER}@${VPS_IP} '$WORK_DIR/sync_and_run.sh'"
echo ""

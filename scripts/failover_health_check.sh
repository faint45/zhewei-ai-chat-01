#!/bin/bash
# Zhe-Wei Tech — Failover Health Check & Auto-Switch
# Runs on Oracle Cloud VPS via cron every 2 minutes
# Checks if local server is alive; if not, starts failover services
#
# Cron: */2 * * * * /opt/zhewei/failover_health_check.sh >> /opt/zhewei/failover.log 2>&1

set -euo pipefail

WORK_DIR="${ZHEWEI_WORK_DIR:-/opt/zhewei}"
PROJECT_DIR="$WORK_DIR/zhe-wei-tech"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.failover.yml"
STATE_FILE="$WORK_DIR/.failover_state"  # "standby" or "active"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

# Health check target: local server via Cloudflare (tests the full chain)
LOCAL_HEALTH_URL="${LOCAL_HEALTH_URL:-https://zhe-wei.net/health}"
HEALTH_TIMEOUT=10
FAIL_THRESHOLD=3  # consecutive failures before failover
FAIL_COUNT_FILE="$WORK_DIR/.fail_count"

# ── Functions ──
log() { echo "$LOG_PREFIX $1"; }

get_state() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        echo "standby"
    fi
}

set_state() {
    echo "$1" > "$STATE_FILE"
    log "State changed to: $1"
}

get_fail_count() {
    if [ -f "$FAIL_COUNT_FILE" ]; then
        cat "$FAIL_COUNT_FILE"
    else
        echo "0"
    fi
}

increment_fail_count() {
    local count=$(get_fail_count)
    echo $((count + 1)) > "$FAIL_COUNT_FILE"
}

reset_fail_count() {
    echo "0" > "$FAIL_COUNT_FILE"
}

check_local_health() {
    local http_code
    http_code=$(curl -sf -o /dev/null -w "%{http_code}" --connect-timeout $HEALTH_TIMEOUT "$LOCAL_HEALTH_URL" 2>/dev/null) || http_code="000"
    if [ "$http_code" = "200" ]; then
        return 0
    else
        return 1
    fi
}

start_failover() {
    log ">>> STARTING FAILOVER SERVICES <<<"
    cd "$PROJECT_DIR"

    # Sync latest code from cloud storage before starting
    if command -v rclone &>/dev/null; then
        local RCLONE_REMOTE="${RCLONE_REMOTE:-gdrive}"
        if rclone listremotes 2>/dev/null | grep -q "^${RCLONE_REMOTE}:$"; then
            log "Syncing latest code from cloud storage..."
            rclone sync "${RCLONE_REMOTE}:Zhewei_Brain/tech_repo_backup" "$PROJECT_DIR" \
                --exclude ".venv312/" --exclude "venv*/" --exclude "node_modules/" \
                --exclude "ComfyUI/" --exclude "Jarvis_Training/.venv312/" \
                --exclude "**/__pycache__/" --exclude ".git/" \
                --quiet 2>/dev/null || log "[WARN] rclone sync failed, using existing files"

            # Sync brain_workspace
            rclone sync "${RCLONE_REMOTE}:Zhewei_Brain/workspace_backup" "$PROJECT_DIR/brain_workspace" \
                --quiet 2>/dev/null || true
        fi
    fi

    # Start failover containers
    docker compose -f "$COMPOSE_FILE" up -d --build 2>&1 || {
        log "[ERROR] docker compose up failed"
        return 1
    }

    set_state "active"
    log "Failover services started successfully"

    # Send notification if ntfy is available
    if [ -n "${NTFY_TOPIC:-}" ]; then
        curl -sf -d "Local server offline. Oracle Cloud failover activated at $(date)" \
            "https://notify.zhewei.tech/$NTFY_TOPIC" 2>/dev/null || true
    fi
}

stop_failover() {
    log ">>> STOPPING FAILOVER (local server recovered) <<<"
    cd "$PROJECT_DIR"

    docker compose -f "$COMPOSE_FILE" down 2>&1 || {
        log "[WARN] docker compose down had issues"
    }

    set_state "standby"
    log "Failover services stopped, back to standby"

    if [ -n "${NTFY_TOPIC:-}" ]; then
        curl -sf -d "Local server recovered. Oracle Cloud failover deactivated at $(date)" \
            "https://notify.zhewei.tech/$NTFY_TOPIC" 2>/dev/null || true
    fi
}

# ── Main Logic ──
current_state=$(get_state)

if check_local_health; then
    # Local server is alive
    reset_fail_count

    if [ "$current_state" = "active" ]; then
        log "Local server recovered! Stopping failover..."
        stop_failover
    else
        # Normal: local alive, failover standby — do nothing
        :
    fi
else
    # Local server is down
    increment_fail_count
    fail_count=$(get_fail_count)
    log "Local health check FAILED (count: $fail_count/$FAIL_THRESHOLD)"

    if [ "$current_state" = "standby" ] && [ "$fail_count" -ge "$FAIL_THRESHOLD" ]; then
        log "Threshold reached! Activating failover..."
        start_failover
        reset_fail_count
    elif [ "$current_state" = "active" ]; then
        # Already in failover mode, check if our services are healthy
        if ! docker compose -f "$COMPOSE_FILE" ps --status running 2>/dev/null | grep -q "zhewei_brain"; then
            log "Failover brain_server is down, restarting..."
            docker compose -f "$COMPOSE_FILE" up -d 2>&1 || true
        fi
    fi
fi

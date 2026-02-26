#!/bin/bash
# 築未科技 — 雲端伺服器同步與啟動腳本
# 用於 VPS：從 Google Drive 拉取資料後啟動 brain_server
# 用法：chmod +x cloud_server_sync_and_run.sh && ./cloud_server_sync_and_run.sh

set -e

WORK_DIR="${ZHEWEI_WORK_DIR:-/opt/zhewei}"
RCLONE_REMOTE="${RCLONE_REMOTE:-gdrive}"

echo "[$(date)] Starting sync and run..."

mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# 1. 從雲端拉取 workspace
if rclone listremotes | grep -q "^${RCLONE_REMOTE}:$"; then
    echo "[1/3] Syncing workspace_backup..."
    rclone sync "${RCLONE_REMOTE}:Zhewei_Brain/workspace_backup" "./brain_workspace" \
        --exclude "venv*/" --exclude "**/__pycache__/" --quiet 2>/dev/null || true

    echo "[2/3] Syncing tech_repo_backup..."
    mkdir -p "./zhe-wei-tech"
    rclone sync "${RCLONE_REMOTE}:Zhewei_Brain/tech_repo_backup" "./zhe-wei-tech" \
        --exclude ".venv312/" --exclude "venv*/" --exclude "node_modules/" --quiet 2>/dev/null || true

    if rclone lsd "${RCLONE_REMOTE}:Zhewei_Brain" 2>/dev/null | grep -q jarvis_chroma_backup; then
        mkdir -p "./zhe-wei-tech/Jarvis_Training/chroma_db"
        rclone sync "${RCLONE_REMOTE}:Zhewei_Brain/jarvis_chroma_backup" "./zhe-wei-tech/Jarvis_Training/chroma_db" --quiet 2>/dev/null || true
    fi
else
    echo "[WARN] Rclone remote ${RCLONE_REMOTE} not found, skip sync"
fi

# 2. 啟動 Docker（使用雲端專用 volume 覆寫）
if [ -f "./zhe-wei-tech/docker-compose.yml" ]; then
    echo "[3/3] Starting docker compose..."
    cd "./zhe-wei-tech"
    export WORK_DIR="$WORK_DIR"
    export BRAIN_WORKSPACE="${WORK_DIR}/brain_workspace"
    export ZHEWEI_MEMORY_ROOT="${WORK_DIR}/brain_workspace"
    if [ -f "docker-compose.cloud.yml" ]; then
        docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d 2>/dev/null || docker-compose -f docker-compose.yml -f docker-compose.cloud.yml up -d 2>/dev/null || echo "[WARN] Docker compose failed"
    else
        docker compose up -d 2>/dev/null || docker-compose up -d 2>/dev/null || echo "[WARN] Docker compose failed"
    fi
    echo "[OK] Done."
else
    echo "[WARN] docker-compose.yml not found at ${WORK_DIR}/zhe-wei-tech"
fi

#!/bin/bash
# 築未科技 — 健康監控與自動重啟腳本
# 用途：定期檢查服務健康狀態，異常時自動重啟
# 建議：加入 crontab 每 5 分鐘執行一次

set -e

WORK_DIR=${WORK_DIR:-/opt/zhewei}
LOG_FILE=${LOG_FILE:-/var/log/zhewei_health.log}
COMPOSE_FILE="docker-compose.cloud.yml"

# 記錄函數
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 檢查容器是否運行
check_container() {
    local container=$1
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        return 0
    else
        return 1
    fi
}

# 檢查容器健康狀態
check_health() {
    local container=$1
    local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "none")
    
    if [ "$health" = "healthy" ] || [ "$health" = "none" ]; then
        return 0
    else
        return 1
    fi
}

# 重啟服務
restart_service() {
    local service=$1
    log "重啟服務: $service"
    cd "$WORK_DIR" || exit 1
    docker compose -f "$COMPOSE_FILE" restart "$service"
    sleep 5
}

# 主檢查邏輯
cd "$WORK_DIR" || { log "錯誤: 找不到目錄 $WORK_DIR"; exit 1; }

# 定義需要檢查的服務
CRITICAL_SERVICES=("ollama" "brain_server" "gateway" "tunnel")
OPTIONAL_SERVICES=("portal" "cms" "codesim" "prediction" "smart_bridge")

# 檢查關鍵服務
for service in "${CRITICAL_SERVICES[@]}"; do
    container="zhewei_${service//_/-}"
    
    if ! check_container "$container"; then
        log "警告: $service 容器未運行，嘗試重啟"
        restart_service "$service"
        
        # 再次檢查
        sleep 10
        if ! check_container "$container"; then
            log "錯誤: $service 重啟失敗"
            # 發送告警（可整合 ntfy 或其他通知服務）
            # curl -d "服務 $service 重啟失敗" https://notify.zhewei.tech/zhewei_alerts
        else
            log "成功: $service 已重啟"
        fi
    elif ! check_health "$container"; then
        log "警告: $service 健康檢查失敗，嘗試重啟"
        restart_service "$service"
    fi
done

# 檢查可選服務（僅記錄，不強制重啟）
for service in "${OPTIONAL_SERVICES[@]}"; do
    container="zhewei_${service//_/-}"
    
    if ! check_container "$container"; then
        log "提示: 可選服務 $service 未運行"
    fi
done

# 檢查磁碟空間
DISK_USAGE=$(df -h "$WORK_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    log "警告: 磁碟使用率 ${DISK_USAGE}%，建議清理"
    # 清理 Docker 舊映像和容器
    docker system prune -af --filter "until=72h" >/dev/null 2>&1
    log "已執行 Docker 清理"
fi

# 檢查記憶體使用
MEM_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3/$2 * 100}')
if [ "$MEM_USAGE" -gt 90 ]; then
    log "警告: 記憶體使用率 ${MEM_USAGE}%"
fi

log "健康檢查完成"

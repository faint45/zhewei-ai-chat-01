# DuckDNS 動態 DNS 更新腳本
# 設定每 5 分鐘自動更新

# DuckDNS 配置
$DUCKDNS_DOMAIN = "zhuwei-tech"
$DUCKDNS_TOKEN = "553407dd-d7c9-40e9-be8a-bbdaa71c24b0"

# 設定日誌路徑
$LOG_FILE = "$env:USERPROFILE\DDNS_Update_Log.txt"

try {
    # 獲取當前公網 IP
    $currentIP = Invoke-RestMethod -Uri "http://ifconfig.me" -TimeoutSec 10

    # 更新 DuckDNS
    $updateUrl = "https://www.duckdns.org/update?domains=$DUCKDNS_DOMAIN&token=$DUCKDNS_TOKEN&ip=$currentIP"
    $response = Invoke-RestMethod -Uri $updateUrl -TimeoutSec 10

    # 記錄日誌
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] IP: $currentIP, Response: $response"
    Add-Content -Path $LOG_FILE -Value $logMessage

    # 如果響應不是 OK，發送錯誤
    if ($response -ne "OK") {
        Write-Error "DDNS 更新失敗: $response"
        exit 1
    }

} catch {
    $errorMsg = "[$timestamp] 錯誤: $_"
    Add-Content -Path $LOG_FILE -Value $errorMsg
    Write-Error $errorMsg
    exit 1
}

exit 0

# Cloudflare DDNS 自動更新腳本
# 使用 Cloudflare API 更新 DNS 記錄

# Cloudflare 配置
$CLOUDFLARE_ZONE_ID = "8ba45d8905b38792b061bdcadac6dd39"
$CLOUDFLARE_API_TOKEN = "JS6dXN0-fQ4efSgUbunBTBMYM83bZKPND6872Rrc"
$CLOUDFLARE_DOMAIN = "zhe-wei.net"
$SUBDOMAIN = "www"  # 可以改為其他子域名

# 完整域名
$FULL_DOMAIN = "$SUBDOMAIN.$CLOUDFLARE_DOMAIN"

# API 端點
$API_BASE = "https://api.cloudflare.com/client/v4"
$HEADERS = @{
    "Authorization" = "Bearer $CLOUDFLARE_API_TOKEN"
    "Content-Type"  = "application/json"
}

# 日誌路徑
$LOG_FILE = "$env:USERPROFILE\Cloudflare_DDNS_Log.txt"

try {
    # 獲取當前公網 IP
    $currentIP = Invoke-RestMethod -Uri "http://ipinfo.io/ip" -TimeoutSec 10

    # 查找 DNS 記錄
    $listRecordsUrl = "$API_BASE/zones/$CLOUDFLARE_ZONE_ID/dns_records?name=$FULL_DOMAIN&type=A"
    $records = Invoke-RestMethod -Uri $listRecordsUrl -Headers $HEADERS

    if ($records.result.Count -eq 0) {
        throw "未找到 DNS 記錄: $FULL_DOMAIN"
    }

    $recordId = $records.result[0].id
    $oldIP = $records.result[0].content

    # 檢查 IP 是否需要更新
    if ($oldIP -eq $currentIP) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $logMessage = "[$timestamp] IP 未變化: $currentIP"
        Add-Content -Path $LOG_FILE -Value $logMessage
        exit 0
    }

    # 更新 DNS 記錄
    $updateUrl = "$API_BASE/zones/$CLOUDFLARE_ZONE_ID/dns_records/$recordId"
    $body = @{
        type    = "A"
        name    = $FULL_DOMAIN
        content = $currentIP
        ttl     = 1  # 自動 TTL
        proxied = $true  # 經由 Cloudflare 代理（橙色雲朵）
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri $updateUrl -Method Put -Headers $HEADERS -Body $body

    if ($response.success) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $logMessage = "[$timestamp] DDNS 更新成功: $oldIP -> $currentIP"
        Add-Content -Path $LOG_FILE -Value $logMessage
        Write-Output "✅ DDNS 更新成功"
        Write-Output "舊 IP: $oldIP"
        Write-Output "新 IP: $currentIP"
    } else {
        throw "Cloudflare API 返回錯誤"
    }

} catch {
    $errorMsg = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] 錯誤: $_"
    Add-Content -Path $LOG_FILE -Value $errorMsg
    Write-Error $errorMsg
    exit 1
}

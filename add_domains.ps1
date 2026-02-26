# Cloudflare API 域名添加腳本
$API_TOKEN = "ccbaf7d563e165e7c5d973022f3f1e9eb4b79"
$TUNNEL_ID = "546fffc1-eb7d-4f9a-a3df-d30a1940aa0c"

Write-Host "🌐 Cloudflare Tunnel 域名自動添加" -ForegroundColor Cyan
Write-Host ""

# 取得 Account ID
Write-Host "🔍 取得 Account ID..." -ForegroundColor Yellow
$headers = @{
    "Authorization" = "Bearer $API_TOKEN"
    "Content-Type" = "application/json"
}

try {
    $accounts = Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/accounts" -Headers $headers -Method Get
    
    if ($accounts.success -and $accounts.result.Count -gt 0) {
        $ACCOUNT_ID = $accounts.result[0].id
        Write-Host "✅ Account ID: $ACCOUNT_ID" -ForegroundColor Green
    } else {
        Write-Host "❌ 無法取得 Account ID" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ API 請求失敗: $_" -ForegroundColor Red
    exit 1
}

# 取得當前 Tunnel 配置
Write-Host ""
Write-Host "📋 取得當前 Tunnel 配置..." -ForegroundColor Yellow
$tunnelUrl = "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/cfd_tunnel/$TUNNEL_ID/configurations"

try {
    $currentConfig = Invoke-RestMethod -Uri $tunnelUrl -Headers $headers -Method Get
    
    if ($currentConfig.success) {
        $config = $currentConfig.result.config
        $ingress = $config.ingress
        $version = $currentConfig.result.version
        
        Write-Host "✅ 當前配置版本: $version" -ForegroundColor Green
        
        $existingHostnames = @()
        foreach ($rule in $ingress) {
            if ($rule.hostname) {
                $existingHostnames += $rule.hostname
            }
        }
        
        Write-Host "📊 現有域名數量: $($existingHostnames.Count)" -ForegroundColor Cyan
        Write-Host ""
        
        # 檢查要添加的域名
        $domainsToAdd = @(
            @{hostname = "zhe-wei.net"; service = "http://gateway:80"},
            @{hostname = "www.zhe-wei.net"; service = "http://gateway:80"}
        )
        
        $newIngress = @()
        $addedCount = 0
        
        foreach ($domain in $domainsToAdd) {
            if ($existingHostnames -contains $domain.hostname) {
                Write-Host "⚠️  $($domain.hostname) 已存在，跳過" -ForegroundColor Yellow
            } else {
                Write-Host "➕ 準備添加: $($domain.hostname)" -ForegroundColor Green
                $newIngress += @{
                    hostname = $domain.hostname
                    service = $domain.service
                    originRequest = @{}
                }
                $addedCount++
            }
        }
        
        if ($addedCount -eq 0) {
            Write-Host ""
            Write-Host "✅ 所有域名已存在，無需添加" -ForegroundColor Green
            exit 0
        }
        
        # 合併配置
        $finalIngress = $newIngress
        foreach ($rule in $ingress) {
            if ($rule.hostname) {
                $finalIngress += $rule
            }
        }
        
        # 添加默認路由
        $defaultRoute = $ingress | Where-Object { -not $_.hostname } | Select-Object -First 1
        if ($defaultRoute) {
            $finalIngress += $defaultRoute
        } else {
            $finalIngress += @{service = "http://gateway:80"}
        }
        
        # 更新配置
        Write-Host ""
        Write-Host "📝 更新 Tunnel 配置..." -ForegroundColor Yellow
        
        $newConfig = @{
            config = @{
                ingress = $finalIngress
                "warp-routing" = @{enabled = $false}
            }
        } | ConvertTo-Json -Depth 10
        
        $updateResult = Invoke-RestMethod -Uri $tunnelUrl -Headers $headers -Method Put -Body $newConfig
        
        if ($updateResult.success) {
            Write-Host ""
            Write-Host "✅ 域名添加成功！" -ForegroundColor Green
            Write-Host ""
            Write-Host "📋 新增的域名:" -ForegroundColor Cyan
            foreach ($domain in $domainsToAdd) {
                if ($existingHostnames -notcontains $domain.hostname) {
                    Write-Host "  ✅ $($domain.hostname) → $($domain.service)" -ForegroundColor Green
                }
            }
            Write-Host ""
            Write-Host "⏱️  等待 10-30 秒 DNS 生效..." -ForegroundColor Yellow
            Write-Host ""
            Write-Host "🔗 測試訪問:" -ForegroundColor Cyan
            Write-Host "  https://zhe-wei.net" -ForegroundColor White
            Write-Host "  https://www.zhe-wei.net" -ForegroundColor White
            Write-Host ""
        } else {
            Write-Host "❌ 域名添加失敗" -ForegroundColor Red
            Write-Host $updateResult | ConvertTo-Json -Depth 5
            exit 1
        }
        
    } else {
        Write-Host "❌ 無法取得 Tunnel 配置" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ 操作失敗: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# 築未科技 — 本地 Cloudflare Tunnel 設定腳本
# 用途：自動設定本地 GPU 服務的 Cloudflare Tunnel

param(
    [string]$TunnelName = "zhewei-local-gpu",
    [string]$Domain = "zhe-wei.net"
)

Write-Host "=== 築未科技本地 Tunnel 設定 ===" -ForegroundColor Green

# 檢查 cloudflared 是否已安裝
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host "❌ cloudflared 未安裝" -ForegroundColor Red
    Write-Host "請執行: winget install Cloudflare.cloudflared" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ cloudflared 已安裝" -ForegroundColor Green

# 檢查本地服務
Write-Host "`n檢查本地服務..." -ForegroundColor Cyan

$services = @(
    @{Name="Ollama"; Port=11460; Path="/api/tags"},
    @{Name="Vision AI"; Port=8030; Path="/healthz"},
    @{Name="ComfyUI"; Port=9188; Path="/"},
    @{Name="Dify"; Port=8080; Path="/"}
)

$availableServices = @()

foreach ($svc in $services) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$($svc.Port)$($svc.Path)" -TimeoutSec 2 -ErrorAction Stop
        Write-Host "  ✅ $($svc.Name) (port $($svc.Port))" -ForegroundColor Green
        $availableServices += $svc
    } catch {
        Write-Host "  ⚠️ $($svc.Name) (port $($svc.Port)) 未運行" -ForegroundColor Yellow
    }
}

if ($availableServices.Count -eq 0) {
    Write-Host "`n❌ 沒有可用的本地服務" -ForegroundColor Red
    Write-Host "請先啟動至少一個本地服務" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n找到 $($availableServices.Count) 個可用服務" -ForegroundColor Green

# 建立 Tunnel 配置
Write-Host "`n建立 Tunnel 配置..." -ForegroundColor Cyan

$configPath = "$env:USERPROFILE\.cloudflared\config.yml"
$configDir = Split-Path $configPath

if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

# 生成配置內容
$configContent = @"
# 築未科技本地 GPU 服務 Tunnel 配置
# 自動生成於 $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

tunnel: $TunnelName
credentials-file: $configDir\$TunnelName.json

ingress:
"@

# 添加可用服務
foreach ($svc in $availableServices) {
    $subdomain = switch ($svc.Name) {
        "Ollama" { "ollama-gpu" }
        "Vision AI" { "vision-gpu" }
        "ComfyUI" { "comfyui" }
        "Dify" { "dify-local" }
    }
    
    $configContent += @"

  # $($svc.Name)
  - hostname: $subdomain.$Domain
    service: http://localhost:$($svc.Port)
"@
}

# 添加 fallback
$configContent += @"

  
  # 404 fallback
  - service: http_status:404
"@

# 寫入配置檔案
$configContent | Out-File -FilePath $configPath -Encoding UTF8 -Force

Write-Host "✅ 配置已寫入: $configPath" -ForegroundColor Green

# 顯示配置內容
Write-Host "`n配置內容:" -ForegroundColor Cyan
Write-Host $configContent -ForegroundColor Gray

# 提示後續步驟
Write-Host "`n=== 後續步驟 ===" -ForegroundColor Green
Write-Host ""
Write-Host "1. 登入 Cloudflare:" -ForegroundColor Yellow
Write-Host "   cloudflared tunnel login"
Write-Host ""
Write-Host "2. 建立 Tunnel:" -ForegroundColor Yellow
Write-Host "   cloudflared tunnel create $TunnelName"
Write-Host ""
Write-Host "3. 設定 DNS（在 Cloudflare Dashboard）:" -ForegroundColor Yellow
foreach ($svc in $availableServices) {
    $subdomain = switch ($svc.Name) {
        "Ollama" { "ollama-gpu" }
        "Vision AI" { "vision-gpu" }
        "ComfyUI" { "comfyui" }
        "Dify" { "dify-local" }
    }
    Write-Host "   $subdomain.$Domain → CNAME → <TUNNEL_ID>.cfargotunnel.com"
}
Write-Host ""
Write-Host "4. 測試 Tunnel:" -ForegroundColor Yellow
Write-Host "   cloudflared tunnel run $TunnelName"
Write-Host ""
Write-Host "5. 安裝為 Windows 服務:" -ForegroundColor Yellow
Write-Host "   cloudflared service install"
Write-Host "   Start-Service cloudflared"
Write-Host ""
Write-Host "完成！" -ForegroundColor Green

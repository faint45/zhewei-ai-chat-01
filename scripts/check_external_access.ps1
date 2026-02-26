# External access diagnostic
# Run: powershell -ExecutionPolicy Bypass -File scripts/check_external_access.ps1
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

Write-Host "`n=== External Access Diagnostic ===" -ForegroundColor Cyan

# 1. CLOUDFLARE_TOKEN
Write-Host "`n[1] CLOUDFLARE_TOKEN..." -ForegroundColor Yellow
$envFile = Join-Path $root ".env"
if (Test-Path $envFile) {
    $content = Get-Content $envFile -Raw -ErrorAction SilentlyContinue
    if ($content -match "CLOUDFLARE_TOKEN=(.+)") {
        $token = $Matches[1].Trim()
        if ($token.Length -eq 0) {
            Write-Host "  [X] Not set. Add CLOUDFLARE_TOKEN in .env" -ForegroundColor Red
        } elseif ($token -match '^[a-f0-9-]{36}$') {
            Write-Host "  [X] Looks like UUID. Use full JWT (eyJ...) instead" -ForegroundColor Red
        } elseif ($token -match '^eyJ') {
            Write-Host "  [OK] Format OK (JWT)" -ForegroundColor Green
        } else {
            Write-Host "  [?] Unknown format. Ensure full Token" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [X] CLOUDFLARE_TOKEN not found" -ForegroundColor Red
    }
} else {
    Write-Host "  [X] .env not found" -ForegroundColor Red
}

# 2. Tunnel container
Write-Host "`n[2] Tunnel container..." -ForegroundColor Yellow
$tunnel = docker ps -a --format "{{.Names}} {{.Status}}" 2>$null | Select-String "tunnel"
if ($tunnel) {
    if ($tunnel -match "Up") {
        Write-Host "  [OK] Running" -ForegroundColor Green
    } else {
        Write-Host "  [X] Not running" -ForegroundColor Red
        Write-Host "  Run: docker start zhe-wei-tech-tunnel-1" -ForegroundColor Gray
    }
} else {
    Write-Host "  [X] Tunnel container not found" -ForegroundColor Red
    Write-Host "  Run: docker compose up -d" -ForegroundColor Gray
}

# 3. Brain container
Write-Host "`n[3] Brain container..." -ForegroundColor Yellow
$brain = docker ps --format "{{.Names}}" 2>$null | Select-String "zhewei_brain"
if ($brain) {
    Write-Host "  [OK] Running" -ForegroundColor Green
} else {
    Write-Host "  [X] Not running" -ForegroundColor Red
}

# 4. Local 8002
Write-Host "`n[4] Local 8002..." -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8002/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "  [OK] Local OK" -ForegroundColor Green
} catch {
    Write-Host "  [X] Local unreachable" -ForegroundColor Red
}

# 5. External https://brain.zhe-wei.net
Write-Host "`n[5] External https://brain.zhe-wei.net ..." -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest -Uri "https://brain.zhe-wei.net/health" -UseBasicParsing -TimeoutSec 10
    Write-Host "  [OK] External OK" -ForegroundColor Green
} catch {
    Write-Host "  [X] External unreachable" -ForegroundColor Red
    Write-Host "  Check: 1) CLOUDFLARE_TOKEN  2) Tunnel container  3) Cloudflare Public Hostname" -ForegroundColor Gray
}

Write-Host "`n=== Done ===" -ForegroundColor Cyan
Write-Host ""

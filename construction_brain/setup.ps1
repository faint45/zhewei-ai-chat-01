# ============================================
# Construction Brain — 一鍵安裝腳本 (Windows)
# 用法: powershell -ExecutionPolicy Bypass -File setup.ps1
# ============================================

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV = Join-Path (Split-Path $ROOT -Parent) "Jarvis_Training\.venv312"
$PY = Join-Path $VENV "Scripts\python.exe"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Construction Brain - Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. 檢查 Python
if (!(Test-Path $PY)) {
    Write-Host "[ERROR] Python venv not found: $VENV" -ForegroundColor Red
    Write-Host "  Please create venv first: python -m venv $VENV" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Python: $PY" -ForegroundColor Green

# 2. 安裝依賴
Write-Host "`n[1/4] Installing dependencies..." -ForegroundColor Yellow
& $PY -m pip install -r (Join-Path $ROOT "requirements.txt") --quiet
Write-Host "[OK] Dependencies installed" -ForegroundColor Green

# 3. 建立資料目錄
Write-Host "`n[2/4] Creating data directories..." -ForegroundColor Yellow
$dirs = @("data\voice", "data\photos", "data\events", "data\reports", "data\schedule")
foreach ($d in $dirs) {
    $full = Join-Path $ROOT $d
    if (!(Test-Path $full)) {
        New-Item -ItemType Directory -Path $full -Force | Out-Null
        Write-Host "  Created: $d" -ForegroundColor Gray
    }
}
Write-Host "[OK] Data directories ready" -ForegroundColor Green

# 4. 複製 env
Write-Host "`n[3/4] Checking .env..." -ForegroundColor Yellow
$envFile = Join-Path (Split-Path $ROOT -Parent) ".env"
if (Test-Path $envFile) {
    Write-Host "[OK] .env exists" -ForegroundColor Green
} else {
    Write-Host "[WARN] .env not found, copy from env.example" -ForegroundColor Yellow
}

# 5. 檢查 Ollama
Write-Host "`n[4/4] Checking Ollama..." -ForegroundColor Yellow
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:11460/api/tags" -Method Get -TimeoutSec 5
    $models = $resp.models | ForEach-Object { $_.name }
    Write-Host "[OK] Ollama running, models: $($models -join ', ')" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Ollama not reachable at :11460" -ForegroundColor Yellow
    Write-Host "  Start with: ollama serve" -ForegroundColor Gray
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Quick Test:" -ForegroundColor Yellow
Write-Host "  & `"$PY`" -c `"from construction_brain.core.extract_work_events import extract_events; print('OK')`""
Write-Host ""

# 築未科技：大腦全系統啟動腳本
# 路徑與 D:\brain_workspace、Z:\Zhewei_Brain 對齊

Write-Host "🚀 正在啟動 築未科技大腦 (Zhewei Brain)..." -ForegroundColor Cyan

$Root = "D:\brain_workspace"

# 1. 啟動 Z 槽檢查 (Google Drive 掛載)
if (-not (Test-Path "Z:\")) {
    Write-Host "⚠️ 警告: 找不到 Z 槽，請確認 Rclone 已掛載！" -ForegroundColor Yellow
} else {
    Write-Host "✅ Z 槽已就緒" -ForegroundColor Green
}

# 確保 brain_workspace 目錄存在
@("$Root\input", "$Root\processed", "$Root\models") | ForEach-Object {
    if (-not (Test-Path $_)) { New-Item -ItemType Directory -Path $_ -Force | Out-Null }
}

# 2. 啟動主腦伺服器 (Python 3.14)
$BrainServerPath = Join-Path $Root "brain_server.py"
if (-not (Test-Path $BrainServerPath)) { $BrainServerPath = Join-Path (Split-Path $PSScriptRoot -Parent) "brain_server.py" }
if (-not (Test-Path $BrainServerPath)) { $BrainServerPath = Join-Path (Get-Location) "brain_server.py" }
$BrainDir = Split-Path $BrainServerPath -Parent
if (Test-Path $BrainServerPath) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$BrainDir'; python brain_server.py" -WindowStyle Normal
    Write-Host "✅ WebSocket 伺服器 (Port 8000) 已啟動" -ForegroundColor Green
} else {
    Write-Host "⚠️ 未找到 brain_server.py，跳過主腦啟動" -ForegroundColor Yellow
}

# 3. 啟動工地主動監控系統 (Python 3.14)
$MonitorScript = Join-Path $Root "site_monitor.py"
if (Test-Path $MonitorScript) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root'; python site_monitor.py" -WindowStyle Normal
    Write-Host "✅ 工地監控中樞已啟動" -ForegroundColor Green
} else {
    Write-Host "⚠️ 未找到 site_monitor.py，跳過工地監控" -ForegroundColor Yellow
}

# 4. 驗證視覺工兵 CUDA 狀態 (Python 3.12)
$VenvPy = Join-Path $Root "venv_vision\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) { $VenvPy = Join-Path $Root "venv_vision\bin\python" }
Write-Host "🔍 正在檢查顯卡 (RTX 4060 Ti) 狀態..."
if (Test-Path $VenvPy) {
    try {
        & $VenvPy -c "import torch; print(f'GPU 狀態: {torch.cuda.is_available()}')"
    } catch {
        Write-Host "⚠️ 視覺工兵環境檢查失敗: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️ 未找到 venv_vision，跳過 CUDA 檢查" -ForegroundColor Yellow
}

Write-Host "✨ 部署完成！總指揮可以開始在 iPhone 15 Pro 下達指令了。" -ForegroundColor Cyan

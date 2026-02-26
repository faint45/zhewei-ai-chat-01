# 築未科技：大腦全系統安全啟動腳本
# 先執行預檢，通過後再分視窗啟動 brain_server 與 site_monitor

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyScript.Path
Set-Location $ScriptDir

Write-Host "🛡️ 正在進行系統安全檢查..." -ForegroundColor Cyan
python preflight_check.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ 診斷未通過，請修正上述問題！" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "`n🚀 正在同步啟動服務..." -ForegroundColor Green

$Root = "D:\brain_workspace"
$BrainServerPath = Join-Path $ScriptDir "brain_server.py"
$MonitorScript = Join-Path $Root "site_monitor.py"
if (-not (Test-Path $MonitorScript)) {
    $MonitorScript = Join-Path $ScriptDir "brain_workspace\site_monitor.py"
    $Root = Join-Path $ScriptDir "brain_workspace"
}

# 啟動 WebSocket 主腦
if (Test-Path $BrainServerPath) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ScriptDir'; python brain_server.py" -WindowStyle Normal
    Write-Host "  ✅ WebSocket 主腦 (Port 8000) 已啟動" -ForegroundColor Green
} else {
    Write-Host "  ⚠️ 未找到 brain_server.py" -ForegroundColor Yellow
}

# 啟動工地主動監控器
if (Test-Path $MonitorScript) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root'; python site_monitor.py" -WindowStyle Normal
    Write-Host "  ✅ 工地主動監控器已啟動" -ForegroundColor Green
} else {
    Write-Host "  ⚠️ 未找到 site_monitor.py，跳過工地監控" -ForegroundColor Yellow
}

Write-Host "`n✨ 築未大腦已上線。您可以從 iPhone 15 Pro 登入 100.116.133.23:8000 了。" -ForegroundColor Cyan

# ========================================
# 築未科技大腦 - 全系統啟動腳本
# ========================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   築未科技大腦 - 全系統啟動" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 設置腳本目錄
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# ========================================
# 步驟 1: 檢查 Z 槽（Google Drive）
# ========================================
Write-Host "[1/6] 檢查 Z 槽狀態..." -ForegroundColor Yellow
if (Test-Path "Z:\") {
    Write-Host "    ✓ Z 槽已掛載" -ForegroundColor Green
} else {
    Write-Host "    ⚠ Z 槽未掛載，請先執行 Rclone 掛載腳本" -ForegroundColor Yellow
    Write-Host "    提示: 右鍵 '挂载 Google Drive 为 Z 槽.bat' 以管理員身份執行" -ForegroundColor Gray
}
Write-Host ""

# ========================================
# 步驟 2: 檢查 Python 環境
# ========================================
Write-Host "[2/6] 檢查 Python 環境..." -ForegroundColor Yellow
try {
    $pythonPath = Get-Command python -ErrorAction Stop
    $pythonVersion = & python --version 2>&1
    Write-Host "    ✓ Python 已安裝: $pythonVersion" -ForegroundColor Green
    Write-Host "      路徑: $($pythonPath.Source)" -ForegroundColor Gray
} catch {
    Write-Host "    ✗ Python 未找到，請安裝 Python 3.x" -ForegroundColor Red
    Read-Host "按 Enter 鍵退出"
    exit 1
}
Write-Host ""

# ========================================
# 步驟 3: 啟動主腦服務器（對話服務）
# ========================================
Write-Host "[3/6] 啟動主腦服務器..." -ForegroundColor Yellow
if (Test-Path "brain_server.py") {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir'; python brain_server.py" -WindowStyle Normal
    Write-Host "    ✓ 主腦服務器啟動中... (http://localhost:8000)" -ForegroundColor Green
    Start-Sleep -Seconds 2
} else {
    Write-Host "    ✗ 找不到 brain_server.py" -ForegroundColor Red
}
Write-Host ""

# ========================================
# 步驟 4: 啟動監控面板
# ========================================
Write-Host "[4/6] 啟動監控面板..." -ForegroundColor Yellow
if (Test-Path "monitoring_dashboard.py") {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir'; python monitoring_dashboard.py" -WindowStyle Normal
    Write-Host "    ✓ 監控面板啟動中... (http://localhost:8001)" -ForegroundColor Green
    Start-Sleep -Seconds 2
} elseif (Test-Path "monitoring_service.py") {
    Write-Host "    ℹ 監控服務器文件存在" -ForegroundColor Gray
} else {
    Write-Host "    ⚠ 監控服務文件未找到" -ForegroundColor Yellow
}
Write-Host ""

# ========================================
# 步驟 5: 檢查 Ollama 服務
# ========================================
Write-Host "[5/6] 檢查 Ollama 服務..." -ForegroundColor Yellow
try {
    $ollamaPath = Get-Command ollama -ErrorAction Stop
    $ollamaList = & ollama list 2>&1
    if ($ollamaList -match "llama|qwen|deepseek") {
        Write-Host "    ✓ Ollama 已安裝並有模型可用" -ForegroundColor Green
        Write-Host "      訪問: http://localhost:11434" -ForegroundColor Gray
    } else {
        Write-Host "    ⚠ Ollama 已安裝但沒有找到模型" -ForegroundColor Yellow
        Write-Host "      提示: 執行 'ollama pull llama3.2' 安裝模型" -ForegroundColor Gray
    }
} catch {
    Write-Host "    ⚠ Ollama 未安裝" -ForegroundColor Yellow
    Write-Host "      提示: 從 https://ollama.com 下載安裝" -ForegroundColor Gray
}
Write-Host ""

# ========================================
# 步驟 6: 檢查網絡連接（Tailscale）
# ========================================
Write-Host "[6/6] 檢查網絡連接..." -ForegroundColor Yellow
try {
    $tailscaleIP = "100.116.133.23"
    $testResult = Test-Connection -ComputerName $tailscaleIP -Count 1 -Quiet
    if ($testResult) {
        Write-Host "    ✓ Tailscale VPN 連接正常" -ForegroundColor Green
        Write-Host "      IP: $tailscaleIP" -ForegroundColor Gray
    } else {
        Write-Host "    ⚠ Tailscale VPN 連接異常" -ForegroundColor Yellow
    }
} catch {
    Write-Host "    ℹ 無法檢查網絡連接" -ForegroundColor Gray
}
Write-Host ""

# ========================================
# 啟動完成
# ========================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   ✨ 啟動完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "已啟動的服務:" -ForegroundColor White
Write-Host "  • 對話服務: http://localhost:8000" -ForegroundColor Cyan
Write-Host "  • 監控面板: http://localhost:8001" -ForegroundColor Cyan
Write-Host "  • Ollama:   http://localhost:11434" -ForegroundColor Cyan
Write-Host ""
Write-Host "遠端訪問（需要 Tailscale VPN）:" -ForegroundColor White
Write-Host "  • 對話服務: http://100.116.133.23:8000" -ForegroundColor Cyan
Write-Host "  • 監控面板: http://100.116.133.23:8001" -ForegroundColor Cyan
Write-Host ""
Write-Host "iOS 使用方式:" -ForegroundColor White
Write-Host "  1. Safari 打開: http://100.116.133.23:8000" -ForegroundColor Gray
Write-Host "  2. 分享 → 添加到主屏幕" -ForegroundColor Gray
Write-Host "  3. 像原生 App 一樣使用" -ForegroundColor Gray
Write-Host ""
Write-Host "提示: 關閉所有服務請執行 '停止所有服務.bat'" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 開啟瀏覽器
Write-Host "3 秒後自動開啟瀏覽器..." -ForegroundColor Gray
Start-Sleep -Seconds 3
Start-Process "http://localhost:8000"

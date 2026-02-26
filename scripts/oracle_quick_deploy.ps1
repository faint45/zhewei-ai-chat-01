# Oracle Cloud 快速部署腳本（Windows PowerShell）
# 使用方法：
# 1. 修改下方的 IP 和私鑰路徑
# 2. 在 PowerShell 中執行：.\oracle_quick_deploy.ps1

param(
    [Parameter(Mandatory=$true)]
    [string]$PublicIP,
    
    [Parameter(Mandatory=$true)]
    [string]$PrivateKeyPath
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Oracle Cloud 快速部署腳本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 檢查私鑰檔案是否存在
if (-not (Test-Path $PrivateKeyPath)) {
    Write-Host "錯誤：找不到私鑰檔案 $PrivateKeyPath" -ForegroundColor Red
    exit 1
}

Write-Host "公用 IP: $PublicIP" -ForegroundColor Green
Write-Host "私鑰路徑: $PrivateKeyPath" -ForegroundColor Green
Write-Host ""

# 設定私鑰權限（Windows）
Write-Host "[1/5] 設定私鑰權限..." -ForegroundColor Yellow
icacls $PrivateKeyPath /inheritance:r
icacls $PrivateKeyPath /grant:r "$($env:USERNAME):(R)"

# 測試 SSH 連線
Write-Host "[2/5] 測試 SSH 連線..." -ForegroundColor Yellow
$testConnection = ssh -i $PrivateKeyPath -o StrictHostKeyChecking=no -o ConnectTimeout=10 opc@$PublicIP "echo 'Connection OK'"
if ($LASTEXITCODE -ne 0) {
    Write-Host "錯誤：無法連線到 $PublicIP" -ForegroundColor Red
    Write-Host "請檢查：" -ForegroundColor Yellow
    Write-Host "  1. 公用 IP 是否正確" -ForegroundColor Yellow
    Write-Host "  2. 防火牆是否開放 22 端口" -ForegroundColor Yellow
    Write-Host "  3. 私鑰是否正確" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ SSH 連線成功" -ForegroundColor Green
Write-Host ""

# 上傳設定腳本
Write-Host "[3/5] 上傳設定腳本..." -ForegroundColor Yellow
scp -i $PrivateKeyPath .\scripts\oracle_vm_setup.sh opc@${PublicIP}:/tmp/
if ($LASTEXITCODE -ne 0) {
    Write-Host "錯誤：無法上傳腳本" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 腳本上傳成功" -ForegroundColor Green
Write-Host ""

# 執行設定腳本
Write-Host "[4/5] 執行 VM 設定（需要 5-10 分鐘）..." -ForegroundColor Yellow
Write-Host "正在安裝：Docker、Swap、防火牆、優化設定..." -ForegroundColor Cyan
ssh -i $PrivateKeyPath opc@$PublicIP "sudo bash /tmp/oracle_vm_setup.sh"
if ($LASTEXITCODE -ne 0) {
    Write-Host "警告：設定腳本執行時出現錯誤" -ForegroundColor Yellow
    Write-Host "請手動檢查 VM 狀態" -ForegroundColor Yellow
} else {
    Write-Host "✓ VM 設定完成" -ForegroundColor Green
}
Write-Host ""

# 檢查系統狀態
Write-Host "[5/5] 檢查系統狀態..." -ForegroundColor Yellow
ssh -i $PrivateKeyPath opc@$PublicIP "sudo /opt/zhewei/health_check.sh"
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✓ 基礎設定完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步：" -ForegroundColor Yellow
Write-Host "1. 上傳專案程式碼" -ForegroundColor White
Write-Host "2. 設定環境變數" -ForegroundColor White
Write-Host "3. 啟動 Docker 服務" -ForegroundColor White
Write-Host ""
Write-Host "SSH 連線指令：" -ForegroundColor Yellow
Write-Host "ssh -i $PrivateKeyPath opc@$PublicIP" -ForegroundColor Cyan
Write-Host ""

# Oracle Cloud 簡化部署腳本
param(
    [string]$PublicIP = "138.2.15.249",
    [string]$PrivateKeyPath = "D:\下載\ssh-key-2026-02-16.key"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Oracle Cloud 部署腳本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "公用 IP: $PublicIP" -ForegroundColor Green
Write-Host "私鑰: $PrivateKeyPath" -ForegroundColor Green
Write-Host ""

# 測試連線
Write-Host "[1/4] 測試 SSH 連線..." -ForegroundColor Yellow
ssh -i $PrivateKeyPath -o StrictHostKeyChecking=no opc@$PublicIP "echo 'OK'"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 連線成功" -ForegroundColor Green
} else {
    Write-Host "✗ 連線失敗，請檢查防火牆設定" -ForegroundColor Red
    exit 1
}

# 上傳腳本
Write-Host "[2/4] 上傳設定腳本..." -ForegroundColor Yellow
scp -i $PrivateKeyPath .\scripts\oracle_vm_setup.sh opc@${PublicIP}:/tmp/

# 執行設定
Write-Host "[3/4] 執行系統設定（5-10分鐘）..." -ForegroundColor Yellow
ssh -i $PrivateKeyPath opc@$PublicIP "sudo bash /tmp/oracle_vm_setup.sh"

# 檢查狀態
Write-Host "[4/4] 檢查系統狀態..." -ForegroundColor Yellow
ssh -i $PrivateKeyPath opc@$PublicIP "free -h && docker --version"

Write-Host ""
Write-Host "✓ 完成！" -ForegroundColor Green
Write-Host "SSH 連線: ssh -i $PrivateKeyPath opc@$PublicIP" -ForegroundColor Cyan

# 築未科技 — D 槽一鍵部署（資料都放在 D 槽）
# 執行：於專案根目錄執行 .\一鍵部屬到D槽.bat 或 powershell -ExecutionPolicy Bypass -File scripts\deploy_to_d_drive.ps1

$ErrorActionPreference = "Stop"
$D_ROOT = "D:\brain_workspace"
$PROJECT_ROOT = if ($PSScriptRoot) { Split-Path $PSScriptRoot -Parent } else { Get-Location }

Write-Host "築未科技 — D 槽部署" -ForegroundColor Cyan
Write-Host "專案目錄: $PROJECT_ROOT" -ForegroundColor Gray
Write-Host "目標目錄: $D_ROOT" -ForegroundColor Gray
Write-Host ""

# 1. 建立 D 槽根目錄與子目錄（資料都放 D）
$dirs = @(
    "$D_ROOT\input",
    "$D_ROOT\processed",
    "$D_ROOT\models",
    "$D_ROOT\output",
    "$D_ROOT\cache",
    "$D_ROOT\Reports",
    "$D_ROOT\Rules",
    "$D_ROOT\Contract",
    "$D_ROOT\static"
)
foreach ($d in $dirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
        Write-Host "[+] 建立 $d" -ForegroundColor Green
    }
}

# 2. 複製 brain_workspace 內容到 D 槽（覆蓋不刪除既有）
$src_bw = Join-Path $PROJECT_ROOT "brain_workspace"
if (Test-Path $src_bw) {
    Get-ChildItem $src_bw -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($src_bw.Length + 1)
        $dest = Join-Path $D_ROOT $rel
        $destDir = Split-Path $dest -Parent
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
        Copy-Item $_.FullName -Destination $dest -Force
    }
    Write-Host "[+] 已同步 brain_workspace -> $D_ROOT" -ForegroundColor Green
} else {
    Write-Host "[!] 未找到 $src_bw" -ForegroundColor Yellow
}

# 3. 複製主腦核心腳本到 D 槽（可選，方便從 D 槽直接啟動）
$core_files = @("brain_server.py", "agent_logic.py", "ai_service.py", "agent_tools.py", "report_generator.py")
foreach ($f in $core_files) {
    $src = Join-Path $PROJECT_ROOT $f
    if (Test-Path $src) {
        Copy-Item $src -Destination (Join-Path $D_ROOT $f) -Force
        Write-Host "[+] 複製 $f" -ForegroundColor Green
    }
}

# 4. 建立視覺用 Python 3.12 虛擬環境
$venv = "$D_ROOT\venv_vision"
$venvPy = "$venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    $venvPy = "$venv\bin\python"
}
if (-not (Test-Path $venvPy)) {
    Write-Host "[*] 建立 venv_vision (Python 3.12)..." -ForegroundColor Cyan
    Push-Location $D_ROOT
    try {
        $py312 = Get-Command py -ErrorAction SilentlyContinue
        if ($py312) {
            py -3.12 -m venv venv_vision
        } else {
            python -m venv venv_vision
        }
        & "$D_ROOT\venv_vision\Scripts\pip.exe" install -q ultralytics torch
        Write-Host "[+] venv_vision 建立並安裝 ultralytics, torch" -ForegroundColor Green
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[+] venv_vision 已存在" -ForegroundColor Green
}

# 5. 寫入 D 槽專用 .env 至專案根目錄（資料都放 D）
$envPath = Join-Path $PROJECT_ROOT ".env"
$envLines = "# 築未科技 - 資料都放在 D 槽（本檔可由 deploy_to_d_drive.ps1 寫入）", "BRAIN_WORKSPACE=$D_ROOT", "ZHEWEI_MEMORY_ROOT=$D_ROOT"
$envContent = $envLines -join "`n"
if (-not (Test-Path $envPath)) {
    Set-Content -Path $envPath -Value $envContent -Encoding UTF8
    Write-Host "[+] 已建立 .env（BRAIN_WORKSPACE、ZHEWEI_MEMORY_ROOT 指向 D 槽）" -ForegroundColor Green
} else {
    $current = Get-Content $envPath -Raw -ErrorAction SilentlyContinue
    $needD = $current -notlike "*ZHEWEI_MEMORY_ROOT=$D_ROOT*"
    if ($needD) {
        Add-Content -Path $envPath -Value "`n# D 槽資料（部署腳本寫入）`nBRAIN_WORKSPACE=$D_ROOT`nZHEWEI_MEMORY_ROOT=$D_ROOT" -Encoding UTF8
        Write-Host "[+] 已追加 .env 之 D 槽設定" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "部署完成。資料目錄：$D_ROOT" -ForegroundColor Cyan
Write-Host "  input, processed, models, output, cache, Reports, Rules, Contract 均已就緒。" -ForegroundColor Gray
Write-Host "啟動方式：" -ForegroundColor Cyan
Write-Host "  cd $D_ROOT" -ForegroundColor White
Write-Host "  .\start_all.ps1" -ForegroundColor White
Write-Host "或從專案目錄：python brain_server.py（請先設定 .env 或本機 ZHEWEI_MEMORY_ROOT=$D_ROOT）" -ForegroundColor Gray

#Requires -Version 5.1
# Archive non-main launchers to archive/ops_legacy_launchers
# Run: powershell -ExecutionPolicy Bypass -File scripts\archive_launchers.ps1

$ErrorActionPreference = "Stop"
$Root = if ($env:ZHEWEI_ROOT) { $env:ZHEWEI_ROOT } else { (Get-Item $PSScriptRoot).Parent.FullName }
$ArchiveDir = Join-Path $Root "archive\ops_legacy_launchers"

$ToArchive = @(
    "啟動完整跑.bat",
    "一鍵啟動.bat",
    "Start_All_Stable.bat",
    "Start_All_Stable_Console.bat",
    "Start_OpenHands.bat",
    "Start_OpenWebUI.bat",
    "Start_48H_Warroom.bat",
    "Start_OpenInterpreter_Debug.bat",
    "Deploy_All.bat",
    "Boot_Health_Check_And_Start.bat",
    "診斷外網連線.bat",
    "build_simple.bat",
    "build_installer.bat",
    "test_package.bat",
    "setup_wizard.bat"
)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Archive non-main launchers" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Root: $Root" -ForegroundColor Gray
Write-Host "  Archive: $ArchiveDir`n" -ForegroundColor Gray

if (-not (Test-Path $Root)) {
    Write-Host "[ERROR] Root not found: $Root" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $ArchiveDir)) {
    New-Item -ItemType Directory -Path $ArchiveDir -Force | Out-Null
    Write-Host "[CREATED] $ArchiveDir" -ForegroundColor Green
}

$moved = 0
foreach ($name in $ToArchive) {
    $src = Join-Path $Root $name
    if (Test-Path $src) {
        $dst = Join-Path $ArchiveDir $name
        if (Test-Path $dst) {
            Write-Host "  [SKIP] $name (exists in archive)" -ForegroundColor Yellow
        } else {
            try {
                Move-Item $src $dst -Force
                Write-Host "  [MOVED] $name" -ForegroundColor Green
                $moved++
            } catch {
                Write-Host "  [FAIL] $name : $_" -ForegroundColor Red
            }
        }
    }
}

Write-Host "`nDone. Moved $moved files." -ForegroundColor Cyan
Write-Host "Main entries kept: 啟動BOT.bat, 啟動_築未科技大腦_完整版.bat, etc." -ForegroundColor Gray
Write-Host "See docs/10_入口總覽.md`n" -ForegroundColor Gray

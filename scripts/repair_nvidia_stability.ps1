#Requires -RunAsAdministrator
# 築未科技 - NVIDIA 顯示穩定性修復與診斷腳本
# 用途：重啟 NVIDIA 服務、匯出錯誤紀錄、套用建議優化，降低因驅動/容器造成的當機

$ErrorActionPreference = "Stop"
$LogDir = Join-Path $env:USERPROFILE "Desktop\zhe-wei-tech\logs"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

function Write-Step { param($Msg) Write-Host "`n==> $Msg" -ForegroundColor Cyan }
function Write-Ok   { param($Msg) Write-Host "    [OK] $Msg" -ForegroundColor Green }
function Write-Warn { param($Msg) Write-Host "    [!] $Msg" -ForegroundColor Yellow }

# 建立 log 目錄
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

Write-Host "`n=== NVIDIA 穩定性修復與優化 ===" -ForegroundColor White
Write-Host "    時間: $(Get-Date -Format 'yyyy/MM/dd HH:mm:ss')" -ForegroundColor Gray

# ----- 1. 匯出近期錯誤事件（供後續比對）-----
Write-Step "匯出近期系統/應用程式錯誤事件"
$ExportPath = Join-Path $LogDir "nvidia_errors_$Timestamp.csv"
try {
    $events = Get-WinEvent -FilterHashtable @{
        LogName = 'System','Application'
        Level   = 2,3
        StartTime = (Get-Date).AddDays(-3)
    } -MaxEvents 200 -ErrorAction SilentlyContinue
    $events | Where-Object { $_.ProviderName -match 'NVIDIA|nvlddmkm|Display' } | Select-Object TimeCreated, Id, LevelDisplayName, ProviderName, Message | Export-Csv -Path $ExportPath -NoTypeInformation -Encoding UTF8
    Write-Ok "已匯出至: $ExportPath"
} catch { Write-Warn "匯出事件時發生錯誤: $_" }

# ----- 2. 重啟 NVIDIA 相關服務（暫時緩解容器崩潰）-----
Write-Step "重啟 NVIDIA 顯示相關服務"
$nvidiaServices = @(
    "NvContainerLocalSystem",
    "NVDisplay.ContainerLocalSystem",
    "NvTelemetryContainer"
)
foreach ($svc in $nvidiaServices) {
    try {
        $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
        if ($s) {
            if ($s.Status -eq 'Running') { Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2 }
            Start-Service -Name $svc -ErrorAction SilentlyContinue
            Write-Ok "已處理: $svc"
        }
    } catch { Write-Warn "服務 $svc : $_" }
}

# ----- 3. 電源計畫建議（有助 GPU 穩定性）-----
Write-Step "檢查電源計畫"
try {
    $active = powercfg /getactivescheme
    if ($active -match "381b4222-f694-41f0-9681-07f99173dbf7|8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c") {
        Write-Ok "目前為高效能/終極效能，無須變更"
    } else {
        Write-Warn "建議切換至「高效能」以減少 GPU 不穩。可執行: powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
        $setHigh = Read-Host "是否現在切換為高效能? (Y/N)"
        if ($setHigh -eq 'Y' -or $setHigh -eq 'y') {
            powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
            Write-Ok "已切換為高效能"
        }
    }
} catch { Write-Warn "電源計畫檢查失敗: $_" }

# ----- 4. 確認小記憶體傾印已啟用（方便日後分析藍屏）-----
Write-Step "檢查傾印設定"
try {
    $dumpKey = "HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl"
    $crashDump = (Get-ItemProperty -Path $dumpKey -Name CrashDumpEnabled -ErrorAction SilentlyContinue).CrashDumpEnabled
    if ($crashDump -eq 1) { Write-Ok "小記憶體傾印已啟用 (Minidump)" }
    else { Write-Warn "建議啟用小記憶體傾印: 系統內容 > 進階 > 啟動及修復 > 寫入偵錯資訊 > 小記憶體傾印" }
} catch { Write-Warn "無法讀取傾印設定" }

# ----- 5. 顯示卡與驅動資訊 -----
Write-Step "顯示卡與驅動資訊"
try {
    $gpu = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -match 'NVIDIA' } | Select-Object -First 1
    if ($gpu) {
        Write-Ok "顯示卡: $($gpu.Name)"
        Write-Ok "驅動版本: $($gpu.DriverVersion)"
        Write-Host "    建議: 至 https://www.nvidia.com/Download/index.aspx 下載 RTX 4060 Ti 最新驅動並「執行全新安裝」" -ForegroundColor Gray
    }
} catch { Write-Warn "無法取得 GPU 資訊" }

# ----- 6. 總結與下一步 -----
Write-Host "`n=== 修復與優化總結 ===" -ForegroundColor White
Write-Host @"

  已執行:
  - 匯出 NVIDIA/顯示相關錯誤事件至 logs 資料夾
  - 重啟 NVIDIA 容器與顯示服務（若仍當機，請進行驅動更新）

  建議手動步驟（根除當機）:
  1. 更新驅動: 至 NVIDIA 官網下載 RTX 4060 Ti 最新版，安裝時勾選「執行全新安裝」
  2. 若仍不穩: 使用 DDU (Display Driver Uninstaller) 在安全模式下移除驅動後再安裝
  3. 關閉 GeForce Experience 遊戲內重疊與即時錄影，減少 _nvtopps.dll 負載
  4. 檢查 GPU 散熱: 使用 HWiNFO64 或 GPU-Z 監控溫度，避免長期 >85°C

  詳細步驟請參閱專案根目錄「當機修復與優化指南.md」。

"@ -ForegroundColor Gray
Write-Host "完成。`n" -ForegroundColor Green

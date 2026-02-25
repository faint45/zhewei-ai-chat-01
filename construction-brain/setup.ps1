# ============================================================
#  築未科技 Construction Brain — 一鍵安裝腳本
#  setup.ps1
#
#  支援：Windows 10/11 x64，從零開始（無需預裝任何工具）
#  執行方式（以系統管理員身份執行 PowerShell）：
#    Set-ExecutionPolicy Bypass -Scope Process -Force
#    .\setup.ps1
# ============================================================

param(
    [string]$LicenseKey = "",
    [string]$ProjectId  = "PRJ-001",
    [string]$ProjectName = "我的第一個工程"
)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "築未科技 Construction Brain — 安裝程式"

# ─── 顏色輸出函式 ────────────────────────────────────────────
function Write-Step  { param($msg) Write-Host "`n► $msg" -ForegroundColor Cyan }
function Write-OK    { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "  [FAIL] $msg" -ForegroundColor Red }
function Write-Info  { param($msg) Write-Host "     $msg" -ForegroundColor Gray }

# ─── 常數 ───────────────────────────────────────────────────
$BASE_DIR      = "C:\ZheweiConstruction"
$REPO_URL      = "https://github.com/faint45/zhewei-ai-chat-01.git"
$REPO_DIR      = "$BASE_DIR\repo"
$APP_DIR       = "$REPO_DIR\construction-brain"
$VENV_DIR      = "$BASE_DIR\venv"
$LOG_DIR       = "$BASE_DIR\logs"
$DB_DIR        = "$BASE_DIR\db"
$CONFIG_DIR    = "$BASE_DIR\config"
$SERVICE_NAME  = "ZheweiConstruction"
$SERVICE_DISP  = "築未科技 Construction Brain"
$PORT          = 8003
$PYTHON_URL    = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
$GIT_URL       = "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/Git-2.47.1-64-bit.exe"
$OLLAMA_URL    = "https://ollama.com/download/OllamaSetup.exe"
$NSSM_URL      = "https://nssm.cc/release/nssm-2.24.zip"
$TEMP_DIR      = "$env:TEMP\zhewei_setup"

# ─── 橫幅 ───────────────────────────────────────────────────
Clear-Host
Write-Host @"
╔══════════════════════════════════════════════════════╗
║      築未科技  Construction Brain  安裝程式          ║
║      版本：1.0.0  |  需要管理員權限                  ║
╚══════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

# ─── 確認管理員權限 ──────────────────────────────────────────
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Fail "請以「系統管理員身份」執行 PowerShell 後再跑此腳本"
    Write-Info "右鍵點選 PowerShell → 以系統管理員身份執行"
    Pause; exit 1
}

# ─── 建立工作目錄 ────────────────────────────────────────────
New-Item -ItemType Directory -Force -Path $TEMP_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $BASE_DIR  | Out-Null
New-Item -ItemType Directory -Force -Path $LOG_DIR   | Out-Null
New-Item -ItemType Directory -Force -Path $DB_DIR    | Out-Null
New-Item -ItemType Directory -Force -Path $CONFIG_DIR| Out-Null

# ─── 工具函式 ────────────────────────────────────────────────
function Download-File {
    param([string]$Url, [string]$Dest)
    Write-Info "下載：$Url"
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($Url, $Dest)
}

function Add-ToPath {
    param([string]$Dir)
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($currentPath -notlike "*$Dir*") {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$Dir", "Machine")
        $env:Path += ";$Dir"
    }
}

function Test-Command {
    param([string]$Cmd)
    return (Get-Command $Cmd -ErrorAction SilentlyContinue) -ne $null
}

# ════════════════════════════════════════════════════════════
#  步驟 1：安裝 Python 3.11
# ════════════════════════════════════════════════════════════
Write-Step "步驟 1/7：確認 Python 3.11"

$pythonOk = $false
try {
    $pyVer = & python --version 2>&1
    if ($pyVer -match "3\.(10|11|12)") { $pythonOk = $true }
} catch {}

if ($pythonOk) {
    Write-OK "Python 已安裝：$pyVer"
} else {
    Write-Info "正在下載 Python 3.11.9..."
    $pyInstaller = "$TEMP_DIR\python-installer.exe"
    Download-File $PYTHON_URL $pyInstaller
    Write-Info "安裝 Python（靜默模式）..."
    Start-Process -FilePath $pyInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1" -Wait
    Add-ToPath "C:\Program Files\Python311"
    Add-ToPath "C:\Program Files\Python311\Scripts"
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Write-OK "Python 3.11 安裝完成"
}

# ════════════════════════════════════════════════════════════
#  步驟 2：安裝 Git
# ════════════════════════════════════════════════════════════
Write-Step "步驟 2/7：確認 Git"

if (Test-Command "git") {
    Write-OK "Git 已安裝：$(git --version)"
} else {
    Write-Info "正在下載 Git..."
    $gitInstaller = "$TEMP_DIR\git-installer.exe"
    Download-File $GIT_URL $gitInstaller
    Start-Process -FilePath $gitInstaller -ArgumentList "/VERYSILENT /NORESTART /NOCANCEL" -Wait
    Add-ToPath "C:\Program Files\Git\bin"
    $env:Path += ";C:\Program Files\Git\bin"
    Write-OK "Git 安裝完成"
}

# ════════════════════════════════════════════════════════════
#  步驟 3：安裝 Ollama
# ════════════════════════════════════════════════════════════
Write-Step "步驟 3/7：確認 Ollama"

if (Test-Command "ollama") {
    Write-OK "Ollama 已安裝"
} else {
    Write-Info "正在下載 Ollama..."
    $ollamaInstaller = "$TEMP_DIR\ollama-installer.exe"
    Download-File $OLLAMA_URL $ollamaInstaller
    Start-Process -FilePath $ollamaInstaller -ArgumentList "/S" -Wait
    Add-ToPath "$env:LOCALAPPDATA\Programs\Ollama"
    $env:Path += ";$env:LOCALAPPDATA\Programs\Ollama"
    Write-OK "Ollama 安裝完成"
}

# ════════════════════════════════════════════════════════════
#  步驟 4：Clone / 更新 Repo
# ════════════════════════════════════════════════════════════
Write-Step "步驟 4/7：取得程式碼（GitHub）"

if (Test-Path "$REPO_DIR\.git") {
    Write-Info "更新現有 repo..."
    & git -C $REPO_DIR pull origin main
    Write-OK "Repo 更新完成"
} else {
    Write-Info "Clone repo..."
    & git clone $REPO_URL $REPO_DIR
    Write-OK "Repo Clone 完成 → $REPO_DIR"
}

# ════════════════════════════════════════════════════════════
#  步驟 5：建立虛擬環境 & 安裝 Python 依賴
# ════════════════════════════════════════════════════════════
Write-Step "步驟 5/7：安裝 Python 依賴"

if (-not (Test-Path "$VENV_DIR\Scripts\python.exe")) {
    Write-Info "建立虛擬環境..."
    & python -m venv $VENV_DIR
}

$PIP = "$VENV_DIR\Scripts\pip.exe"
$PYTHON = "$VENV_DIR\Scripts\python.exe"

Write-Info "升級 pip..."
& $PIP install --upgrade pip --quiet

Write-Info "安裝依賴（requirements.txt）..."
& $PIP install -r "$APP_DIR\requirements.txt" --quiet
Write-OK "Python 依賴安裝完成"

# ════════════════════════════════════════════════════════════
#  步驟 6：初始化專案 & 建立 .env
# ════════════════════════════════════════════════════════════
Write-Step "步驟 6/7：初始化專案設定"

# 初始化專案資料夾
& $PYTHON "$APP_DIR\init_project.py" --project_id $ProjectId --name $ProjectName

# 建立 .env（如不存在）
$envFile = "$BASE_DIR\.env"
if (-not (Test-Path $envFile)) {
    $envContent = @"
LINE_CHANNEL_SECRET=your_line_channel_secret_here
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
DEFAULT_PROJECT_ID=$ProjectId
ZHEWEI_BASE=$BASE_DIR
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=zhewei-brain
WHISPER_MODEL=base
"@
    $envContent | Out-File -FilePath $envFile -Encoding UTF8
    Write-Warn ".env 已建立，請填入 LINE Token：$envFile"
} else {
    Write-OK ".env 已存在，略過"
}

# ════════════════════════════════════════════════════════════
#  步驟 7：安裝 Windows Service（NSSM）
# ════════════════════════════════════════════════════════════
Write-Step "步驟 7/7：安裝 Windows 背景服務"

$NSSM_EXE = "$BASE_DIR\nssm.exe"

if (-not (Test-Path $NSSM_EXE)) {
    Write-Info "下載 NSSM 服務管理工具..."
    $nssmZip = "$TEMP_DIR\nssm.zip"
    Download-File $NSSM_URL $nssmZip
    Expand-Archive -Path $nssmZip -DestinationPath $TEMP_DIR -Force
    $nssmBin = Get-ChildItem "$TEMP_DIR\nssm*\win64\nssm.exe" | Select-Object -First 1
    Copy-Item $nssmBin.FullName $NSSM_EXE
    Write-OK "NSSM 準備完成"
}

# 移除舊 service（如存在）
$existingSvc = Get-Service -Name $SERVICE_NAME -ErrorAction SilentlyContinue
if ($existingSvc) {
    Write-Info "移除舊服務..."
    & $NSSM_EXE stop $SERVICE_NAME confirm 2>$null
    & $NSSM_EXE remove $SERVICE_NAME confirm 2>$null
}

# 建立 service
$uvicornExe = "$VENV_DIR\Scripts\uvicorn.exe"
& $NSSM_EXE install $SERVICE_NAME $uvicornExe
& $NSSM_EXE set $SERVICE_NAME AppParameters "line_receiver:app --host 0.0.0.0 --port $PORT"
& $NSSM_EXE set $SERVICE_NAME AppDirectory $APP_DIR
& $NSSM_EXE set $SERVICE_NAME DisplayName $SERVICE_DISP
& $NSSM_EXE set $SERVICE_NAME Description "築未科技 Construction Brain LINE Webhook 服務"
& $NSSM_EXE set $SERVICE_NAME AppEnvironmentExtra "ZHEWEI_BASE=$BASE_DIR"
& $NSSM_EXE set $SERVICE_NAME AppStdout "$LOG_DIR\service.log"
& $NSSM_EXE set $SERVICE_NAME AppStderr "$LOG_DIR\service_err.log"
& $NSSM_EXE set $SERVICE_NAME AppRotateFiles 1
& $NSSM_EXE set $SERVICE_NAME AppRotateBytes 10485760
& $NSSM_EXE set $SERVICE_NAME Start SERVICE_AUTO_START

Start-Service -Name $SERVICE_NAME
$svc = Get-Service -Name $SERVICE_NAME
Write-OK "Windows 服務已啟動：$SERVICE_NAME（狀態：$($svc.Status)）"

# ════════════════════════════════════════════════════════════
#  完成報告
# ════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║           [OK]  安裝完成！                            ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  安裝目錄    ：$BASE_DIR" -ForegroundColor White
Write-Host "  LINE Webhook：http://localhost:$PORT/webhook" -ForegroundColor White
Write-Host "  專案代碼    ：$ProjectId" -ForegroundColor White
Write-Host ""
Write-Host "  ─── 下一步 ───────────────────────────────────────" -ForegroundColor Yellow
Write-Host "  1. 填入 LINE Token：$envFile" -ForegroundColor Yellow
Write-Host "  2. 設定 Cloudflare Tunnel 指向 localhost:$PORT" -ForegroundColor Yellow
Write-Host "  3. 啟動 Ollama 並載入模型：ollama run zhewei-brain" -ForegroundColor Yellow
Write-Host "  4. 餵入知識庫：python kb_ingest.py --folder $BASE_DIR\03_KB --category 施工法" -ForegroundColor Yellow
Write-Host ""
Write-Host "  服務管理指令：" -ForegroundColor Cyan
Write-Host "    啟動：Start-Service $SERVICE_NAME" -ForegroundColor Cyan
Write-Host "    停止：Stop-Service  $SERVICE_NAME" -ForegroundColor Cyan
Write-Host "    日誌：Get-Content $LOG_DIR\service.log -Tail 50 -Wait" -ForegroundColor Cyan
Write-Host ""
Pause

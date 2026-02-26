# Zhe-Wei Tech — Sync to Oracle Cloud VPS
# Runs on local Windows machine via Task Scheduler every 30 minutes
# Syncs code + data to Google Drive, which Oracle VPS pulls from
#
# Setup: schtasks /create /tn "ZheweiCloudSync" /tr "powershell -File D:\zhe-wei-tech\scripts\sync_to_oracle.ps1" /sc minute /mo 30

$ErrorActionPreference = "Continue"
$ROOT = "D:\zhe-wei-tech"
$LOG = "$ROOT\logs\cloud_sync.log"
$RCLONE = "rclone"
$REMOTE = "gdrive"
$REMOTE_BASE = "${REMOTE}:Zhewei_Brain"

# Ensure log directory
New-Item -ItemType Directory -Force -Path "$ROOT\logs" | Out-Null

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$ts] $msg" | Tee-Object -FilePath $LOG -Append
}

Log "=== Cloud sync started ==="

# 1. Sync main project code (exclude heavy dirs)
Log "[1/4] Syncing project code..."
& $RCLONE sync "$ROOT" "${REMOTE_BASE}/tech_repo_backup" `
    --exclude ".venv312/**" `
    --exclude "venv*/**" `
    --exclude "node_modules/**" `
    --exclude "ComfyUI/**" `
    --exclude "Jarvis_Training/.venv312/**" `
    --exclude "Jarvis_Training/chroma_db/**" `
    --exclude "**/__pycache__/**" `
    --exclude ".git/**" `
    --exclude "*.pyc" `
    --exclude "dist/**" `
    --exclude "logs/**" `
    --exclude "D/**" `
    --exclude "workspace/metagpt*/**" `
    --exclude "MetaGPT_env/**" `
    --transfers 4 `
    --checkers 8 `
    --quiet 2>&1 | ForEach-Object { Log $_ }

if ($LASTEXITCODE -eq 0) { Log "[1/4] Project code synced OK" }
else { Log "[1/4] WARNING: Project code sync had issues (exit=$LASTEXITCODE)" }

# 2. Sync brain_workspace (auth, orders, licenses, etc.)
Log "[2/4] Syncing brain_workspace..."
& $RCLONE sync "$ROOT\brain_workspace" "${REMOTE_BASE}/workspace_backup" `
    --exclude "**/__pycache__/**" `
    --transfers 4 `
    --quiet 2>&1 | ForEach-Object { Log $_ }

if ($LASTEXITCODE -eq 0) { Log "[2/4] Brain workspace synced OK" }
else { Log "[2/4] WARNING: Brain workspace sync had issues" }

# 3. Sync .env (critical for API keys)
Log "[3/4] Syncing .env..."
& $RCLONE copy "$ROOT\.env" "${REMOTE_BASE}/env_backup/" --quiet 2>&1 | ForEach-Object { Log $_ }

if ($LASTEXITCODE -eq 0) { Log "[3/4] .env synced OK" }
else { Log "[3/4] WARNING: .env sync had issues" }

# 4. Sync zhewei_memory
Log "[4/4] Syncing memory..."
& $RCLONE sync "$ROOT\zhewei_memory" "${REMOTE_BASE}/memory_backup" `
    --quiet 2>&1 | ForEach-Object { Log $_ }

if ($LASTEXITCODE -eq 0) { Log "[4/4] Memory synced OK" }
else { Log "[4/4] WARNING: Memory sync had issues" }

Log "=== Cloud sync completed ==="

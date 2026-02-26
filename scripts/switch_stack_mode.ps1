param(
    [ValidateSet("daily", "dev")]
    [string]$Mode = "daily"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$dailyKeep = @(
    "zhewei_brain",
    "zhe-wei-tech-tunnel-1",
    "zhe-wei-ollama",
    "zhewei-qdrant"
)

$devExtras = @(
    "zhewei-n8n",
    "openhands",
    "open-webui",
    "webui-mcpo",
    "docker-web-1",
    "docker-api-1",
    "docker-worker-1",
    "docker-plugin_daemon-1",
    "docker-db_postgres-1",
    "docker-redis-1",
    "docker-weaviate-1",
    "docker-sandbox-1",
    "docker-nginx-1",
    "docker-ssrf_proxy-1"
)

if ($Mode -eq "daily") {
    Write-Host "[MODE] daily - keep core services only"
    foreach ($c in $dailyKeep) {
        docker start $c 2>$null | Out-Null
    }
    foreach ($c in $devExtras) {
        docker stop $c 2>$null | Out-Null
    }
    Write-Host "[OK] switched to daily mode"
    exit 0
}

Write-Host "[MODE] dev - enable full engineering stack"
foreach ($c in $dailyKeep) {
    docker start $c 2>$null | Out-Null
}
foreach ($c in $devExtras) {
    docker start $c 2>$null | Out-Null
}
Write-Host "[OK] switched to dev mode"

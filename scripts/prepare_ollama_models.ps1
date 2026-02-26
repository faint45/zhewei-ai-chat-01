param(
    [string[]]$Models = @("qwen2.5:7b", "qwen2.5:14b")
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

foreach ($m in $Models) {
    Write-Host "[INFO] pulling $m ..."
    docker exec zhe-wei-ollama ollama pull $m
    if ($LASTEXITCODE -ne 0) {
        throw "pull failed: $m"
    }
}

Write-Host "[INFO] final model list"
docker exec zhe-wei-ollama ollama list

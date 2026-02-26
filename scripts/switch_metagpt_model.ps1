param(
    [ValidateSet('gemini','ollama')]
    [string]$Provider = 'gemini',
    [string]$Model = ''
)

$root = "D:\zhe-wei-tech"
$envFile = Join-Path $root '.env'
$config = "C:\Users\user\.metagpt\config2.yaml"
if (!(Test-Path $config)) {
    throw "MetaGPT config not found: $config"
}

if ($Provider -eq 'gemini') {
    $line = if (Test-Path $envFile) { Get-Content $envFile | Where-Object { $_ -match '^GEMINI_API_KEY=' } | Select-Object -First 1 } else { $null }
    if (-not $line) { throw 'GEMINI_API_KEY not found in .env' }
    $key = ($line -replace '^GEMINI_API_KEY=','').Trim()
    if (-not $Model) { $Model = 'gemini-2.0-flash' }

    @"
llm:
  api_type: "gemini"
  model: "$Model"
  base_url: "https://generativelanguage.googleapis.com"
  api_key: "$key"
  timeout: 600
  stream: false
"@ | Set-Content -Path $config -Encoding UTF8

    Write-Output "Switched MetaGPT provider to GEMINI ($Model)"
}

if ($Provider -eq 'ollama') {
    $line = if (Test-Path $envFile) { Get-Content $envFile | Where-Object { $_ -match '^OLLAMA_BASE_URL=' } | Select-Object -First 1 } else { $null }
    $base = if ($line) { ($line -replace '^OLLAMA_BASE_URL=','').Trim() } else { 'http://localhost:11434' }
    if ($base -notmatch '/api$') { $base = "$base/api" }
    if (-not $Model) { $Model = 'zhewei-brain:latest' }

    @"
llm:
  api_type: "ollama"
  model: "$Model"
  base_url: "$base"
  api_key: "ollama-local"
  timeout: 600
  stream: false
"@ | Set-Content -Path $config -Encoding UTF8

    Write-Output "Switched MetaGPT provider to OLLAMA ($Model)"
}

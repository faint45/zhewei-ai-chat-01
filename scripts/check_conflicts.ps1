# Merge conflict check
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$files = Get-ChildItem -Path $root -Recurse -Include *.py,*.md,*.json,*.bat,*.yml -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch '[\\/](venv|\.venv|archive|node_modules|site-packages)[\\/]' }
$found = @()
foreach ($f in $files) {
    $c = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
    if ($c -match "<<<<<<< HEAD" -or $c -match ">>>>>>> ") { $found += $f.FullName }
}
if ($found.Count -eq 0) { Write-Host "[OK] No merge conflicts" } else { $found | ForEach-Object { Write-Host "[CONFLICT] $_" } }

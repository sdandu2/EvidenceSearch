$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root
$python = Join-Path $root '.venv\Scripts\python.exe'
if (Test-Path $python) {
    & $python -u .\scripts\stage_public_release.py --stage
} else {
    & py -3 .\scripts\stage_public_release.py --stage
}
if ($LASTEXITCODE -ne 0) { throw 'Staging failed.' }
if (Test-Path $python) {
    & $python -u .\scripts\audit_public_release.py
} else {
    & py -3 .\scripts\audit_public_release.py
}
if ($LASTEXITCODE -ne 0) { throw 'Publication audit blocked: see output above.' }
Write-Host 'Review git diff --cached --stat and git diff --cached before committing.'

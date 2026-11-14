$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
Push-Location $root
try {
    if (-not (Test-Path $python)) { throw 'Python virtual environment is missing.' }
    & $python -m backend.smoke_live --frontend 'http://localhost:3000'
    if ($LASTEXITCODE -ne 0) { throw 'Live-search smoke test failed. Inspect the error and backend logs.' }
} finally { Pop-Location }

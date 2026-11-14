$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
$web = Join-Path $root 'web'
if (-not (Test-Path $python)) { throw 'Missing .venv. Create/install the EvidenceSearch Python environment first.' }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'Node.js/npm not found. Install Node.js 22 LTS and reopen VS Code.' }
if (-not (Test-Path (Join-Path $web 'node_modules'))) { throw 'Run npm install inside the web folder first.' }
& $python -m backend.verify_assets
if ($LASTEXITCODE -ne 0) { throw 'The SciFact artifact audit failed; see the output above.' }
$apiCommand = "& '$python' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
Start-Process powershell.exe -WorkingDirectory $root -ArgumentList '-NoExit','-Command',$apiCommand
Start-Process powershell.exe -WorkingDirectory $web -ArgumentList '-NoExit','-Command','npm run dev'
Write-Host 'Started API on http://127.0.0.1:8000/docs and Next.js on http://localhost:3000.'
Write-Host 'Open http://localhost:3000 when the Next.js terminal shows Ready.'

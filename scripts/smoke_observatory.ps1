$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
& .\.venv\Scripts\python.exe -m backend.smoke_observatory
if ($LASTEXITCODE -ne 0) { throw "Observatory data-integrity test failed" }

$ErrorActionPreference = 'Stop'
$web = 'http://localhost:3000'
Write-Host "Checking Observatory homepage at $web ..."
$page = Invoke-WebRequest -Uri $web -UseBasicParsing -TimeoutSec 45
if ($page.StatusCode -ne 200 -or $page.Content -notmatch 'SELECT A RESEARCH WORLD') {
    throw 'The homepage did not render the expected Observatory world selector. Check Next.js terminal errors and restart the frontend.'
}
Write-Host 'PASS: Observatory world selection is rendered at localhost:3000.'
Write-Host 'The source-model inference and abstract-provenance checks remain in scripts/smoke_observatory.ps1.'

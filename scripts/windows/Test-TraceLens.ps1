[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $projectRoot

docker run --rm -v "${projectRoot}:/src" -w /src python:3.12-slim `
    sh -c "pip install -q -r requirements.txt -r requirements-dev.txt && pytest"
if ($LASTEXITCODE -ne 0) { throw "Python tests failed." }
docker run --rm -v "${projectRoot}:/src" -v /src/apps/web/node_modules -w /src/apps/web node:22-alpine `
    sh -c "npm ci --quiet && npm run typecheck && npm run build"
if ($LASTEXITCODE -ne 0) { throw "Frontend type checks failed." }
Write-Host "TraceLens checks passed." -ForegroundColor Green

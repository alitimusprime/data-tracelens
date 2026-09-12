[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $projectRoot
docker compose down
if ($LASTEXITCODE -ne 0) { throw "Docker Compose could not stop cleanly." }
Write-Host "TraceLens stopped. Persistent local data was preserved." -ForegroundColor Green

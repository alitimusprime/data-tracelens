[CmdletBinding()]
param(
    [switch]$ConfirmReset
)

if (-not $ConfirmReset) {
    throw "Reset deletes TraceLens databases and retained telemetry. Re-run with -ConfirmReset to continue."
}

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $projectRoot
docker compose down --volumes
if ($LASTEXITCODE -ne 0) { throw "Docker Compose reset failed." }
Write-Host "TraceLens containers and project volumes were removed. Images remain cached." -ForegroundColor Yellow

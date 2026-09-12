[CmdletBinding()]
param(
    [switch]$Logs
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $projectRoot
docker compose ps
if ($Logs) {
    docker compose logs --tail 100 tracelens-api analyzer web gateway order inventory payment notification
}

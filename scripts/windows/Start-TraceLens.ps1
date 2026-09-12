[CmdletBinding()]
param(
    [switch]$NoBuild,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $projectRoot

& (Join-Path $PSScriptRoot "Check-Prerequisites.ps1")

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from the safe local example." -ForegroundColor Yellow
}

Write-Host "Starting TraceLens. The first build can take several minutes..." -ForegroundColor Cyan
if ($NoBuild) {
    docker compose up -d
} else {
    docker compose up -d --build
}
if ($LASTEXITCODE -ne 0) { throw "Docker Compose could not start the stack." }

$deadline = (Get-Date).AddMinutes(4)
do {
    Start-Sleep -Seconds 3
    try {
        $ready = Invoke-RestMethod "http://127.0.0.1:8080/ready" -TimeoutSec 5
        $webReady = (Invoke-WebRequest "http://127.0.0.1:3000" -TimeoutSec 5 -UseBasicParsing).StatusCode -eq 200
    } catch {
        $ready = $null
        $webReady = $false
    }
    Write-Host "." -NoNewline
} until (($ready.status -eq "ready" -and $webReady) -or (Get-Date) -gt $deadline)
Write-Host ""

if (-not $ready -or $ready.status -ne "ready" -or -not $webReady) {
    docker compose ps
    throw "TraceLens API did not become ready. Run scripts\windows\Status-TraceLens.ps1 for details."
}

Write-Host "TraceLens is ready." -ForegroundColor Green
Write-Host "  Product UI:    http://localhost:3000"
Write-Host "  API docs:      http://localhost:8080/docs"
Write-Host "  Raw telemetry: http://localhost:3001 (admin / admin)"

if (-not $NoBrowser) {
    Start-Process "http://localhost:3000"
}

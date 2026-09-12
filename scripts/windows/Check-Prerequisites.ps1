[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "TraceLens prerequisite check" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI was not found. Install or start Docker Desktop first."
}

$dockerInfo = docker info --format '{{.OSType}}|{{.OperatingSystem}}' 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is not running. Restart into Windows 10 - Docker Mode, then open Docker Desktop."
}

$parts = $dockerInfo -split '\|'
if ($parts[0] -ne "linux") {
    throw "TraceLens requires Docker Desktop Linux containers. Current container OS: $($parts[0])."
}

$memoryGb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
$projectDrive = (Get-Item $PSScriptRoot).PSDrive.Name
$freeGb = [math]::Round((Get-PSDrive $projectDrive).Free / 1GB, 1)

Write-Host "  Docker engine: $($parts[1])" -ForegroundColor Green
Write-Host "  Container OS: $($parts[0])" -ForegroundColor Green
Write-Host "  System RAM: $memoryGb GB" -ForegroundColor Green
Write-Host "  Free space on ${projectDrive}: $freeGb GB" -ForegroundColor Green

if ($memoryGb -lt 12) {
    Write-Warning "The complete stack is designed for at least 12 GB of system RAM."
}
if ($freeGb -lt 15) {
    Write-Warning "Less than 15 GB is free on the project drive. Docker images may need cleanup later."
}

Write-Host "Prerequisites passed." -ForegroundColor Green

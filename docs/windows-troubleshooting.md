# Windows Troubleshooting

## Docker API is unavailable

Confirm that you booted **Windows 10 - Docker Mode**, then start Docker Desktop and run:

```powershell
docker version
docker info --format 'Container OS: {{.OSType}} | Engine: {{.OperatingSystem}}'
```

The server section must exist and the container OS must be `linux`.

## Valorant reports VAN9005

Stop TraceLens, shut down Windows, and select **Windows 10 - Valorant Mode** at boot. That entry has the hypervisor disabled. Do not modify the boot entries unless the known working switch stops appearing.

## PowerShell blocks scripts

Use a process-scoped policy that disappears when the terminal closes:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

## A container repeatedly restarts

```powershell
.\scripts\windows\Status-TraceLens.ps1 -Logs
docker compose ps
```

The API waits for PostgreSQL and runs the migration before becoming healthy. On the first start, image downloads can delay dependencies.

## Port conflict

The project uses host ports 3000, 3001, 8000 through 8005, 8080, 8222, and 9090. Stop the conflicting application or change the host side of the relevant mapping in `docker-compose.yml`.

## Disk pressure on D

Ordinary `Stop-TraceLens.ps1` preserves project data. `Reset-TraceLens.ps1 -ConfirmReset` removes this project's named volumes. Docker Desktop can show image usage, but do not delete unrelated project data during cleanup.

## Full clean rebuild

```powershell
.\scripts\windows\Stop-TraceLens.ps1
docker compose build --no-cache
.\scripts\windows\Start-TraceLens.ps1 -NoBuild
```

# Explicit operator command. Creates a new backup INSIDE the repository only.
# No source data is deleted, modified, or overwritten. PowerShell 5.1 compatible.
Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$destination = Join-Path $root "backups"
if (-not (Test-Path $destination)) { New-Item -ItemType Directory -Path $destination | Out-Null }
$disk = Get-PSDrive -Name ((Get-Item $root).PSDrive.Name)
if ($disk.Free -lt 512MB) { throw "Abort: insufficient free disk space for database backup" }
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssfffZ")
$name = "triagedock-$stamp.dump"
$target = Join-Path $destination $name
if (Test-Path $target) { throw "Refusing to overwrite existing backup" }
Push-Location $root
try {
    $db = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "triagedock" }
    $user = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "triagedock" }
    if ($db -notmatch '^[a-zA-Z0-9_]+$' -or $user -notmatch '^[a-zA-Z0-9_]+$') {
        throw "Database identifier must be alphanumeric or underscore"
    }
    $containerPath = "/tmp/$name"
    docker compose exec -T db pg_dump -U $user -d $db -Fc -f $containerPath
    if ($LASTEXITCODE -ne 0) { throw "pg_dump failed. No successful backup claimed." }
    docker compose cp "db:$containerPath" $target
    if ($LASTEXITCODE -ne 0) { throw "Backup copy failed. No successful backup claimed." }
    if ((Get-Item $target).Length -lt 100) { throw "Backup file unexpectedly small" }
    Write-Host "Backup created: $target"
    Write-Host "Validate it in an isolated database before relying on it."
} finally { Pop-Location }

# Restores to a UNIQUE, isolated Compose project. Existing TriageDock DB is untouched.
# Persistent verification volume is retained until you explicitly authorize cleanup.
param([Parameter(Mandatory=$true)][string]$Backup)
Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$full = [IO.Path]::GetFullPath($Backup)
$allowed = [IO.Path]::GetFullPath((Join-Path $root "backups")) + [IO.Path]::DirectorySeparatorChar
if (-not $full.StartsWith($allowed, [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path $full)) {
    throw "Backup must be an existing file under this repository's backups folder"
}
$project = "triagedock-restore-" + [guid]::NewGuid().ToString("N").Substring(0,8)
Push-Location $root
try {
    docker compose -p $project up -d db
    if ($LASTEXITCODE -ne 0) { throw "Isolated database did not start" }
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        docker compose -p $project exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | Out-Null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw "Isolated PostgreSQL did not become ready" }
    docker compose -p $project cp $full "db:/tmp/restore-check.dump"
    if ($LASTEXITCODE -ne 0) { throw "Could not copy backup to isolated database" }
    docker compose -p $project exec -T db sh -c 'pg_restore --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB" "/tmp/restore-check.dump"'
    if ($LASTEXITCODE -ne 0) { throw "Restore failed; isolated verification data retained for inspection" }
    docker compose -p $project exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT COUNT(*) FROM incidents_incident"'
    if ($LASTEXITCODE -ne 0) { throw "Restored incident schema verification failed" }
    Write-Host "Isolated restore succeeded. Verification project: $project"
} finally {
    docker compose -p $project down
    Pop-Location
}

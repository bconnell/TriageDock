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
$partial = Join-Path $destination ("." + $name + ".partial")
if ((Test-Path $target) -or (Test-Path $partial)) {
    throw "Refusing to overwrite an existing backup or partial backup"
}
Push-Location $root
try {
    $containerPath = "/tmp/$name"
    $dump = 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "' + $containerPath + '"'
    docker compose exec -T db sh -c $dump
    if ($LASTEXITCODE -ne 0) { throw "pg_dump failed. No successful backup claimed." }
    # Inspect the newly created archive format before copying it. This does
    # NOT establish successful restoration or completeness of the source data.
    docker compose exec -T db pg_restore --list $containerPath | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "pg_restore could not read the archive manifest" }
    $sourceHashLine = [string](docker compose exec -T db sha256sum $containerPath)
    if ($LASTEXITCODE -ne 0) {
        throw "Cannot compute container archive checksum; backup not finalized"
    }
    $hashMatch = [regex]::Match($sourceHashLine, '^[a-fA-F0-9]{64}(?=\s)')
    if (-not $hashMatch.Success) {
        throw "Invalid checksum output from container; backup not finalized"
    }
    $sourceDigest = $hashMatch.Value.ToUpperInvariant()
    docker compose cp "db:$containerPath" $partial
    if ($LASTEXITCODE -ne 0) { throw "Backup copy failed; incomplete file retained for inspection" }
    if ((Get-Item $partial).Length -lt 100) { throw "Backup copy unexpectedly small; not finalized" }
    $digest = (Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash
    if ($digest -ne $sourceDigest) {
        throw "Host archive does not match container checksum; partial file retained"
    }
    Move-Item -LiteralPath $partial -Destination $target -ErrorAction Stop
    Write-Host "Backup copied: $target"
    Write-Host "SHA256: $digest"
    Write-Host "Unverified until restored into an isolated database and inspected."
    # Remove only the invocation's own temporary container archive after the
    # host backup is finalized. Never remove a user-supplied path or volume.
    docker compose exec -T db rm -- $containerPath
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Temporary archive remains in the database container: $containerPath"
    }
} finally { Pop-Location }

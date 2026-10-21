# Explicit isolated Docker test. PowerShell 5.1; run only when authorized.
# Personal file safety: no edits outside this repository and its owned test project.
# System safety: no registry, firewall, global tooling, unrelated services or
# parallel heavy work. Stop if physical memory, commit or disk headroom is low.
param([switch]$ConfirmIsolatedRun)
Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"
if (-not $ConfirmIsolatedRun) {
    throw "Pass -ConfirmIsolatedRun to authorize temporary project-owned test containers."
}
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $root "compose.yaml"))) { throw "Unexpected repository path" }
$disk = Get-PSDrive -Name ((Get-Item $root).PSDrive.Name)
$os = Get-CimInstance Win32_OperatingSystem
$memory = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
if ($null -eq $os -or $null -eq $memory) { throw "Abort: memory budget cannot be measured" }
if ($disk.Free -lt 5GB) { throw "Abort: less than 5 GiB free disk space" }
if ([int64]$os.FreePhysicalMemory -lt 2097152) { throw "Abort: less than 2 GiB free physical RAM" }
if (([int64]$memory.CommitLimit - [int64]$memory.CommittedBytes) -lt 2147483648) {
    throw "Abort: less than 2 GiB free commit budget"
}
if (-not (Test-Path (Join-Path $root ".env"))) {
    throw "Provide a local ignored .env containing real unique test credentials"
}
$sha = (& git -C $root rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $sha -notmatch '^[0-9a-f]{40}$') { throw "Cannot identify candidate commit" }
$changes = @(& git -C $root status --porcelain)
if ($LASTEXITCODE -ne 0 -or $changes.Count -gt 0) {
    throw "Use a clean committed worktree so test evidence names an exact candidate"
}

$project = "td-check-" + [guid]::NewGuid().ToString("N").Substring(0, 10)
$oldParallel = $env:COMPOSE_PARALLEL_LIMIT
$logDir = Join-Path $root ".validation"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssfffZ")
$log = Join-Path $logDir ("compose-" + $sha.Substring(0, 12) + "-" + $stamp + ".txt")
$transcriptStarted = $false
Push-Location $root
try {
    Start-Transcript -Path $log -ErrorAction Stop | Out-Null
    $transcriptStarted = $true
    Write-Host "Testing commit $sha in isolated project $project"
    $env:COMPOSE_PARALLEL_LIMIT = "1"
    docker compose -p $project config --quiet
    if ($LASTEXITCODE -ne 0) { throw "Compose configuration is invalid" }
    docker compose -p $project build web
    if ($LASTEXITCODE -ne 0) { throw "Container image build failed" }
    docker compose -p $project up -d db redis
    if ($LASTEXITCODE -ne 0) { throw "Isolated PostgreSQL/Redis failed to start" }
    docker compose -p $project run --rm --no-deps web python manage.py check
    if ($LASTEXITCODE -ne 0) { throw "PostgreSQL-backed Django checks failed" }
    docker compose -p $project run --rm --no-deps web python manage.py makemigrations --check --dry-run
    if ($LASTEXITCODE -ne 0) { throw "Migration drift check failed" }
    docker compose -p $project run --rm --no-deps web python manage.py test incidents --verbosity 2
    if ($LASTEXITCODE -ne 0) { throw "PostgreSQL-backed test suite failed" }
    Write-Host "PASS: isolated PostgreSQL/Redis tests for commit $sha"
    Write-Host "Browser, webhook-receiver and backup-restore acceptance remain separate."
} finally {
    # Only the uniquely named test project's containers/network are stopped.
    # Volumes and data are preserved: deliberately no --volumes or blanket prune.
    docker compose -p $project down
    if ($null -eq $oldParallel) { Remove-Item Env:COMPOSE_PARALLEL_LIMIT -ErrorAction SilentlyContinue }
    else { $env:COMPOSE_PARALLEL_LIMIT = $oldParallel }
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
    Pop-Location
}

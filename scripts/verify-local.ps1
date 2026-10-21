# TriageDock exact-revision local validation, Windows PowerShell 5.1.
# Personal file/data safety: work inside this repository only; preserve user files,
# other repositories, local incident data, uncommitted work, and secrets.
# System safety: no registry, firewall, OS, security product, startup or global tool
# changes; measure RAM, commit and disk before starting; execute gates serially.
param([switch]$WithDocker)
Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $root "backend\manage.py"))) {
    throw "Unexpected repository path"
}
$disk = Get-PSDrive -Name ((Get-Item $root).PSDrive.Name)
if ($disk.Free -lt 2GB) { throw "Abort: less than 2 GiB free on project drive" }
$memory = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
$osMemory = Get-CimInstance Win32_OperatingSystem
if ($null -eq $memory -or $null -eq $osMemory) { throw "Abort: memory measurements unavailable" }
if (([int64]$memory.CommitLimit - [int64]$memory.CommittedBytes) -lt 1073741824) {
    throw "Abort: less than 1 GiB available commit budget"
}
if ([int64]$osMemory.FreePhysicalMemory -lt 1572864) {
    throw "Abort: less than 1.5 GiB physical RAM available"
}

$sha = (& git -C $root rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $sha -notmatch '^[0-9a-f]{40}$') {
    throw "Cannot identify the candidate commit"
}
$changes = @(& git -C $root status --porcelain)
if ($LASTEXITCODE -ne 0 -or $changes.Count -gt 0) {
    throw "A clean committed worktree is required. Preserve and commit existing changes."
}
$logDir = Join-Path $root ".validation"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssfffZ")
$log = Join-Path $logDir ("local-gates-" + $sha.Substring(0,12) + "-" + $stamp + ".txt")
$transcriptStarted = $false
$originalDebug = $env:DJANGO_DEBUG
$originalEngine = $env:DATABASE_ENGINE

Push-Location $root
try {
    Start-Transcript -Path $log -ErrorAction Stop | Out-Null
    $transcriptStarted = $true
    Write-Host "Exact candidate: $sha"
    Write-Host "Local evidence file: $log"
    git diff --check
    if ($LASTEXITCODE -ne 0) { throw "Git whitespace gate failed" }
    python scripts/verify_source.py
    if ($LASTEXITCODE -ne 0) { throw "Python source gate failed" }
    python scripts/check_public_copy.py
    if ($LASTEXITCODE -ne 0) { throw "Public copy gate failed" }

    $py = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path $py)) {
        throw "Missing repo-local Python environment. Install backend/requirements-dev.lock and pip-audit."
    }
    $env:DJANGO_DEBUG = "1"
    $env:DATABASE_ENGINE = "sqlite"
    & $py backend/manage.py check
    if ($LASTEXITCODE -ne 0) { throw "Django checks failed" }
    & $py backend/manage.py makemigrations --check --dry-run
    if ($LASTEXITCODE -ne 0) { throw "Migration drift gate failed" }
    & $py backend/manage.py test incidents --verbosity 2
    if ($LASTEXITCODE -ne 0) { throw "Backend regression tests failed" }

    Push-Location frontend
    try {
        if (-not (Test-Path "node_modules")) { throw "Install repo-local frontend dependencies using npm ci" }
        npm run typecheck
        if ($LASTEXITCODE -ne 0) { throw "TypeScript gate failed" }
        npm test
        if ($LASTEXITCODE -ne 0) { throw "Frontend unit tests failed" }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
        npm audit --omit=dev --audit-level=high
        if ($LASTEXITCODE -ne 0) { throw "Frontend vulnerability audit failed or could not run" }
    } finally {
        Pop-Location
    }

    & $py -m pip_audit -r backend/requirements.lock
    if ($LASTEXITCODE -ne 0) { throw "Python dependency audit failed or could not run" }

    if ($WithDocker) {
        if ([int64]$osMemory.FreePhysicalMemory -lt 2097152) {
            throw "Abort Docker configuration gate: less than 2 GiB physical RAM available"
        }
        docker compose config --quiet
        if ($LASTEXITCODE -ne 0) { throw "Compose configuration gate failed" }
        Write-Host "Compose configuration checked; containers were not started."
    }
    Write-Host "PASS: exact-commit source, Django, frontend, and vulnerability gates."
} finally {
    if ($null -eq $originalDebug) { Remove-Item Env:DJANGO_DEBUG -ErrorAction SilentlyContinue }
    else { $env:DJANGO_DEBUG = $originalDebug }
    if ($null -eq $originalEngine) { Remove-Item Env:DATABASE_ENGINE -ErrorAction SilentlyContinue }
    else { $env:DATABASE_ENGINE = $originalEngine }
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
    Pop-Location
}

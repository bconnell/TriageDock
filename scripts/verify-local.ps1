# Runs only in this repository. Windows PowerShell 5.1 compatible.
# Personal data safety: never modify Desktop/Documents/profile/other repos.
# System safety: no registry, global tooling, firewall or service changes.
param([switch]$WithDocker)
Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $root "backend\manage.py"))) { throw "Unexpected repository path" }
$disk = Get-PSDrive -Name ((Get-Item $root).PSDrive.Name)
if ($disk.Free -lt 2GB) { throw "Abort: less than 2 GB free on project drive" }
$memory = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
$osMemory = Get-CimInstance Win32_OperatingSystem
if ($null -eq $memory -or $null -eq $osMemory) { throw "Abort: memory budget cannot be measured safely" }
if (([int64]$memory.CommitLimit - [int64]$memory.CommittedBytes) -lt 1073741824) {
    throw "Abort: less than 1 GiB available commit budget"
}
if ([int64]$osMemory.FreePhysicalMemory -lt 1572864) {
    throw "Abort: less than 1.5 GiB physical RAM available"
}
Push-Location $root
try {
    git diff --check
    if ($LASTEXITCODE -ne 0) { throw "Git whitespace gate failed" }
    python scripts/verify_source.py
    if ($LASTEXITCODE -ne 0) { throw "Source gate failed" }
    python scripts/check_public_copy.py
    if ($LASTEXITCODE -ne 0) { throw "Documentation consistency gate failed" }

    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        throw "Missing repo-local .venv. Create it and install backend/requirements-dev.lock first."
    }
    $py = Join-Path $root ".venv\Scripts\python.exe"
    $env:DJANGO_DEBUG = "1"
    $env:DATABASE_ENGINE = "sqlite"
    & $py backend/manage.py check
    if ($LASTEXITCODE -ne 0) { throw "Django checks failed" }
    & $py backend/manage.py makemigrations --check --dry-run
    if ($LASTEXITCODE -ne 0) { throw "Migration drift check failed" }
    & $py backend/manage.py test incidents --verbosity 2
    if ($LASTEXITCODE -ne 0) { throw "Django tests failed" }

    Push-Location frontend
    try {
        if (-not (Test-Path node_modules)) { throw "Missing repo-local frontend node_modules; run npm ci." }
        npm run typecheck
        if ($LASTEXITCODE -ne 0) { throw "TypeScript gate failed" }
        npm test
        if ($LASTEXITCODE -ne 0) { throw "Frontend tests failed" }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
    } finally { Pop-Location }

    if ($WithDocker) {
        $os = Get-CimInstance Win32_OperatingSystem
        if ([int64]$os.FreePhysicalMemory -lt 2097152) { throw "Abort Docker gate: less than 2 GiB physical RAM available" }
        docker compose config --quiet
        if ($LASTEXITCODE -ne 0) { throw "Compose config gate failed" }
        Write-Host "Docker config verified. Live Compose testing requires a separate, explicit manual run."
    }
    Write-Host "All requested local source/backend/frontend gates PASSED."
} finally {
    Pop-Location
}

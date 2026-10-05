#!/usr/bin/env pwsh
<#
Unit-test runner for an EMBEDDED CRM integration plug-in (PowerShell port).

The integration's generated code is consumed in-process by the host CRM
backend, so unit tests must run against the host's source layout. To let
several renders run side by side without clobbering each other (or the real
host tree), every run works in its OWN isolated workspace in the system temp
directory: the host codebase is snapshotted into it, the renderer's build
folder ($args[0]) is overlaid onto the snapshot at the module's package path
(src/integrations/<name>/ and tests/integrations/<name>/), and pytest runs
from the snapshot root scoped to the staged integration package(s). The real
host tree is never written to, and the workspace is removed on exit.

Tests run on the host project's OWN virtual environment at
$HOST_CODEBASE_ROOT\.venv (the one scripts\start.ps1 provisions), so unit
tests use the exact interpreter and installed dependencies the host uses.
The venv is only read, never modified, so concurrent runs can share it.
The script does not create a throwaway venv: the project's floor is Python
>= 3.12 and any interpreter at or above it is fine, but the tests must run on
the SAME one as the host. Selecting an interpreter off PATH here broke that -
PATH may offer a newer Python than the host venv was built with.

  Usage: run_unittests_python.ps1 <source_build_folder>

The host codebase root defaults to the parent of the plain/ folder and can
be overridden with the HOST_CODEBASE_ROOT environment variable.

This is the Windows counterpart of run_unittests_python.sh and does exactly the
same thing: same staging model, same host-venv requirement, same pytest flags,
same exit codes (69 = host venv missing/invalid, missing dependencies, or
workspace setup failure, 1 = bad usage / no tests to run, 2 = missing input or
host root, otherwise pytest's own exit code).
#>

function Write-Err($msg) { [Console]::Error.WriteLine($msg) }

# Top-level host entries NOT copied into the workspace snapshot: VCS metadata,
# the venv (used in place), secrets, local data, caches, agent tooling, and the
# ***plain project itself (plain/ holds generated copies of the tests that
# would collide on module names).
$SnapshotExcludes = @('.git', '.venv', '.env', 'crm.db', '.pytest_cache', '.tmp', 'plain', '.claude', '.agents', '.opencode', '.plainwright')

$Workspace = $null
# Remove this run's workspace (if created) and exit - the counterpart of the
# Bash `trap ... EXIT`.
function Exit-Run($code) {
    if ($Workspace -and (Test-Path -LiteralPath $Workspace)) {
        Set-Location -LiteralPath ([System.IO.Path]::GetTempPath())
        Remove-Item -LiteralPath $Workspace -Recurse -Force -ErrorAction SilentlyContinue
    }
    exit $code
}

# Step 1 - argument validation
if ($args.Count -ne 1) {
    Write-Err "Usage: $($MyInvocation.MyCommand.Name) <source_build_folder>"
    Write-Err "       HOST_CODEBASE_ROOT (env) overrides the host codebase root"
    Write-Err "       (defaults to the parent of the plain/ folder)."
    exit 1
}

$SourceFolder = $args[0]

if (-not (Test-Path -LiteralPath $SourceFolder -PathType Container)) {
    Write-Err "Error: source build folder not found: $SourceFolder"
    exit 2
}

# Step 2 - resolve the host codebase root (the embedded integration's host)
$PlainDir = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if ($env:HOST_CODEBASE_ROOT) {
    $HostRoot = $env:HOST_CODEBASE_ROOT
} else {
    $HostRoot = (Resolve-Path -LiteralPath (Join-Path $PlainDir '..')).Path
}

if (-not (Test-Path -LiteralPath $HostRoot -PathType Container)) {
    Write-Err "Error: host codebase root not found: $HostRoot"
    exit 2
}
Write-Host "Host codebase root: $HostRoot"

# Step 3 - dependency environment. Use the host project's OWN virtual
# environment at $HostRoot\.venv, which is expected to already be provisioned
# (e.g. by scripts\start.ps1). This script never installs anything - it only
# verifies the environment and fails fast with exit 69 if it is not ready. A
# valid venv requires both Scripts\python.exe and the pyvenv.cfg marker.
$VenvDir = Join-Path $HostRoot '.venv'
$VenvPy = Join-Path (Join-Path $VenvDir 'Scripts') 'python.exe'

if (-not (Test-Path -LiteralPath $VenvPy -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $VenvDir 'pyvenv.cfg') -PathType Leaf)) {
    Write-Err "Error: host virtual environment not found or invalid at $VenvDir."
    Write-Err "       Provision it first, e.g. .\scripts\start.ps1 (or"
    Write-Err "       py -3 -m venv .venv; .venv\Scripts\pip install -r requirements.txt)."
    exit 69
}

# Inner quotes should be single: PowerShell 5.1 drops double quotes when passing
# arguments to a program, so this check would silently report "unknown".
$VenvPyVersion = (& $VenvPy -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null)
if (-not $VenvPyVersion) { $VenvPyVersion = "unknown" }
Write-Host "Using host venv $VenvDir (Python $VenvPyVersion)"

# Verify pytest is available in the venv. Do NOT install anything - a missing
# dependency is a provisioning error the user must resolve (re-run
# scripts\start.ps1), reported as exit 69. Missing host runtime packages are left
# to surface as import errors from the tests themselves.
& $VenvPy -m pytest --version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Err "Error: pytest is not installed in host venv $VenvDir."
    Write-Err "       Install the project's test dependencies into .venv and retry."
    exit 69
}

# Step 4 - create this run's isolated workspace (unique per run, so concurrent
# renders never share it) and snapshot the host codebase into it.
$Workspace = Join-Path ([System.IO.Path]::GetTempPath()) ("python_unittests." + [guid]::NewGuid().ToString('N').Substring(0, 12))
try {
    New-Item -ItemType Directory -Path $Workspace -ErrorAction Stop | Out-Null
} catch {
    Write-Err "Error: could not create workspace $Workspace"
    $Workspace = $null
    exit 69
}
Write-Host "Workspace: $Workspace"

Write-Host "Snapshotting host codebase into workspace"
foreach ($entry in (Get-ChildItem -LiteralPath $HostRoot -Force)) {
    if ($SnapshotExcludes -contains $entry.Name) { continue }
    try {
        Copy-Item -LiteralPath $entry.FullName -Destination $Workspace -Recurse -Force -ErrorAction Stop
    } catch {
        Write-Err "Error: failed to copy $($entry.FullName) into workspace $Workspace"
        Exit-Run 69
    }
}

# Step 5 - overlay the generated integration package(s) onto the snapshot.
# The build only ships integration package dirs (src/integrations/<name>/ and
# tests/integrations/<name>/), so destructive ops are scoped to those leaf dirs
# of the workspace only.
$TestTargets = @()
$StagedAny = $false

foreach ($sub in @('src', 'tests')) {
    $pkgRoot = Join-Path (Join-Path $SourceFolder $sub) 'integrations'
    if (-not (Test-Path -LiteralPath $pkgRoot -PathType Container)) { continue }
    foreach ($pkg in (Get-ChildItem -LiteralPath $pkgRoot -Directory)) {
        $name = $pkg.Name
        $rel = "$sub/integrations/$name"
        $dest = Join-Path (Join-Path (Join-Path $Workspace $sub) 'integrations') $name

        Write-Host "Staging $rel into workspace"
        if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force -ErrorAction SilentlyContinue }
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        Copy-Item -Path (Join-Path $pkg.FullName '*') -Destination $dest -Recurse -Force
        $StagedAny = $true

        if ($sub -eq 'tests') { $TestTargets += $rel }
    }
}

if (-not $StagedAny) {
    Write-Err "Error: build folder ships no src/integrations/<name>/ packages: $SourceFolder"
    Exit-Run 2
}

if ($TestTargets.Count -eq 0) {
    Write-Err "Error: build folder ships no tests/integrations/<name>/ packages to run."
    Exit-Run 1
}

# Step 6 - run pytest from the workspace root so `from src.integrations.<name> ...`
# resolves against the snapshot's host layout, scoped to the staged package(s).
try {
    Set-Location -LiteralPath $Workspace -ErrorAction Stop
} catch {
    Write-Err "Error: could not enter workspace $Workspace"
    Exit-Run 69
}

# --basetemp keeps pytest's tmp_path dirs inside the workspace rather than the
# per-user directory pytest otherwise shares (and prunes) across runs.
Write-Host "Running pytest in $Workspace for: $($TestTargets -join ' ')"
$env:PYTHONPATH = $Workspace
& $VenvPy `
    -m pytest `
    -vv `
    -rA `
    -l `
    -s `
    --tb=long `
    --durations=0 `
    --color=yes `
    -o log_cli=true `
    --log-cli-level=DEBUG `
    --import-mode=importlib `
    "--basetemp=$(Join-Path $Workspace '.pytest_tmp')" `
    @TestTargets
Exit-Run $LASTEXITCODE

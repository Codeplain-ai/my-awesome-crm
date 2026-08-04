#!/usr/bin/env pwsh
<#
Unit-test runner for an EMBEDDED CRM integration plug-in (PowerShell port).

The integration's generated code is consumed in-process by the host CRM
backend, so unit tests must run against the host's source layout - not a
detached copy. This script overlays the renderer's build folder ($args[0]) onto
the host codebase at the module's package path (src/integrations/<name>/
and tests/integrations/<name>/), then runs pytest from the host root scoped
to the staged integration package(s).

Tests run inside the host project's OWN virtual environment at
$HOST_CODEBASE_ROOT\.venv (the one scripts\start.ps1 provisions), so unit
tests use the exact interpreter and installed dependencies the host uses.
The script does not create a throwaway venv: the project's floor is Python
>= 3.12 and any interpreter at or above it is fine, but the tests must run on
the SAME one as the host. Selecting an interpreter off PATH here broke that -
PATH may offer a newer Python than the host venv was built with.

  Usage: run_unittests_python.ps1 <source_build_folder>

The host codebase root defaults to the parent of the plain/ folder and can
be overridden with the HOST_CODEBASE_ROOT environment variable.

This is the Windows counterpart of run_unittests_python.sh and does exactly the
same thing: same staging model, same host-venv requirement, same pytest flags,
same exit codes (69 = host venv missing/invalid or missing dependencies,
 1 = bad usage / no tests to run, 2 = missing input or host root,
 otherwise pytest's own exit code).
#>

function Write-Err($msg) { [Console]::Error.WriteLine($msg) }

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

# Step 3 - overlay the generated integration package(s) into the host source tree.
# The build only ships integration package dirs (src/integrations/<name>/ and
# tests/integrations/<name>/), so destructive ops are scoped to those leaf dirs
# only - never the host's top-level src/ or tests/.
$TestTargets = @()
$StagedAny = $false

foreach ($sub in @('src', 'tests')) {
    $pkgRoot = Join-Path (Join-Path $SourceFolder $sub) 'integrations'
    if (-not (Test-Path -LiteralPath $pkgRoot -PathType Container)) { continue }
    foreach ($pkg in (Get-ChildItem -LiteralPath $pkgRoot -Directory)) {
        $name = $pkg.Name
        $rel = "$sub/integrations/$name"
        $dest = Join-Path (Join-Path (Join-Path $HostRoot $sub) 'integrations') $name

        Write-Host "Staging $rel into host"
        if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force -ErrorAction SilentlyContinue }
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        Copy-Item -Path (Join-Path $pkg.FullName '*') -Destination $dest -Recurse -Force
        $StagedAny = $true

        if ($sub -eq 'tests') { $TestTargets += $rel }
    }
}

if (-not $StagedAny) {
    Write-Err "Error: build folder ships no src/integrations/<name>/ packages: $SourceFolder"
    exit 2
}

if ($TestTargets.Count -eq 0) {
    Write-Err "Error: build folder ships no tests/integrations/<name>/ packages to run."
    exit 1
}

# Step 4 - dependency environment. Use the host project's OWN virtual
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

$VenvPyVersion = (& $VenvPy -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>$null)
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

# Step 5 - run pytest from the host root so `from src.integrations.<name> ...`
# resolves against the host layout, scoped to the staged integration package(s).
try {
    Set-Location -LiteralPath $HostRoot -ErrorAction Stop
} catch {
    Write-Err "Error: could not enter host codebase root $HostRoot"
    exit 2
}

Write-Host "Running pytest in $HostRoot for: $($TestTargets -join ' ')"
$env:PYTHONPATH = $HostRoot
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
    @TestTargets
exit $LASTEXITCODE

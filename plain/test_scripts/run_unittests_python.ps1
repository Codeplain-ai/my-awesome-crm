#!/usr/bin/env pwsh
<#
Unit-test runner for an EMBEDDED CRM integration plug-in (PowerShell port).

The integration's generated code is consumed in-process by the host CRM
backend, so unit tests must run against the host's source layout - not a
detached copy. This script overlays the renderer's build folder ($args[0]) onto
the host codebase at the module's package path (src/integrations/<name>/
and tests/integrations/<name>/), then runs pytest from the host root scoped
to the staged integration package(s).

  Usage: run_unittests_python.ps1 <source_build_folder>

The host codebase root defaults to the parent of the plain/ folder and can
be overridden with the HOST_CODEBASE_ROOT environment variable.

This is the Windows counterpart of run_unittests_python.sh and does exactly the
same thing: same staging model, same pytest flags, same exit codes
(69 = no usable Python / venv-pip failure / missing host manifest,
 1 = bad usage / no tests to run, 2 = missing input or host root,
 otherwise pytest's own exit code).
#>

function Write-Err($msg) { [Console]::Error.WriteLine($msg) }

# Step 1 - toolchain check. Any Python >= 3.12 is accepted (version-agnostic).
# Each candidate is version-checked, not just probed for existence, so a launcher
# aliased to an older Python (e.g. python3 -> 3.9) is skipped rather than wrongly
# selected. Newer launchers are preferred over older ones.
$MinPyMajor = 3
$MinPyMinor = 12

function Test-PyMeetsMin($exe, $restArgs) {
    try {
        & $exe @restArgs -c "import sys; sys.exit(0 if sys.version_info[:2] >= ($MinPyMajor, $MinPyMinor) else 1)" 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

$candidates = @(
    @('py', '-3.15'), @('py', '-3.14'), @('py', '-3.13'), @('py', '-3.12'),
    @('python3.15'), @('python3.14'), @('python3.13'), @('python3.12'),
    @('python3'), @('python')
)

$PyExe = $null
$PyArgs = @()
foreach ($cand in $candidates) {
    $exe = $cand[0]
    if ($cand.Count -gt 1) { $rest = @($cand[1..($cand.Count - 1)]) } else { $rest = @() }
    if (Test-PyMeetsMin $exe $rest) {
        $PyExe = $exe
        $PyArgs = $rest
        break
    }
}
if (-not $PyExe) {
    Write-Err "Error: a Python >= $MinPyMajor.$MinPyMinor interpreter is required but none was found on PATH."
    exit 69
}

$PyVersion = (& $PyExe @PyArgs -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>$null)
if (-not $PyVersion) { $PyVersion = "unknown" }
$PyDisplay = ((@($PyExe) + $PyArgs) -join ' ')
Write-Host "Using $PyDisplay ($PyVersion)"

# Step 2 - argument validation
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

# Step 3 - resolve the host codebase root (the embedded integration's host)
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

# Step 4 - overlay the generated integration package(s) into the host source tree.
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

# Step 5 - dependency environment. Keep the host source tree clean by housing
# the venv under plain/.tmp/ rather than inside the host repo.
$VenvDir = Join-Path (Join-Path $PlainDir '.tmp') 'venv'
$VenvPy = Join-Path (Join-Path $VenvDir 'Scripts') 'python.exe'
$CreatedVenv = $false
if (-not (Test-Path -LiteralPath $VenvPy)) {
    Write-Host "Creating venv at $VenvDir"
    & $PyExe @PyArgs -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $CreatedVenv = $true
}

# Some hosts create a venv without pip (a stripped Python where ensurepip is
# missing, or an incomplete system python-venv package). pip must be present
# inside the venv; try to bootstrap it with ensurepip, and if it still is not
# available, fail fast with 69 rather than dying later with an opaque error.
& $VenvPy -m pip --version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Err "pip not found in venv; attempting to bootstrap it with ensurepip"
    & $VenvPy -m ensurepip --upgrade --default-pip 2>$null | Out-Null
}
& $VenvPy -m pip --version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Err "Error: pip is not available in the venv at $VenvDir and could not be bootstrapped."
    Write-Err "       Install the platform's Python venv/pip support (e.g. the python-venv package) and retry."
    exit 69
}
if ($CreatedVenv) {
    & $VenvPy -m pip install --upgrade pip | Out-Null
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$hostReq = Join-Path $HostRoot 'requirements.txt'
$hostPyproject = Join-Path $HostRoot 'pyproject.toml'
if (Test-Path -LiteralPath $hostReq) {
    & $VenvPy -m pip install -r $hostReq
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} elseif (Test-Path -LiteralPath $hostPyproject) {
    & $VenvPy -m pip install -e $HostRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Err "Error: no requirements.txt or pyproject.toml in $HostRoot"
    exit 69
}

# pytest is needed to run the suite even if the host does not declare it.
& $VenvPy -m pip install pytest | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Step 6 - run pytest from the host root so `from src.integrations.<name> ...`
# resolves against the host layout, scoped to the staged integration package(s).
try {
    Set-Location -LiteralPath $HostRoot -ErrorAction Stop
} catch {
    Write-Err "Error: could not enter host codebase root $HostRoot"
    exit 2
}

Write-Host "Running pytest in $HostRoot for: $($TestTargets -join ' ')"
$env:PYTHONPATH = $HostRoot
& $VenvPy -m pytest `
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

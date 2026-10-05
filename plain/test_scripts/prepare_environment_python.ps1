#!/usr/bin/env pwsh
<#
Prepare-environment script for an EMBEDDED CRM integration plug-in (PowerShell port).

The renderer calls this ONCE per render, before any conformance run. It
builds the one expensive thing every conformance run needs - a venv with the
host requirements.txt and pytest installed - so run_conformance_tests_python.ps1
(activate-only variant) attaches to it instead of creating and populating a
fresh venv on every one of its N invocations per render.

What this script deliberately does NOT do: stage the build folder ($1). The
generated implementation changes after every functional spec renders, while
this script runs only once, so a copy staged here would be stale. The
conformance runner keeps overlaying the CURRENT $1 onto its own per-run host
snapshot; only the venv is shared.

The prepared environment lives at

  <temp>\python_conformance_env_<module>_<hash>\.venv

where <module> is the name of $1's parent folder (plain_modules\<module>\code)
and <hash> is a short hash of $1's absolute path. $1's own leaf name is always
"code", so keying on it alone would make every module share - and clobber -
one folder; keying on the module lets several renders prepare side by side.
run_conformance_tests_python.ps1 derives the identical path. The folder is
intentionally LEFT IN PLACE on exit: it is this script's deliverable, and the
next prepare of the same module wipes and rebuilds it.

The venv is built from the HOST project's interpreter at
$HOST_CODEBASE_ROOT\.venv (provisioned by scripts\start.ps1), so the tests run
on the same Python the host uses - never one picked off PATH.

  Usage: prepare_environment_python.ps1 <build_folder>

Environment overrides:
  HOST_CODEBASE_ROOT  host repo root (default: parent of plain\)

Every failure exits 69: a half-prepared environment is unusable.

This is the Windows counterpart of prepare_environment_python.sh and does
exactly the same thing: same prepared-env path derivation, same installs, same
ready marker, same exit codes.
#>

$UNRECOVERABLE_ERROR_EXIT_CODE = 69

function Write-Err($msg) { [Console]::Error.WriteLine($msg) }
function Banner($msg) { Write-Host ""; Write-Host "===== $msg =====" }

function Fail($msg) {
    Write-Err "Error: $msg"
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}

# Run a native command, echoing it first; on failure print context and exit 69.
function Run($exe, [string[]]$cmdArgs) {
    Write-Host "+ $exe $($cmdArgs -join ' ')"
    & $exe @cmdArgs
    $rc = $LASTEXITCODE
    if ($rc -ne 0) {
        Write-Err "Error: command failed (exit $rc): $exe $($cmdArgs -join ' ')"
        Write-Err "       cwd=$((Get-Location).Path) PATH=$env:PATH"
        exit $UNRECOVERABLE_ERROR_EXIT_CODE
    }
}

$start_time = Get-Date

# ----- [1/5] Toolchain check ------------------------------------------------
Banner "[1/5] Toolchain check"
$PlainDir = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if ($env:HOST_CODEBASE_ROOT) {
    $HostRoot = $env:HOST_CODEBASE_ROOT
} else {
    $HostRoot = (Resolve-Path -LiteralPath (Join-Path $PlainDir '..')).Path
}
$HostVenvDir = Join-Path $HostRoot '.venv'
$PyExe = Join-Path (Join-Path $HostVenvDir 'Scripts') 'python.exe'

if (-not (Test-Path -LiteralPath $PyExe -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $HostVenvDir 'pyvenv.cfg') -PathType Leaf)) {
    Write-Err "Error: host virtual environment not found or invalid at $HostVenvDir."
    Write-Err "       Provision it first, e.g. .\scripts\start.ps1 (or"
    Write-Err "       py -3 -m venv .venv; .venv\Scripts\pip install -r requirements.txt)."
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}
Write-Host "Host codebase root: $HostRoot"
Write-Host "Python interpreter: $PyExe (host venv)"
& $PyExe --version

# ----- [2/5] Argument validation --------------------------------------------
Banner "[2/5] Argument validation"
if ($args.Count -lt 1 -or [string]::IsNullOrEmpty($args[0])) {
    Write-Err "Error: No build folder provided."
    Write-Err "Usage: $($MyInvocation.MyCommand.Name) <build_folder>"
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}
if (-not (Test-Path -LiteralPath $args[0] -PathType Container)) { Fail "build folder not found: $($args[0])" }
$AbsBuildFolder = (Resolve-Path -LiteralPath $args[0]).Path
Write-Host "Build folder: $AbsBuildFolder"

# ----- [3/5] Working folder setup -------------------------------------------
Banner "[3/5] Working folder setup"
# Keep this derivation identical to run_conformance_tests_python.ps1.
$ModuleName = Split-Path (Split-Path $AbsBuildFolder -Parent) -Leaf
$PathHash = (& $PyExe -c 'import hashlib, sys; print(hashlib.sha1(sys.argv[1].encode()).hexdigest()[:8])' $AbsBuildFolder)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrEmpty($PathHash)) { Fail "could not hash the build folder path" }
$PreparedEnv = Join-Path ([System.IO.Path]::GetTempPath()) "python_conformance_env_$($ModuleName)_$($PathHash.Trim())"
$VenvDir = Join-Path $PreparedEnv '.venv'
$VenvPy = Join-Path (Join-Path $VenvDir 'Scripts') 'python.exe'
$ReadyMarker = Join-Path $PreparedEnv '.prepared'

Write-Host "Module:           $ModuleName"
Write-Host "Prepared env:     $PreparedEnv"
if (Test-Path -LiteralPath $PreparedEnv) {
    Write-Host "+ Remove-Item -Recurse -Force $PreparedEnv"
    try { Remove-Item -LiteralPath $PreparedEnv -Recurse -Force -ErrorAction Stop }
    catch { Fail "could not remove $PreparedEnv" }
}
try { New-Item -ItemType Directory -Force -Path $PreparedEnv -ErrorAction Stop | Out-Null }
catch { Fail "could not create $PreparedEnv" }
try { Set-Location -LiteralPath $PreparedEnv -ErrorAction Stop }
catch { Fail "could not enter prepared env folder $PreparedEnv" }
Write-Host "Now in:           $((Get-Location).Path)"

# ----- [4/5] Create the venv ------------------------------------------------
Banner "[4/5] Create venv"
Run $PyExe @('-m', 'venv', $VenvDir)

# Some hosts create a venv without pip. Try to bootstrap it with ensurepip.
& $VenvPy -m pip --version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "pip not found in venv; attempting to bootstrap it with ensurepip"
    & $VenvPy -m ensurepip --upgrade --default-pip
}
& $VenvPy -m pip --version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Err "Error: pip is not available in the venv at $VenvDir and could not be bootstrapped."
    Write-Err "       Install the platform's Python venv/pip support (e.g. the python-venv package) and retry."
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}

# ----- [5/5] Install dependencies -------------------------------------------
Banner "[5/5] Install dependencies"
$install_start = Get-Date
Run $VenvPy @('-m', 'pip', 'install', '--upgrade', 'pip')
# Host runtime deps, read in place (read-only) from the real host tree, so the
# conformance runner's snapshot of the implementation imports cleanly.
$HostRequirements = Join-Path $HostRoot 'requirements.txt'
if (Test-Path -LiteralPath $HostRequirements -PathType Leaf) {
    Write-Host "Installing host requirements from $HostRequirements into $VenvDir"
    Run $VenvPy @('-m', 'pip', 'install', '-r', $HostRequirements)
} else {
    Write-Host "Warning: no host requirements.txt at $HostRequirements"
}
Run $VenvPy @('-m', 'pip', 'install', 'pytest')
$install_elapsed = [int]([math]::Round(((Get-Date) - $install_start).TotalSeconds))
Write-Host "Requirements setup completed in $install_elapsed seconds"

# Written last, so the conformance runner can tell a complete environment from
# one a failed prepare left half-built.
try { New-Item -ItemType File -Force -Path $ReadyMarker -ErrorAction Stop | Out-Null }
catch { Fail "could not write $ReadyMarker" }

$elapsed = [int]([math]::Round(((Get-Date) - $start_time).TotalSeconds))
$venvVersion = (& $VenvPy --version 2>&1 | Out-String).Trim()
Write-Host ""
Write-Host "Summary: lang=python prepared_env=$PreparedEnv venv=$VenvDir python=$venvVersion duration=${elapsed}s exit=0"
exit 0

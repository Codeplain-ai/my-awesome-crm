#!/usr/bin/env pwsh
<#
Conformance-test runner for an EMBEDDED CRM integration plug-in (PowerShell port).

Variant: install-inline (no prepare_environment_python.ps1 exists). This maps
the embedded Java conformance flow onto Python:

  Java                                   | Python (this script)
  ---------------------------------------|----------------------------------------
  mvn install from ROOT (host + impl)     | overlay $1 (generated impl) into the
    -> artifact in ~/.m2                  |   host ROOT src/integrations/<name>/,
                                          |   install ROOT requirements.txt
  cd .tmp/java_conformance && mvn install | stage $2 into .tmp/python_conformance,
    -> resolve conformance deps           |   install the conformance suite's deps
  mvn test (impl from ~/.m2)              | cd .tmp/python_conformance && pytest
                                          |   with PYTHONPATH=ROOT so the ROOT impl
                                          |   code is what gets imported

$1 (build folder) is overlaid into the host root per the embedded contract
(scoped to the module's own package dir). $2 (conformance tests) is copied
into .tmp and run from there, leaving the authored test tree pristine.

  Usage: run_conformance_tests_python.ps1 <build_folder> <conformance_tests_folder>

Credentials come from the environment. A .env file at the project root is
REQUIRED (the script exits 69 if it is absent) and is loaded into the
environment before the tests run; shell-exported variables take precedence
over .env. This script is integration-agnostic - it never inspects or
validates any specific secret by name. Each integration validates the
credentials it actually needs at call time (e.g. fetch_contacts() raises if a
required variable is missing), and the live run surfaces that failure.

Environment overrides:
  HOST_CODEBASE_ROOT  host repo root (default: parent of plain/)
  ENV_FILE            path to the required .env file (default: <host root>/.env)

This is the Windows counterpart of run_conformance_tests_python.sh and does
exactly the same thing: same staging model, same .env loading, same pytest
flags, and the same strict verdict (only a clean pytest exit with zero
failures/errors/skips passes; no collected tests exits 1).
#>

$UNRECOVERABLE_ERROR_EXIT_CODE = 69
$NO_TESTS_EXIT_CODE = 1

function Write-Err($msg) { [Console]::Error.WriteLine($msg) }
function Banner($msg) { Write-Host ""; Write-Host "===== $msg =====" }

# ----- [1/8] Toolchain check ------------------------------------------------
Banner "[1/8] Toolchain check"
# Any Python >= 3.12 is accepted (version-agnostic). Each candidate is
# version-checked, not just probed for existence, so a launcher aliased to an
# older Python (e.g. python3 -> 3.9) is skipped rather than wrongly selected.
# Newer launchers are preferred over older ones.
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
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}
$PyDisplay = ((@($PyExe) + $PyArgs) -join ' ')
$PyPath = (Get-Command $PyExe -ErrorAction SilentlyContinue).Source
Write-Host "Python interpreter: $PyDisplay ($PyPath)"
& $PyExe @PyArgs --version

# ----- [2/8] Argument validation --------------------------------------------
Banner "[2/8] Argument validation"
if ($args.Count -lt 1 -or [string]::IsNullOrEmpty($args[0])) {
    Write-Err "Error: No build folder provided."
    Write-Err "Usage: $($MyInvocation.MyCommand.Name) <build_folder> <conformance_tests_folder>"
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}
if ($args.Count -lt 2 -or [string]::IsNullOrEmpty($args[1])) {
    Write-Err "Error: No conformance tests folder provided."
    Write-Err "Usage: $($MyInvocation.MyCommand.Name) <build_folder> <conformance_tests_folder>"
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}

$BuildFolder = $args[0]
$TestsFolder = $args[1]

if (-not (Test-Path -LiteralPath $BuildFolder -PathType Container)) {
    Write-Err "Error: build folder not found: $BuildFolder"
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}
if (-not (Test-Path -LiteralPath $TestsFolder -PathType Container)) {
    Write-Err "Error: conformance tests folder not found: $TestsFolder"
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}

# ----- [3/8] Resolve paths --------------------------------------------------
Banner "[3/8] Resolve paths"
$current_dir = (Get-Location).Path
$PlainDir = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if ($env:HOST_CODEBASE_ROOT) {
    $HostRoot = $env:HOST_CODEBASE_ROOT
} else {
    $HostRoot = (Resolve-Path -LiteralPath (Join-Path $PlainDir '..')).Path
}
$AbsBuildFolder = (Resolve-Path -LiteralPath $BuildFolder).Path
$AbsTestsFolder = (Resolve-Path -LiteralPath $TestsFolder).Path

if (-not (Test-Path -LiteralPath $HostRoot -PathType Container)) {
    Write-Err "Error: host codebase root not found: $HostRoot"
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}
Write-Host "Invocation dir (current_dir):  $current_dir"
Write-Host "Build folder (impl source):    $AbsBuildFolder"
Write-Host "Conformance tests source:      $AbsTestsFolder"
Write-Host "Host codebase root:            $HostRoot"

# ----- [4/8] Overlay generated implementation into the host ROOT ------------
# Mirrors the Java "mvn install from root with all code" step: put the freshly
# generated implementation where the conformance suite will import it from
# (root's src/). Scoped to the module's own integration package dir(s) only -
# never the host's top-level src/ or tests/.
Banner "[4/8] Overlay implementation into host root"
$StagedAny = $false
foreach ($sub in @('src', 'tests')) {
    $pkgRoot = Join-Path (Join-Path $AbsBuildFolder $sub) 'integrations'
    if (-not (Test-Path -LiteralPath $pkgRoot -PathType Container)) { continue }
    foreach ($pkg in (Get-ChildItem -LiteralPath $pkgRoot -Directory)) {
        $name = $pkg.Name
        $rel = "$sub/integrations/$name"
        $dest = Join-Path (Join-Path (Join-Path $HostRoot $sub) 'integrations') $name
        Write-Host "Staging $rel into host root"
        if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force -ErrorAction SilentlyContinue }
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        Copy-Item -Path (Join-Path $pkg.FullName '*') -Destination $dest -Recurse -Force
        $StagedAny = $true
    }
}
if (-not $StagedAny) {
    Write-Err "Error: build folder ships no src/integrations/<name>/ packages: $AbsBuildFolder"
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}

# ----- [5/8] Provider credentials (live run) --------------------------------
# A .env at the project root is REQUIRED. This step only guarantees the file
# exists and loads it into the environment - it is integration-agnostic and
# never validates any specific secret by name. Each integration validates the
# credentials it needs at call time; the live run surfaces a missing one.
Banner "[5/8] Provider credentials"
if ($env:ENV_FILE) { $EnvFile = $env:ENV_FILE } else { $EnvFile = Join-Path $HostRoot '.env' }
if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    Write-Err "Error: credentials file not found: $EnvFile"
    Write-Err "       :ConformanceTests: run live and require a .env at the project root."
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}
Write-Host "Loading credentials from $EnvFile (shell-exported vars take precedence)"
# Shell-exported credentials are authoritative; .env only fills variables the
# shell did not already set. Parse KEY=VALUE lines, skipping comments / blanks.
foreach ($line in (Get-Content -LiteralPath $EnvFile)) {
    if ($line -eq '') { continue }
    if ($line.StartsWith('#')) { continue }
    $eq = $line.IndexOf('=')
    if ($eq -lt 0) { continue }                       # line had no '='
    $key = ($line.Substring(0, $eq) -replace '\s', '') # strip all whitespace from key
    if ([string]::IsNullOrEmpty($key)) { continue }
    $val = $line.Substring($eq + 1)
    # strip one layer of surrounding quotes
    if ($val.Length -ge 2 -and $val.StartsWith('"') -and $val.EndsWith('"')) {
        $val = $val.Substring(1, $val.Length - 2)
    } elseif ($val.Length -ge 2 -and $val.StartsWith("'") -and $val.EndsWith("'")) {
        $val = $val.Substring(1, $val.Length - 2)
    }
    if ([string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable($key, 'Process'))) {
        Set-Item -Path ("Env:" + $key) -Value $val
    }
}

# ----- [6/8] Stage conformance tests into .tmp ------------------------------
Banner "[6/8] Stage conformance tests into working folder"
$WorkingFolder = Join-Path (Join-Path $PlainDir '.tmp') 'python_conformance'
Write-Host "Working folder: $WorkingFolder"
# Remove the folder itself in one shot so no stale files from a previous
# conformance run (e.g. a nested .venv) are picked up by pytest alongside the
# current run's freshly-copied tests.
if (Test-Path -LiteralPath $WorkingFolder) { Remove-Item -LiteralPath $WorkingFolder -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Force -Path $WorkingFolder | Out-Null
Copy-Item -Path (Join-Path $AbsTestsFolder '*') -Destination $WorkingFolder -Recurse -Force

# ----- [7/8] Install dependencies (isolated venv inside working folder) -----
Banner "[7/8] Install dependencies"
$start_time = Get-Date
$VenvDir = Join-Path $WorkingFolder '.venv'
& $PyExe @PyArgs -m venv $VenvDir
if ($LASTEXITCODE -ne 0) {
    Write-Err "Error: failed to create virtual environment at $VenvDir"
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}
$VenvPy = Join-Path (Join-Path $VenvDir 'Scripts') 'python.exe'

# Some hosts create a venv without pip. pip must be present inside the venv;
# try to bootstrap it with ensurepip, and if it still is not available, fail
# fast with 69 rather than dying later with an opaque error.
& $VenvPy -m pip --version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Err "pip not found in venv; attempting to bootstrap it with ensurepip"
    & $VenvPy -m ensurepip --upgrade --default-pip 2>$null | Out-Null
}
& $VenvPy -m pip --version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Err "Error: pip is not available in the venv at $VenvDir and could not be bootstrapped."
    Write-Err "       Install the platform's Python venv/pip support (e.g. the python-venv package) and retry."
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}

& $VenvPy -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Host runtime deps ("from src") so the root implementation imports cleanly.
$hostReq = Join-Path $HostRoot 'requirements.txt'
if (Test-Path -LiteralPath $hostReq) {
    Write-Host "Installing host requirements from $hostReq"
    & $VenvPy -m pip install -r $hostReq
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
# Conformance suite's own deps ("from conformance"), if it ships any.
$workReq = Join-Path $WorkingFolder 'requirements.txt'
if (Test-Path -LiteralPath $workReq) {
    Write-Host "Installing conformance-suite requirements"
    & $VenvPy -m pip install -r $workReq
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& $VenvPy -m pip install pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$end_time = Get-Date
$elapsed = [int]([math]::Round(($end_time - $start_time).TotalSeconds))
Write-Host "Requirements setup completed in $elapsed seconds"

# ----- [8/8] Run conformance tests LIVE from .tmp, impl from ROOT -----------
Banner "[8/8] Run conformance tests (live provider)"
try {
    Set-Location -LiteralPath $WorkingFolder -ErrorAction Stop
} catch {
    Write-Err "Error: could not enter working folder $WorkingFolder"
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}
# PYTHONPATH=ROOT => `from src.integrations.<name> import ...` resolves to the
# implementation code in the host root, not anything under .tmp.
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$HostRoot" + [IO.Path]::PathSeparator + $env:PYTHONPATH
} else {
    $env:PYTHONPATH = $HostRoot
}

$TestArgs = @(
    '-m', 'pytest',
    '-vv',
    '-rA',
    '-l',
    '-s',
    '--tb=long',
    '--durations=0',
    '--color=yes',
    '-o', 'log_cli=true',
    '--log-cli-level=DEBUG',
    '--import-mode=importlib',
    '-p', 'no:cacheprovider',
    "--basetemp=$(Join-Path $WorkingFolder '.pytest_tmp')",
    $WorkingFolder
)

Write-Host "Now in:       $((Get-Location).Path)"
Write-Host "PYTHONPATH:   $env:PYTHONPATH"
Write-Host "Test command: $VenvPy $($TestArgs -join ' ')`n"

$output = & $VenvPy @TestArgs 2>&1 | Out-String
$exit_code = $LASTEXITCODE
Write-Host $output

# The verbose flags above (-s, -rA, log_cli=DEBUG) let test output and live log
# lines land in $output - any of which could contain strings like "3 failed" or
# "no tests ran". So DO NOT grep the whole stream for the verdict. Instead pull
# out pytest's final summary bar (the "===== N passed/failed ... in Xs ====="
# line, always last), strip ANSI color, and judge only that line.
$esc = [char]27
$clean = $output -replace ("$esc\[[0-9;]*m"), ''
$summary_line = ($clean -split "`r?`n" | Where-Object { $_ -match '^=+.*=+$' } | Select-Object -Last 1)
if ($null -eq $summary_line) { $summary_line = '' }

# pytest exit 5 == no tests collected. Strict no-tests guard.
if ($exit_code -eq 5 -or ($summary_line -match 'no tests ran')) {
    Write-Err ""
    Write-Err "Error: No conformance tests discovered in $WorkingFolder."
    Write-Err "Failure context: cwd=$((Get-Location).Path) current_dir=$current_dir tests=$AbsTestsFolder"
    exit $NO_TESTS_EXIT_CODE
}

# Strict pass criteria: clean exit AND zero failures / errors / skipped.
if ($exit_code -ne 0 -or ($summary_line -match '[0-9]+ (failed|error|skipped|xfailed|xpassed)')) {
    Write-Err ""
    Write-Err "Error: conformance run did not pass cleanly (exit $exit_code)."
    Write-Err "All conformance tests must pass with zero failures, errors, and skips."
    Write-Err "Failure context: cwd=$((Get-Location).Path) current_dir=$current_dir tests=$AbsTestsFolder PYTHONPATH=$env:PYTHONPATH"
    if ($exit_code -eq 0) { $exit_code = 1 }
    exit $exit_code
}

Write-Host ""
Write-Host "Conformance run passed."
Write-Host "Summary: variant=install-inline cmd='$VenvPy $($TestArgs -join ' ')' exit=$exit_code current_dir=$current_dir working_folder=$WorkingFolder"
exit $exit_code

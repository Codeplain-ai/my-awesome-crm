#!/usr/bin/env pwsh
<#
Conformance-test runner for an EMBEDDED CRM integration plug-in (PowerShell port).

Variant: activate-only. prepare_environment_python.ps1 runs once per render and
builds the venv (host requirements.txt + pytest); this script attaches to it
and exits 69 if it is missing. This maps the embedded Java conformance flow
onto Python:

  Java                                   | Python
  ---------------------------------------|----------------------------------------
  mvn install from ROOT (host + impl)     | prepare: venv + host requirements.txt
    -> artifact in ~/.m2                  | this script: snapshot the host into
                                          |   the workspace, overlay $1 (generated
                                          |   impl) onto its src/integrations/<name>/
  cd .tmp/java_conformance && mvn install | stage $2 into the workspace, install
    -> resolve conformance deps           |   the suite's own deps (if any) into
                                          |   the prepared venv
  mvn test (impl from ~/.m2)              | cd <workspace>/conformance && pytest
                                          |   with PYTHONPATH=<workspace>/host so
                                          |   the snapshot's impl is imported

Every run works in its OWN isolated workspace in the system temp directory
(unique per run), so several renders can run conformance side by side without
clobbering each other or the real host tree:

  <workspace>/host/         host codebase snapshot + $1 overlaid onto it
  <workspace>/conformance/  copy of $2 (the authored test tree stays pristine)

The real host tree is never written to, and the workspace is removed on exit.
The prepared venv (<temp>\python_conformance_env_<module>_<hash>\.venv, see
prepare_environment_python.ps1) is shared by the module's runs and never
deleted here; prepare owns its lifecycle. $1 is still overlaid on every run
because the generated implementation changes after each functional spec.

  Usage: run_conformance_tests_python.ps1 <build_folder> <conformance_tests_folder>

Credentials come from the environment. A .env file at the project root is
REQUIRED (the script exits 69 if it is absent) and is loaded into the
environment before the tests run; shell-exported variables take precedence
over .env. This script is integration-agnostic - it never inspects or
validates any specific secret by name. Each integration validates the
credentials it actually needs at call time (e.g. fetch(get_stored) raises if a
required variable is missing), and the live run surfaces that failure.

Environment overrides:
  HOST_CODEBASE_ROOT  host repo root (default: parent of plain/)
  ENV_FILE            path to the required .env file (default: <host root>/.env)

Top-level host entries NOT copied into the workspace snapshot: VCS metadata,
the venv, secrets (loaded from the real host .env in [6/9] instead), local
data, caches, agent tooling, and the ***plain project itself.

This is the Windows counterpart of run_conformance_tests_python.sh and does
exactly the same thing: same staging model, same .env loading, same pytest
flags, and the same strict verdict (only a clean pytest exit with zero
failures/errors/skips passes; no collected tests exits 1).
#>

$UNRECOVERABLE_ERROR_EXIT_CODE = 69
$NO_TESTS_EXIT_CODE = 1
$SnapshotExcludes = @('.git', '.venv', '.env', 'crm.db', '.pytest_cache', '.tmp', 'plain', '.claude', '.agents', '.opencode', '.plainwright')

function Write-Err($msg) { [Console]::Error.WriteLine($msg) }
function Banner($msg) { Write-Host ""; Write-Host "===== $msg =====" }

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

# ----- [1/9] Toolchain check ------------------------------------------------
Banner "[1/9] Toolchain check"
# The conformance suite runs in its own isolated venv (it installs its own test
# dependencies, which must not pollute the host environment), but that venv is
# built (by prepare_environment_python.ps1) from the HOST project's interpreter at $HOST_CODEBASE_ROOT\.venv - the
# one scripts\start.ps1 provisioned. The project's floor is Python >= 3.12 and
# any interpreter at or above it is fine; what is NOT fine is the tests running
# on a DIFFERENT interpreter than the host. Selecting one off PATH here did
# exactly that (PATH may offer a newer Python than the host venv was built
# with), so a test dependency could break on an interpreter the host never uses.
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
Write-Host "Python interpreter: $PyExe (host venv)"
& $PyExe --version

# ----- [2/9] Argument validation --------------------------------------------
Banner "[2/9] Argument validation"
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

# ----- [3/9] Resolve paths --------------------------------------------------
Banner "[3/9] Resolve paths"
# $PlainDir / $HostRoot were already resolved (and validated) in [1/9], because
# the host venv there is derived from them.
$current_dir = (Get-Location).Path
$AbsBuildFolder = (Resolve-Path -LiteralPath $BuildFolder).Path
$AbsTestsFolder = (Resolve-Path -LiteralPath $TestsFolder).Path

Write-Host "Invocation dir (current_dir):  $current_dir"
Write-Host "Build folder (impl source):    $AbsBuildFolder"
Write-Host "Conformance tests source:      $AbsTestsFolder"
Write-Host "Host codebase root:            $HostRoot"

# The prepared environment - keep this derivation identical to
# prepare_environment_python.ps1.
$ModuleName = Split-Path (Split-Path $AbsBuildFolder -Parent) -Leaf
$PathHash = (& $PyExe -c 'import hashlib, sys; print(hashlib.sha1(sys.argv[1].encode()).hexdigest()[:8])' $AbsBuildFolder)
$PreparedEnv = Join-Path ([System.IO.Path]::GetTempPath()) "python_conformance_env_$($ModuleName)_$("$PathHash".Trim())"
$VenvDir = Join-Path $PreparedEnv '.venv'
$VenvPy = Join-Path (Join-Path $VenvDir 'Scripts') 'python.exe'
Write-Host "Prepared env:                  $PreparedEnv"

if (-not (Test-Path -LiteralPath $VenvPy -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $VenvDir 'pyvenv.cfg') -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $PreparedEnv '.prepared') -PathType Leaf)) {
    Write-Err "Error: prepared environment missing or incomplete at $PreparedEnv."
    Write-Err "       Run prepare_environment_python.ps1 $AbsBuildFolder first."
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}

# ----- [4/9] Create the isolated workspace and snapshot the host -----------
Banner "[4/9] Create workspace and snapshot host"
# The workspace lives in the system temp directory (an absolute path), not
# inside the project, so no build debris is left in the repo. A GUID suffix
# makes the name unique per run; $2's leaf name only labels it (never
# concatenate the raw argument).
$Workspace = Join-Path ([System.IO.Path]::GetTempPath()) ("python_conformance_$(Split-Path $AbsTestsFolder -Leaf)." + [guid]::NewGuid().ToString('N').Substring(0, 12))
try {
    New-Item -ItemType Directory -Path $Workspace -ErrorAction Stop | Out-Null
} catch {
    Write-Err "Error: could not create workspace $Workspace"
    $Workspace = $null
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}
$HostSnapshot = Join-Path $Workspace 'host'
$WorkingFolder = Join-Path $Workspace 'conformance'
New-Item -ItemType Directory -Force -Path $HostSnapshot | Out-Null
New-Item -ItemType Directory -Force -Path $WorkingFolder | Out-Null
Write-Host "Workspace:     $Workspace"
Write-Host "Host snapshot: $HostSnapshot"

foreach ($entry in (Get-ChildItem -LiteralPath $HostRoot -Force)) {
    if ($SnapshotExcludes -contains $entry.Name) { continue }
    try {
        Copy-Item -LiteralPath $entry.FullName -Destination $HostSnapshot -Recurse -Force -ErrorAction Stop
    } catch {
        Write-Err "Error: failed to copy $($entry.FullName) into host snapshot $HostSnapshot"
        Exit-Run $UNRECOVERABLE_ERROR_EXIT_CODE
    }
}

# ----- [5/9] Overlay generated implementation onto the host snapshot --------
# Mirrors the Java "mvn install from root with all code" step: put the freshly
# generated implementation where the conformance suite will import it from
# (the snapshot's src/). Scoped to the module's own integration package dir(s)
# of the snapshot only.
Banner "[5/9] Overlay implementation onto host snapshot"
$StagedAny = $false
foreach ($sub in @('src', 'tests')) {
    $pkgRoot = Join-Path (Join-Path $AbsBuildFolder $sub) 'integrations'
    if (-not (Test-Path -LiteralPath $pkgRoot -PathType Container)) { continue }
    foreach ($pkg in (Get-ChildItem -LiteralPath $pkgRoot -Directory)) {
        $name = $pkg.Name
        $rel = "$sub/integrations/$name"
        $dest = Join-Path (Join-Path (Join-Path $HostSnapshot $sub) 'integrations') $name
        Write-Host "Staging $rel into host snapshot"
        if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force -ErrorAction SilentlyContinue }
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        Copy-Item -Path (Join-Path $pkg.FullName '*') -Destination $dest -Recurse -Force
        $StagedAny = $true
    }
}
if (-not $StagedAny) {
    Write-Err "Error: build folder ships no src/integrations/<name>/ packages: $AbsBuildFolder"
    Exit-Run $UNRECOVERABLE_ERROR_EXIT_CODE
}

# ----- [6/9] Provider credentials (live run) --------------------------------
# A .env at the project root is REQUIRED. This step only guarantees the file
# exists and loads it into the environment - it is integration-agnostic and
# never validates any specific secret by name. Each integration validates the
# credentials it needs at call time; the live run surfaces a missing one.
Banner "[6/9] Provider credentials"
if ($env:ENV_FILE) { $EnvFile = $env:ENV_FILE } else { $EnvFile = Join-Path $HostRoot '.env' }
if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    Write-Err "Error: credentials file not found: $EnvFile"
    Write-Err "       :ConformanceTests: run live and require a .env at the project root."
    Exit-Run $UNRECOVERABLE_ERROR_EXIT_CODE
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

# ----- [7/9] Stage conformance tests into the workspace ---------------------
Banner "[7/9] Stage conformance tests into working folder"
# The working folder is freshly created inside this run's workspace, so no
# stale files from a previous run can be collected alongside this run's tests.
Write-Host "Working folder: $WorkingFolder"
Copy-Item -Path (Join-Path $AbsTestsFolder '*') -Destination $WorkingFolder -Recurse -Force

# ----- [8/9] Attach to the prepared venv ------------------------------------
Banner "[8/9] Attach to prepared venv"
# Host requirements and pytest were installed by prepare_environment_python.ps1.
# Only the suite's own deps vary per functional spec; they go into the prepared
# venv, where pip skips anything already satisfied.
$start_time = Get-Date
Write-Host "Using prepared venv $VenvDir"
$workReq = Join-Path $WorkingFolder 'requirements.txt'
if (Test-Path -LiteralPath $workReq) {
    Write-Host "Installing conformance-suite requirements"
    & $VenvPy -m pip install -r $workReq
    if ($LASTEXITCODE -ne 0) { Exit-Run $LASTEXITCODE }
}

$end_time = Get-Date
$elapsed = [int]([math]::Round(($end_time - $start_time).TotalSeconds))
Write-Host "Requirements setup completed in $elapsed seconds"

# ----- [9/9] Run conformance tests LIVE, impl from the host snapshot --------
Banner "[9/9] Run conformance tests (live provider)"
try {
    Set-Location -LiteralPath $WorkingFolder -ErrorAction Stop
} catch {
    Write-Err "Error: could not enter working folder $WorkingFolder"
    Exit-Run $UNRECOVERABLE_ERROR_EXIT_CODE
}
# PYTHONPATH=snapshot => `from src.integrations.<name> import ...` resolves to
# the implementation code in this run's host snapshot, never the real host tree.
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$HostSnapshot" + [IO.Path]::PathSeparator + $env:PYTHONPATH
} else {
    $env:PYTHONPATH = $HostSnapshot
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
    "--basetemp=$(Join-Path $Workspace '.pytest_tmp')",
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
    Exit-Run $NO_TESTS_EXIT_CODE
}

# Strict pass criteria: clean exit AND zero failures / errors / skipped.
if ($exit_code -ne 0 -or ($summary_line -match '[0-9]+ (failed|error|skipped|xfailed|xpassed)')) {
    Write-Err ""
    Write-Err "Error: conformance run did not pass cleanly (exit $exit_code)."
    Write-Err "All conformance tests must pass with zero failures, errors, and skips."
    Write-Err "Failure context: cwd=$((Get-Location).Path) current_dir=$current_dir tests=$AbsTestsFolder PYTHONPATH=$env:PYTHONPATH"
    if ($exit_code -eq 0) { $exit_code = 1 }
    Exit-Run $exit_code
}

Write-Host ""
Write-Host "Conformance run passed."
Write-Host "Summary: variant=activate-only cmd='$VenvPy $($TestArgs -join ' ')' exit=$exit_code current_dir=$current_dir working_folder=$WorkingFolder"
Exit-Run $exit_code

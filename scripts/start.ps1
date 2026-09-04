<#
.SYNOPSIS
    One-shot getting-started + run script for My Awesome CRM (Windows / PowerShell).

.DESCRIPTION
    Idempotent: on first run it bootstraps everything (Python 3.12-3.14, virtualenv,
    dependencies) and starts the server; on subsequent runs it detects that the
    environment is already set up and just starts the server.

.EXAMPLE
    .\scripts\start.ps1

.NOTES
    Keep this file pure ASCII. Windows PowerShell 5.1 misreads non-ASCII, so an
    em dash or smart quote silently breaks that string and every one after it.

    Honors the same env vars the app does (all optional):
      CRM_PORT     (default 8000)   - port to serve on
      CRM_DB_PATH  (default crm.db) - where the SQLite file lives
#>

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Resolve paths so the script works no matter where it is invoked from.
# ---------------------------------------------------------------------------
$ScriptDir    = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot  = (Resolve-Path (Join-Path $ScriptDir '..')).Path
$VenvDir      = Join-Path $ProjectRoot '.venv'
$Requirements = Join-Path $ProjectRoot 'requirements.txt'
# Any stable Python release from 3.12 up. The ceiling excludes pre-releases
# (3.15 is a RC and our dependencies don't support it). 
# The minimum is what auto-install targets.
$PythonVersion    = '3.12'
$MaxPythonVersion = '3.14'
$MinPythonMajor   = 3
$MinPythonMinor   = 12
$MaxPythonMinor   = 14

# ---------------------------------------------------------------------------
# Small logging helpers.
# ---------------------------------------------------------------------------
function Write-Info  { param($Msg) Write-Host "==> $Msg"  -ForegroundColor Blue }
function Write-Ok    { param($Msg) Write-Host "  + $Msg"   -ForegroundColor Green }
function Write-Warn  { param($Msg) Write-Host "  ! $Msg"   -ForegroundColor Yellow }
function Write-Err   { param($Msg) Write-Host "ERROR: $Msg" -ForegroundColor Red }

# Lets a program call fail without stopping this script. 5.1 raises redirected
# stderr as an error, 7 will have non-zero exit if $PSNativeCommandUseErrorActionPreference is set.
function Invoke-Native {
    param([scriptblock]$Command)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Command } finally { $ErrorActionPreference = $prev }
}

# ---------------------------------------------------------------------------
# 1. Ensure a supported Python (3.12 - 3.14) is available.
# ---------------------------------------------------------------------------
function Find-Python312 {
    # First candidate inside the supported window wins. Names lie
    # (python3 may be 3.9), so every candidate is version-checked. Never
    # reference a `py -3.X` tag, the Install Manager silently installs it.
    $probe = "import sys; sys.exit(0 if ($MinPythonMajor, $MinPythonMinor) <= sys.version_info[:2] <= ($MinPythonMajor, $MaxPythonMinor) else 1)"

    $candidates = [System.Collections.Generic.List[string]]::new()

    # Runtimes registered with the py launcher, how this script reaches an
    # install that is not on PATH. Both generations answer `py -0p`
    # (`py list` is Install Manager only) and end each line with the path.
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($line in (Invoke-Native { py -0p 2>&1 })) {
            if ("$line" -match '((?:[A-Za-z]:\\|\\\\)[^*]*\.exe)\s*$' -and (Test-Path $matches[1])) {
                $candidates.Add($matches[1])
            }
        }
    }
    # Then any python on PATH. WindowsApps alias stubs are skipped because
    # invoking one installs Python.
    $aliasDir = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps'
    foreach ($exe in @('python3.14', 'python3.13', 'python3.12', 'python3', 'python')) {
        $cmd = Get-Command $exe -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -notlike "$aliasDir*") { $candidates.Add($cmd.Source) }
    }

    foreach ($exe in ($candidates | Select-Object -Unique)) {
        Invoke-Native { & $exe -c $probe 2>&1 } | Out-Null
        if ($LASTEXITCODE -eq 0) { return $exe }
    }
    return $null
}

function Install-Python312 {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Info "Installing Python $PythonVersion via winget..."
        winget install --id "Python.Python.$PythonVersion" --exact --silent `
            --accept-package-agreements --accept-source-agreements
    }
    elseif (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Info "Installing Python $PythonVersion via Chocolatey..."
        choco install python --version=3.12.0 -y
    }
    else {
        Write-Err "Neither winget nor Chocolatey is available to auto-install Python $PythonVersion."
        Write-Err "Install Python $PythonVersion from https://www.python.org/downloads/ and re-run this script."
        exit 1
    }
    # Refresh PATH for the current session so the fresh install is discoverable.
    $env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [System.Environment]::GetEnvironmentVariable('Path', 'User')
}

Write-Info "Checking for Python $PythonVersion - $MaxPythonVersion..."
$PythonCmd = Find-Python312
if ($PythonCmd) {
    Write-Ok ("Found: " + (Invoke-Native { & $PythonCmd --version 2>&1 }))
}
else {
    Write-Warn "No supported Python ($PythonVersion - $MaxPythonVersion) was found."
    $reply = Read-Host "Install Python $PythonVersion now? [y/N]"
    if ($reply -match '^(y|yes)$') {
        Install-Python312
        $PythonCmd = Find-Python312
        if ($PythonCmd) {
            Write-Ok ("Installed: " + (Invoke-Native { & $PythonCmd --version 2>&1 }))
        }
        else {
            Write-Err "A supported Python ($PythonVersion - $MaxPythonVersion) is still not found after install. You may need to open a new terminal, or install it manually."
            exit 1
        }
    }
    else {
        Write-Err "Python $PythonVersion - $MaxPythonVersion is required to run this project. Aborting."
        exit 1
    }
}

# ---------------------------------------------------------------------------
# 2. Ensure the virtualenv exists.
# ---------------------------------------------------------------------------
# A directory is not proof of a usable venv. An interpreter with a broken or
# absent ensurepip builds the tree, aborts at the pip step, and leaves a
# pip-less .venv behind - after which a bare existence check reports "already
# exists" and the install step dies with "No module named pip". Validate the
# way the test scripts do: Scripts\python.exe plus the pyvenv.cfg marker.
# Use the venv's Python directly (no need to dot-source Activate.ps1).
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
function Test-VenvValid {
    (Test-Path -LiteralPath $VenvPython -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $VenvDir 'pyvenv.cfg') -PathType Leaf)
}

Write-Info "Checking for virtualenv at .venv..."
if ((Test-Path $VenvDir) -and -not (Test-VenvValid)) {
    Write-Warn "Found an incomplete virtualenv at $VenvDir - recreating it."
    Remove-Item -Recurse -Force $VenvDir
}
if (-not (Test-Path $VenvDir)) {
    Write-Warn "No virtualenv found - creating one."
    & $PythonCmd -m venv $VenvDir
    # Remove the partial tree on failure so the next run recreates it instead of
    # inheriting a broken one.
    if ($LASTEXITCODE -ne 0 -or -not (Test-VenvValid)) {
        if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
        Write-Err "Failed to create a virtualenv with the selected Python."
        Write-Err "Reinstall Python with the standard library complete and re-run."
        exit 1
    }
    Write-Ok "Created virtualenv at $VenvDir"
}
else {
    Write-Ok "Virtualenv already exists."
}

if (-not (Test-VenvValid)) {
    Write-Err "Expected virtualenv Python at $VenvPython but it was not found."
    exit 1
}

# pip can be absent from an otherwise well-formed venv (see above). ensurepip
# bootstraps it; if that fails the standard library itself is incomplete.
& $VenvPython -m pip --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Warn "pip is missing from the virtualenv - bootstrapping it with ensurepip."
    & $VenvPython -m ensurepip --upgrade *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Could not bootstrap pip: this interpreter has no working ensurepip."
        Write-Err "Reinstall Python with the standard library complete, then delete"
        Write-Err "$VenvDir and re-run this script."
        exit 1
    }
    Write-Ok "pip bootstrapped into the virtualenv."
}

# ---------------------------------------------------------------------------
# 3. Ensure requirements are installed.
#    A stamp file records the hash of requirements.txt so we only reinstall
#    when the dependency list actually changed.
# ---------------------------------------------------------------------------
$StampFile = Join-Path $VenvDir '.requirements.installed'
$ReqHash = (Get-FileHash -Algorithm SHA256 $Requirements).Hash

Write-Info "Checking Python dependencies..."
$installed = (Test-Path $StampFile) -and ((Get-Content $StampFile -ErrorAction SilentlyContinue) -eq $ReqHash)
if (-not $installed) {
    Write-Warn "Dependencies missing or out of date - installing."
    # A native non-zero exit is not a PowerShell error, so pip needs an explicit
    # check or $StampFile records a failed install as a successful one.
    & $VenvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        Write-Err "pip self-upgrade failed (exit $LASTEXITCODE)."
        exit 1
    }
    & $VenvPython -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) {
        Write-Err "pip install -r $Requirements failed (exit $LASTEXITCODE). Dependencies were NOT installed."
        exit 1
    }
    Set-Content -Path $StampFile -Value $ReqHash
    Write-Ok "Dependencies installed."
}
else {
    Write-Ok "Dependencies already up to date."
}

# ---------------------------------------------------------------------------
# 4. Run the server.
#    Launch uvicorn as a child process and wait on it, tearing it down in a
#    finally block so the server (and uvicorn's --reload child worker) is
#    stopped when the script stops - including on Ctrl+C or window close.
# ---------------------------------------------------------------------------
$Port = if ($env:CRM_PORT) { $env:CRM_PORT } else { '8000' }
Write-Info "Starting My Awesome CRM on http://localhost:$Port ..."
Write-Info "  Web UI:  http://localhost:$Port/"
Write-Info "  Swagger: http://localhost:$Port/docs"
Write-Info "  (press Ctrl+C to stop)"

$server = Start-Process -FilePath $VenvPython `
    -ArgumentList @('-m', 'uvicorn', 'src.main:app', '--reload', '--host', '0.0.0.0', '--port', $Port) `
    -WorkingDirectory $ProjectRoot -NoNewWindow -PassThru
try {
    Wait-Process -Id $server.Id
}
finally {
    if (-not $server.HasExited) {
        Write-Info "Shutting down server..."
        # Kill the uvicorn process and its --reload child worker. Wrapped in
        # Invoke-Native because taskkill errors when the process already exited.
        Invoke-Native { taskkill /PID $server.Id /T /F 2>&1 } | Out-Null
    }
}

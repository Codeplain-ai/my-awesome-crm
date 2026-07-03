<#
.SYNOPSIS
    One-shot getting-started + run script for My Awesome CRM (Windows / PowerShell).

.DESCRIPTION
    Idempotent: on first run it bootstraps everything (Python 3.12, virtualenv,
    dependencies) and starts the server; on subsequent runs it detects that the
    environment is already set up and just starts the server.

.EXAMPLE
    .\scripts\start.ps1

.NOTES
    Honors the same env vars the app does (all optional):
      CRM_PORT     (default 8000)   — port to serve on
      CRM_DB_PATH  (default crm.db) — where the SQLite file lives
#>

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Resolve paths so the script works no matter where it is invoked from.
# ---------------------------------------------------------------------------
$ScriptDir    = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot  = (Resolve-Path (Join-Path $ScriptDir '..')).Path
$VenvDir      = Join-Path $ProjectRoot '.venv'
$Requirements = Join-Path $ProjectRoot 'requirements.txt'
$PythonVersion = '3.12'

Set-Location $ProjectRoot

# ---------------------------------------------------------------------------
# Small logging helpers.
# ---------------------------------------------------------------------------
function Write-Info  { param($Msg) Write-Host "==> $Msg"  -ForegroundColor Blue }
function Write-Ok    { param($Msg) Write-Host "  + $Msg"   -ForegroundColor Green }
function Write-Warn  { param($Msg) Write-Host "  ! $Msg"   -ForegroundColor Yellow }
function Write-Err   { param($Msg) Write-Host "ERROR: $Msg" -ForegroundColor Red }

# ---------------------------------------------------------------------------
# 1. Ensure Python 3.12 is available.
# ---------------------------------------------------------------------------
function Find-Python312 {
    # Prefer the Windows launcher (py -3.12), then any python on PATH that is 3.12.
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py "-$PythonVersion" -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return @('py', "-$PythonVersion")
        }
    }
    foreach ($exe in @('python', 'python3', "python$PythonVersion")) {
        if (Get-Command $exe -ErrorAction SilentlyContinue) {
            $isMatch = & $exe -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                return @($exe)
            }
        }
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

Write-Info "Checking for Python $PythonVersion..."
$PythonCmd = Find-Python312
if ($PythonCmd) {
    Write-Ok ("Found: " + (& $PythonCmd[0] $PythonCmd[1..($PythonCmd.Length-1)] --version 2>&1))
}
else {
    Write-Warn "Python $PythonVersion is not installed."
    $reply = Read-Host "Install Python $PythonVersion now? [y/N]"
    if ($reply -match '^(y|yes)$') {
        Install-Python312
        $PythonCmd = Find-Python312
        if ($PythonCmd) {
            Write-Ok ("Installed: " + (& $PythonCmd[0] $PythonCmd[1..($PythonCmd.Length-1)] --version 2>&1))
        }
        else {
            Write-Err "Python $PythonVersion still not found after install. You may need to open a new terminal, or install it manually."
            exit 1
        }
    }
    else {
        Write-Err "Python $PythonVersion is required to run this project. Aborting."
        exit 1
    }
}

# ---------------------------------------------------------------------------
# 2. Ensure the virtualenv exists.
# ---------------------------------------------------------------------------
Write-Info "Checking for virtualenv at .venv..."
if (-not (Test-Path $VenvDir)) {
    Write-Warn "No virtualenv found — creating one."
    & $PythonCmd[0] $PythonCmd[1..($PythonCmd.Length-1)] -m venv $VenvDir
    Write-Ok "Created virtualenv at $VenvDir"
}
else {
    Write-Ok "Virtualenv already exists."
}

# Use the venv's Python directly (no need to dot-source Activate.ps1).
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
if (-not (Test-Path $VenvPython)) {
    Write-Err "Expected virtualenv Python at $VenvPython but it was not found."
    exit 1
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
    Write-Warn "Dependencies missing or out of date — installing."
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r $Requirements
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
#    stopped when the script stops — including on Ctrl+C or window close.
# ---------------------------------------------------------------------------
$Port = if ($env:CRM_PORT) { $env:CRM_PORT } else { '8000' }
Write-Info "Starting My Awesome CRM on http://localhost:$Port ..."
Write-Info "  Web UI:  http://localhost:$Port/"
Write-Info "  Swagger: http://localhost:$Port/docs"
Write-Info "  (press Ctrl+C to stop)"

$server = Start-Process -FilePath $VenvPython `
    -ArgumentList @('-m', 'uvicorn', 'src.main:app', '--reload', '--host', '0.0.0.0', '--port', $Port) `
    -NoNewWindow -PassThru
try {
    Wait-Process -Id $server.Id
}
finally {
    if (-not $server.HasExited) {
        Write-Info "Shutting down server..."
        # Kill the uvicorn process and its --reload child worker.
        taskkill /PID $server.Id /T /F 2>$null | Out-Null
    }
}

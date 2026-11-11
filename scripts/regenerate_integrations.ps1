#!/usr/bin/env pwsh
<#
Regenerate the code of four integrations - hubspot, dynamics, pipedrive and
attio - side by side, then deploy and run.

  1. Starts from a clean slate: removes each module's build folder
     plain/plain_modules/<module>/ and its log plain/codeplain.<module>.log, so
     every render starts from scratch. The plain/<module>.plain specs are
     never touched.
  2. Opens one PowerShell window per module, titled "render: <module>", running
     `codeplain <module>.plain --config-name config.pwsh.yaml` from plain/.
     Each render writes its own log (plain/codeplain.<module>.log) so the
     concurrent runs do not overwrite each other's codeplain.log. Render
     windows left over from an earlier run are killed first.
  3. This window then waits until all renders have finished, and runs
     scripts/deploy_integrations.ps1. A module whose render failed is left out
     (its code/ may be partial or stale); the others are deployed. codeplain
     exits 0 even when a render fails, so success is read from the render's
     own log: it must carry codeplain's success banner.
  4. This window then runs scripts/start.ps1 (the server).

Because deploy_integrations.ps1 empties src/integrations/ first, only the
modules that rendered successfully in this run are present afterwards.

  Usage: .\scripts\regenerate_integrations.ps1

Requires codeplain on PATH, and CODEPLAIN_API_KEY in this shell or in your
PowerShell profile (the render windows inherit the environment and load the
profile).

This is the Windows counterpart of regenerate_integrations.sh. It does the same
thing, except that separate console windows replace the tmux session.
#>

function Write-Err($msg) { [Console]::Error.WriteLine($msg) }

$Modules = @('hubspot', 'dynamics', 'pipedrive', 'attio')

$ScriptDir = $PSScriptRoot
$Root = (Resolve-Path -LiteralPath (Join-Path $ScriptDir '..')).Path
$PlainDir = Join-Path $Root 'plain'
$TempDir = [IO.Path]::GetTempPath()
# PIDs of the render windows of the last run, so a re-run can replace them.
$PidFile = Join-Path $TempDir 'regenerate_integrations.pids'

if ($args.Count -ne 0) {
    Write-Err "Usage: .\scripts\regenerate_integrations.ps1   (takes no arguments; regenerates: $($Modules -join ' '))"
    exit 1
}

if (-not (Get-Command codeplain -ErrorAction SilentlyContinue)) {
    Write-Err "Error: codeplain is not on PATH."
    exit 69
}

foreach ($module in $Modules) {
    $spec = Join-Path $PlainDir "$module.plain"
    if (-not (Test-Path -LiteralPath $spec -PathType Leaf)) {
        Write-Err "Error: $spec not found."
        exit 2
    }
}

# Render windows left over from an earlier run are replaced, not reused: kill
# each window with its process tree (stopping any codeplain still running in
# it) and drop the stale status dirs.
if (Test-Path -LiteralPath $PidFile) {
    foreach ($line in (Get-Content -LiteralPath $PidFile)) {
        $oldPid = 0
        if (-not [int]::TryParse($line, [ref]$oldPid)) { continue }
        if (Get-Process -Id $oldPid -ErrorAction SilentlyContinue) {
            Write-Host "Killing previous render window (PID $oldPid)"
            & taskkill.exe /T /F /PID $oldPid | Out-Null
        }
    }
    Remove-Item -LiteralPath $PidFile -Force
}
Get-ChildItem -LiteralPath $TempDir -Directory -Filter 'regenerate_integrations.*' -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Step 1 - clean slate: each module's build folder and log are removed so it
# renders from scratch.
foreach ($module in $Modules) {
    foreach ($path in @((Join-Path (Join-Path $PlainDir 'plain_modules') $module),
                        (Join-Path $PlainDir "codeplain.$module.log"))) {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        Write-Host "Removing $path"
        Remove-Item -LiteralPath $path -Recurse -Force
    }
}
Write-Host "Regenerating $($Modules.Count) integrations: $($Modules -join ' ')"

# Each render window drops a marker file here when its codeplain run finishes.
$StatusDir = Join-Path $TempDir ('regenerate_integrations.' + [Guid]::NewGuid().ToString('N').Substring(0, 6))
New-Item -ItemType Directory -Force -Path $StatusDir | Out-Null

# Step 2 - one render window per module. The command is passed encoded so
# paths with spaces or quotes survive the hop to the new process. -NoExit keeps
# the window open after codeplain quits, so its last output stays readable.
$Pids = @()
foreach ($module in $Modules) {
    $marker = (Join-Path $StatusDir $module).Replace("'", "''")
    $command = @"
`$Host.UI.RawUI.WindowTitle = 'render: $module'
codeplain $module.plain --config-name config.pwsh.yaml --log-file-name codeplain.$module.log
New-Item -ItemType File -Force -Path '$marker' | Out-Null
"@
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
    $proc = Start-Process -FilePath 'powershell.exe' -WorkingDirectory $PlainDir -PassThru `
        -ArgumentList @('-NoExit', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', $encoded)
    $Pids += $proc.Id
}
Set-Content -LiteralPath $PidFile -Value $Pids

# Steps 3 + 4 - wait, deploy, start the server.
function Test-LogMatch($module, $pattern) {
    $log = Join-Path $PlainDir "codeplain.$module.log"
    if (-not (Test-Path -LiteralPath $log)) { return $false }
    return [bool](Select-String -LiteralPath $log -Pattern $pattern -Quiet)
}
function Test-Succeeded($module) {
    Test-LogMatch $module "Render of module $module completed successfully|rendering succeeded|rendering complete"
}
function Test-Failed($module) {
    Test-LogMatch $module "Render of module $module failed|rendering failed"
}

# codeplain's TUI stays open after a render ends, so the process exiting (the
# window's marker file) cannot be the signal. A render counts as finished once
# its log carries the success or failure banner; the marker still covers a
# codeplain that crashed or quit before writing either.
Write-Host "Waiting for $($Modules.Count) renders to finish..."
while ($true) {
    $doneCount = 0
    foreach ($module in $Modules) {
        if ((Test-Succeeded $module) -or (Test-Failed $module) -or
            (Test-Path -LiteralPath (Join-Path $StatusDir $module))) {
            $doneCount++
        }
    }
    if ($doneCount -eq $Modules.Count) { break }
    Write-Host -NoNewline ("`r{0}/{1} renders finished" -f $doneCount, $Modules.Count)
    Start-Sleep -Seconds 5
}
Write-Host ("`rAll {0} renders finished.        " -f $Modules.Count)

$Deploy = @()
foreach ($module in $Modules) {
    if (Test-Succeeded $module) {
        $Deploy += $module
    } else {
        Write-Host "Render of $module FAILED (no success banner in $(Join-Path $PlainDir "codeplain.$module.log")) - not deploying it."
    }
}
Remove-Item -LiteralPath $StatusDir -Recurse -Force -ErrorAction SilentlyContinue

if ($Deploy.Count -eq 0) {
    Write-Err "Error: nothing to deploy."
    exit 1
}

# deploy_integrations.ps1 ends without an explicit exit on success, so clear
# any exit code left over from an earlier native command (e.g. taskkill).
$global:LASTEXITCODE = 0
& (Join-Path $ScriptDir 'deploy_integrations.ps1') @Deploy
if ($LASTEXITCODE -ne 0) {
    Write-Err "Error: deploy failed - not starting the server."
    exit 1
}
& (Join-Path $ScriptDir 'start.ps1')
exit $LASTEXITCODE

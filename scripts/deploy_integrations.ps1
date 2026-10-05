#!/usr/bin/env pwsh
<#
Deploy rendered integrations into the host codebase.

The test runners in plain/test_scripts/ work in isolated temp workspaces so
several renders can run at once - which means a render no longer leaves its
code in the host tree. Run this script by hand once the renders are done: it
copies each module's rendered build (plain/plain_modules/<module>/code/) into
the host, ALWAYS under the module's own name:

  code/src/integrations/<pkg>/    -> src/integrations/<module>/
  code/tests/integrations/<pkg>/  -> tests/integrations/<module>/

For most modules <pkg> == <module>. When they differ (e.g. hubspot1.plain
renders a package named hubspot), deploying under the module name lets both
coexist: the host discovers src/integrations/hubspot1/ as its own
integration. The implementation uses relative imports, so it works under any
folder name; the deployed unit tests import it by absolute path, so their
`src.integrations.<pkg>` references are rewritten to
`src.integrations.<module>` in the deployed copy (plain_modules/ is never
modified).

Everything in src/integrations/ is removed first, so the deployed set is
exactly the modules deployed by this run - an integration that is no longer
rendered does not linger. Each tests/integrations/<module>/ dir is replaced
wholesale. Nothing else is touched.

Note: passing a subset of modules still empties src/integrations/ first, so
only that subset is deployed afterwards.

  Usage: .\scripts\deploy_integrations.ps1 [<module> ...]
         (no modules = every module under plain/plain_modules/)

This is the Windows counterpart of deploy_integrations.sh and does exactly the
same thing.
#>

function Write-Err($msg) { [Console]::Error.WriteLine($msg) }

$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$ModulesDir = Join-Path (Join-Path $Root 'plain') 'plain_modules'

if (-not (Test-Path -LiteralPath $ModulesDir -PathType Container)) {
    Write-Err "Error: no rendered modules found at $ModulesDir"
    exit 2
}

if ($args.Count -gt 0) {
    $Modules = @($args)
} else {
    $Modules = @(Get-ChildItem -LiteralPath $ModulesDir -Directory | ForEach-Object { $_.Name })
}

# Returns the package dirs under code/<sub>/integrations/ (empty if none).
function Get-Packages($code, $sub) {
    $pkgRoot = Join-Path (Join-Path $code $sub) 'integrations'
    if (-not (Test-Path -LiteralPath $pkgRoot -PathType Container)) { return @() }
    return @(Get-ChildItem -LiteralPath $pkgRoot -Directory)
}

# Pass 1 - validate every module before copying anything, so a failed run never
# leaves the host half-deployed. Each module must ship exactly one
# src/integrations/<pkg>/ package, and at most one tests/integrations/<pkg>/.
foreach ($module in $Modules) {
    $code = Join-Path (Join-Path $ModulesDir $module) 'code'
    if (-not (Test-Path -LiteralPath $code -PathType Container)) {
        Write-Err "Error: module '$module' has no rendered code at $code"
        exit 2
    }
    $srcCount = (Get-Packages $code 'src').Count
    if ($srcCount -ne 1) {
        Write-Err "Error: module '$module' must ship exactly one src/integrations/<name>/ package (found $srcCount)"
        exit 2
    }
    $testsCount = (Get-Packages $code 'tests').Count
    if ($testsCount -gt 1) {
        Write-Err "Error: module '$module' ships $testsCount tests/integrations/<name>/ packages (expected at most 1)"
        exit 2
    }
}

# Pass 2 - empty src/integrations/ (the directory itself is kept), then copy
# each rendered package into place.
Write-Host "Removing everything in src/integrations/"
$SrcIntegrations = Join-Path (Join-Path $Root 'src') 'integrations'
New-Item -ItemType Directory -Force -Path $SrcIntegrations | Out-Null
Get-ChildItem -LiteralPath $SrcIntegrations -Force | Remove-Item -Recurse -Force
$Deployed = 0
foreach ($module in $Modules) {
    $code = Join-Path (Join-Path $ModulesDir $module) 'code'
    foreach ($sub in @('src', 'tests')) {
        foreach ($pkg in (Get-Packages $code $sub)) {
            $pkgName = $pkg.Name
            $dest = Join-Path (Join-Path (Join-Path $Root $sub) 'integrations') $module
            if ($pkgName -eq $module) {
                Write-Host "Deploying $sub/integrations/$module"
            } else {
                Write-Host "Deploying $sub/integrations/$module (rendered as package '$pkgName')"
            }
            if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }
            New-Item -ItemType Directory -Force -Path $dest | Out-Null
            try {
                Copy-Item -Path (Join-Path $pkg.FullName '*') -Destination $dest -Recurse -Force -ErrorAction Stop
            } catch {
                Write-Err "Error: failed to copy $sub/integrations/$pkgName from module '$module'"
                exit 1
            }
            Get-ChildItem -LiteralPath $dest -Recurse -Directory -Filter '__pycache__' |
                Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
            if ($pkgName -ne $module) {
                # Point absolute imports / patch targets at the renamed package.
                $pattern = '\bsrc\.integrations\.' + [regex]::Escape($pkgName) + '\b'
                foreach ($file in (Get-ChildItem -LiteralPath $dest -Recurse -File -Filter '*.py')) {
                    $text = [IO.File]::ReadAllText($file.FullName)
                    $new = [regex]::Replace($text, $pattern, "src.integrations.$module")
                    if ($new -ne $text) { [IO.File]::WriteAllText($file.FullName, $new) }
                }
            }
        }
    }
    $Deployed++
}

Write-Host "Deployed $Deployed module(s)."

#!/bin/bash
# Deploy rendered integrations into the host codebase.
#
# The test runners in plain/test_scripts/ work in isolated temp workspaces so
# several renders can run at once - which means a render no longer leaves its
# code in the host tree. Run this script by hand once the renders are done: it
# copies each module's rendered build (plain/plain_modules/<module>/code/) into
# the host, ALWAYS under the module's own name:
#
#   code/src/integrations/<pkg>/    -> src/integrations/<module>/
#   code/tests/integrations/<pkg>/  -> tests/integrations/<module>/
#
# For most modules <pkg> == <module>. When they differ (e.g. hubspot1.plain
# renders a package named hubspot), deploying under the module name lets both
# coexist: the host discovers src/integrations/hubspot1/ as its own
# integration. The implementation uses relative imports, so it works under any
# folder name; the deployed unit tests import it by absolute path, so their
# `src.integrations.<pkg>` references are rewritten to
# `src.integrations.<module>` in the deployed copy (plain_modules/ is never
# modified).
#
# Everything in src/integrations/ is removed first, so the deployed set is
# exactly the modules deployed by this run - an integration that is no longer
# rendered does not linger. Each tests/integrations/<module>/ dir is replaced
# wholesale. Nothing else is touched.
#
# Note: passing a subset of modules still empties src/integrations/ first, so
# only that subset is deployed afterwards.
#
#   Usage: ./scripts/deploy_integrations.sh [<module> ...]
#          (no modules = every module under plain/plain_modules/)
#
# This is the macOS / Linux counterpart of deploy_integrations.ps1 and does
# exactly the same thing.

set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODULES_DIR="$ROOT/plain/plain_modules"

if [ ! -d "$MODULES_DIR" ]; then
    echo "Error: no rendered modules found at $MODULES_DIR" >&2
    exit 2
fi

if [ $# -gt 0 ]; then
    MODULES=("$@")
else
    MODULES=()
    for dir in "$MODULES_DIR"/*/; do
        [ -d "$dir" ] && MODULES+=("$(basename "$dir")")
    done
fi

# Pass 1 - validate every module before copying anything, so a failed run never
# leaves the host half-deployed. Each module must ship exactly one
# src/integrations/<pkg>/ package, and at most one tests/integrations/<pkg>/.
for module in "${MODULES[@]}"; do
    code="$MODULES_DIR/$module/code"
    if [ ! -d "$code" ]; then
        echo "Error: module '$module' has no rendered code at $code" >&2
        exit 2
    fi
    for sub in src tests; do
        count=0
        for pkg in "$code/$sub/integrations"/*/; do
            [ -d "$pkg" ] && count=$((count + 1))
        done
        if [ "$sub" = "src" ] && [ "$count" -ne 1 ]; then
            echo "Error: module '$module' must ship exactly one src/integrations/<name>/ package (found $count)" >&2
            exit 2
        fi
        if [ "$sub" = "tests" ] && [ "$count" -gt 1 ]; then
            echo "Error: module '$module' ships $count tests/integrations/<name>/ packages (expected at most 1)" >&2
            exit 2
        fi
    done
done

# Pass 2 - empty src/integrations/ (the directory itself is kept), then copy
# each rendered package into place.
echo "Removing everything in src/integrations/"
mkdir -p "$ROOT/src/integrations"
find "$ROOT/src/integrations" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
DEPLOYED=0
for module in "${MODULES[@]}"; do
    code="$MODULES_DIR/$module/code"
    for sub in src tests; do
        for pkg in "$code/$sub/integrations"/*/; do
            [ -d "$pkg" ] || continue
            pkg_name="$(basename "$pkg")"
            dest="$ROOT/$sub/integrations/$module"
            if [ "$pkg_name" = "$module" ]; then
                echo "Deploying $sub/integrations/$module"
            else
                echo "Deploying $sub/integrations/$module (rendered as package '$pkg_name')"
            fi
            rm -rf "$dest"
            mkdir -p "$dest"
            cp -R "$pkg". "$dest"/ || {
                echo "Error: failed to copy $sub/integrations/$pkg_name from module '$module'" >&2
                exit 1
            }
            find "$dest" -type d -name __pycache__ -prune -exec rm -rf {} +
            if [ "$pkg_name" != "$module" ]; then
                # Point absolute imports / patch targets at the renamed package.
                find "$dest" -type f -name '*.py' -exec \
                    perl -pi -e "s/\\bsrc\\.integrations\\.\\Q$pkg_name\\E\\b/src.integrations.$module/g" {} +
            fi
        done
    done
    DEPLOYED=$((DEPLOYED + 1))
done

echo "Deployed $DEPLOYED module(s)."

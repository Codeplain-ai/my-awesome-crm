#!/bin/bash
# Deploy ONE rendered integration into the host codebase.
#
# Like deploy_integrations.sh, but for a single module, and it leaves every
# other integration in place. It copies the module's rendered build
# (plain/plain_modules/<module>/code/) into the host under the module's own name:
#
#   code/src/integrations/<pkg>/    -> src/integrations/<module>/
#   code/tests/integrations/<pkg>/  -> tests/integrations/<module>/
#
# Only those two destination dirs are replaced wholesale; nothing else is
# touched. When <pkg> differs from <module> (e.g. hubspot1.plain renders a
# package named hubspot), `src.integrations.<pkg>` references in the deployed
# copy are rewritten to `src.integrations.<module>` (plain_modules/ is never
# modified).
#
#   Usage: ./scripts/deploy_integration.sh <module>   (e.g. hubspot or hubspot.plain)

set -u

if [ $# -ne 1 ] || [ -z "$1" ]; then
    echo "Usage: $0 <module>   (e.g. hubspot or hubspot.plain)" >&2
    exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODULE="$(basename "$1" .plain)"
CODE="$ROOT/plain/plain_modules/$MODULE/code"

if [ ! -d "$CODE" ]; then
    echo "Error: module '$MODULE' has no rendered code at $CODE" >&2
    exit 2
fi

# Validate before copying anything: exactly one src/integrations/<pkg>/ package,
# and at most one tests/integrations/<pkg>/.
for sub in src tests; do
    count=0
    for pkg in "$CODE/$sub/integrations"/*/; do
        [ -d "$pkg" ] && count=$((count + 1))
    done
    if [ "$sub" = "src" ] && [ "$count" -ne 1 ]; then
        echo "Error: module '$MODULE' must ship exactly one src/integrations/<name>/ package (found $count)" >&2
        exit 2
    fi
    if [ "$sub" = "tests" ] && [ "$count" -gt 1 ]; then
        echo "Error: module '$MODULE' ships $count tests/integrations/<name>/ packages (expected at most 1)" >&2
        exit 2
    fi
done

for sub in src tests; do
    for pkg in "$CODE/$sub/integrations"/*/; do
        [ -d "$pkg" ] || continue
        pkg_name="$(basename "$pkg")"
        dest="$ROOT/$sub/integrations/$MODULE"
        if [ "$pkg_name" = "$MODULE" ]; then
            echo "Deploying $sub/integrations/$MODULE"
        else
            echo "Deploying $sub/integrations/$MODULE (rendered as package '$pkg_name')"
        fi
        rm -rf "$dest"
        mkdir -p "$dest"
        cp -R "$pkg". "$dest"/ || {
            echo "Error: failed to copy $sub/integrations/$pkg_name from module '$MODULE'" >&2
            exit 1
        }
        find "$dest" -type d -name __pycache__ -prune -exec rm -rf {} +
        if [ "$pkg_name" != "$MODULE" ]; then
            # Point absolute imports / patch targets at the renamed package.
            find "$dest" -type f -name '*.py' -exec \
                perl -pi -e "s/\\bsrc\\.integrations\\.\\Q$pkg_name\\E\\b/src.integrations.$MODULE/g" {} +
        fi
    done
done

echo "Deployed $MODULE."

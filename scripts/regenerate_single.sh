#!/bin/bash
# Render one integration, then deploy.
#
#   1. Runs `codeplain --exit-when-done <spec>` in plain/, logging to
#      plain/codeplain.<module>.log.
#   2. If the render succeeded, runs scripts/deploy_single.sh <module>,
#      which deploys only this module and leaves the other integrations alone.
#      codeplain exits 0 even when a render fails, so success is read from the
#      log's success banner.
#
#   Usage: ./scripts/regenerate_single.sh <spec.plain>   (e.g. hubspot.plain)
#
# <spec.plain> is a path relative to the current directory (e.g.
# ./plain/hubspot.plain) or, failing that, relative to plain/ (e.g. hubspot.plain).

set -u

if [ $# -ne 1 ] || [ -z "$1" ]; then
    echo "Usage: $0 <spec.plain>   (e.g. hubspot.plain)" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLAIN_DIR="$(cd "$SCRIPT_DIR/../plain" && pwd)" || exit 69

# Resolve the spec to an absolute path before leaving the caller's directory:
# first relative to the current directory, then relative to plain/.
if [ -f "$1" ]; then
    SPEC="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
elif [ -f "$PLAIN_DIR/$1" ]; then
    SPEC="$PLAIN_DIR/$1"
else
    echo "Error: spec '$1' not found (looked in $(pwd) and $PLAIN_DIR)." >&2
    exit 2
fi
MODULE="$(basename "$SPEC" .plain)"
LOG="codeplain.$MODULE.log"

if ! command -v codeplain >/dev/null 2>&1; then
    echo "Error: codeplain is not on PATH." >&2
    exit 69
fi

cd "$PLAIN_DIR" || exit 69

echo "Rendering $SPEC (log: plain/$LOG)"
codeplain --exit-when-done "$SPEC" --log-file-name "$LOG"

if ! grep -qE "Render of module $MODULE completed successfully|rendering succeeded|rendering complete" "$LOG" 2>/dev/null; then
    echo "Error: render of $MODULE failed (no success banner in plain/$LOG) - not deploying." >&2
    exit 1
fi

exec "$SCRIPT_DIR/deploy_single.sh" "$MODULE"

#!/usr/bin/env bash
# Repeatedly run `codeplain --force-render --exit-when-done <module>` in the plain/ folder.
#
# Usage: scripts/regenerate_loop.sh <module.plain>
#   <module.plain> is a path relative to the current directory (e.g.
#   ./plain/hubspot.plain) or, failing that, relative to plain/ (e.g. hubspot.plain).
# Env:
#   WAIT_SECS  seconds to wait between runs (default 2)
#   LOOP_RUNS  number of runs; 0 = loop forever (default 0)

set -u

if [ $# -lt 1 ] || [ -z "$1" ]; then
    echo "Usage: $0 <module.plain>" >&2
    exit 1
fi

WAIT_SECS="${WAIT_SECS:-2}"
LOOP_RUNS="${LOOP_RUNS:-0}"

PLAIN_DIR="$(cd "$(dirname "$0")/../plain" && pwd)" || exit 69

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

cd "$PLAIN_DIR" || exit 69

run=0
while [ "$LOOP_RUNS" -eq 0 ] || [ "$run" -lt "$LOOP_RUNS" ]; do
    run=$((run + 1))
    total=""; [ "$LOOP_RUNS" -ne 0 ] && total="/$LOOP_RUNS"
    echo "=== run $run$total:codeplain --force-render --exit-when-done $SPEC ==="
    codeplain --force-render --exit-when-done "$SPEC"
    echo "=== run $run exited with $? ==="

    if [ "$LOOP_RUNS" -ne 0 ] && [ "$run" -ge "$LOOP_RUNS" ]; then
        break
    fi
    sleep "$WAIT_SECS"
done

#!/usr/bin/env bash
# Repeatedly run `codeplain --force-render --exit-when-done <module>` in the plain/ folder.
#
# Usage: scripts/regenerate_single_loop.sh <module.plain>
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

cd "$(dirname "$0")/../plain" || exit 69

run=0
while [ "$LOOP_RUNS" -eq 0 ] || [ "$run" -lt "$LOOP_RUNS" ]; do
    run=$((run + 1))
    total=""; [ "$LOOP_RUNS" -ne 0 ] && total="/$LOOP_RUNS"
    echo "=== run $run$total:codeplain --force-render --exit-when-done $1 ==="
    codeplain --force-render --exit-when-done "$1"
    echo "=== run $run exited with $? ==="

    if [ "$LOOP_RUNS" -ne 0 ] && [ "$run" -ge "$LOOP_RUNS" ]; then
        break
    fi
    sleep "$WAIT_SECS"
done

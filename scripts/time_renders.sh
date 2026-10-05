#!/bin/bash
# Render <count> instances of one integration module concurrently in headless
# mode, time each one, and print the mean, standard deviation, min and max.
#
#   1. Starts from a clean slate, like regenerate_integrations.sh: removes the original
#      module's build folder plain/plain_modules/<module>/ and log, and every
#      copy left by an earlier run - plain/<module><N>.plain,
#      plain/plain_modules/<module><N>/, and its log - so every render starts
#      from scratch. Only plain/<module>.plain itself is kept. Then copies it
#      to plain/<module>1.plain ... <module><count-1>.plain, so there are
#      <count> modules in total.
#   2. Starts `codeplain <module><idx>.plain --headless` for every module at
#      once (from plain/), each writing its own log
#      (plain/codeplain.<module><idx>.log), and times each render wall-clock.
#   3. Once all renders have finished, prints each render's time and status,
#      then the mean, sample standard deviation, min and max over the renders
#      that succeeded. codeplain exits 0 even when a render fails, so success
#      is read from the render's own log: it must carry codeplain's success
#      banner. A failed render's time is listed but left out of the stats.
#
# Nothing is deployed. Ctrl-C stops every render still running.
#
#   Usage: ./scripts/time_renders.sh <module> [count]
#          e.g. ./scripts/time_renders.sh hubspot 4
#          <count> is the total number of renders, default 9.
#
# Requires codeplain on PATH and CODEPLAIN_API_KEY in the environment.
#
# macOS / Linux only, like regenerate_integrations.sh: there is no .ps1 counterpart.

set -u

DEFAULT_COUNT=9

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLAIN_DIR="$ROOT/plain"

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    echo "Usage: $0 <module> [count]   (e.g. $0 hubspot 4; count defaults to $DEFAULT_COUNT)" >&2
    exit 1
fi
COUNT="${2:-$DEFAULT_COUNT}"
case "$COUNT" in
    ''|*[!0-9]*|0*) echo "Error: count must be a positive integer, got '$COUNT'" >&2; exit 1 ;;
esac
MODULE="${1%.plain}"
case "$MODULE" in
    ''|*/*) echo "Error: <module> must be a module name in plain/, e.g. hubspot" >&2; exit 1 ;;
esac

if ! command -v codeplain >/dev/null 2>&1; then
    echo "Error: codeplain is not on PATH." >&2
    exit 69
fi

if [ ! -f "$PLAIN_DIR/$MODULE.plain" ]; then
    echo "Error: $PLAIN_DIR/$MODULE.plain not found." >&2
    exit 2
fi

# Step 1 - clean slate, then the copies (same rules as regenerate_integrations.sh).
is_copy() {
    case "$1" in
        "$MODULE"*) rest="${1#"$MODULE"}"; case "$rest" in ''|*[!0-9]*) return 1 ;; esac ;;
        *) return 1 ;;
    esac
}
for path in "$PLAIN_DIR"/"$MODULE"*.plain "$PLAIN_DIR"/plain_modules/"$MODULE"* "$PLAIN_DIR"/codeplain."$MODULE"*.log; do
    [ -e "$path" ] || continue
    [ "$path" = "$PLAIN_DIR/$MODULE.plain" ] && continue
    name="$(basename "$path")"
    name="${name#codeplain.}"; name="${name%.log}"; name="${name%.plain}"
    [ "$name" = "$MODULE" ] || is_copy "$name" || continue
    echo "Removing $path"
    rm -rf "$path"
done

MODULES=("$MODULE")
for ((idx = 1; idx < COUNT; idx++)); do
    cp "$PLAIN_DIR/$MODULE.plain" "$PLAIN_DIR/$MODULE$idx.plain"
    MODULES+=("$MODULE$idx")
done
echo "Prepared ${#MODULES[@]} modules: ${MODULES[*]}"

# Each render writes its duration in seconds here when it finishes.
TIMES_DIR="$(mktemp -d "${TMPDIR:-/tmp}/${MODULE}_timing.XXXXXX")"
PIDS=()
cleanup() {
    for pid in "${PIDS[@]:-}"; do
        # Background jobs ignore SIGINT in a script, so stop the codeplain
        # child explicitly, then its timing subshell.
        [ -n "$pid" ] || continue
        pkill -TERM -P "$pid" 2>/dev/null
        kill "$pid" 2>/dev/null
    done
    rm -rf "$TIMES_DIR"
}
trap cleanup EXIT
trap 'echo; echo "Interrupted - stopping renders."; exit 130' INT TERM

succeeded() {
    grep -qE "Render of module $1 completed successfully|rendering succeeded|rendering complete" \
        "$PLAIN_DIR/codeplain.$1.log" 2>/dev/null
}

# Step 2 - start every render at once. Headless progress goes to the log file,
# so stdout is discarded to keep this terminal readable.
cd "$PLAIN_DIR" || { echo "Error: cannot enter $PLAIN_DIR" >&2; exit 69; }
for module in "${MODULES[@]}"; do
    (
        start=$(date +%s)
        codeplain "$module.plain" --headless --log-file-name "codeplain.$module.log" >/dev/null 2>&1
        rc=$?
        end=$(date +%s)
        echo "$((end - start)) $rc" > "$TIMES_DIR/$module"
        echo "Finished $module in $((end - start))s (exit $rc)"
    ) &
    PIDS+=("$!")
done
echo "Started ${#MODULES[@]} headless renders - waiting for them to finish..."
wait "${PIDS[@]}"
PIDS=()

# Step 3 - per-render results, then the stats over the successful renders.
echo
printf "%-24s %10s  %s\n" "MODULE" "SECONDS" "STATUS"
OK_TIMES=()
for module in "${MODULES[@]}"; do
    read -r secs rc < "$TIMES_DIR/$module" 2>/dev/null || { secs="?"; rc="?"; }
    if [ "$rc" = "0" ] && succeeded "$module"; then
        status="ok"
        OK_TIMES+=("$secs")
    else
        status="FAILED (exit $rc; see plain/codeplain.$module.log)"
    fi
    printf "%-24s %10s  %s\n" "$module" "$secs" "$status"
done

echo
if [ "${#OK_TIMES[@]}" -eq 0 ]; then
    echo "No render succeeded - no timing stats."
    exit 1
fi
printf "%s\n" "${OK_TIMES[@]}" | awk -v total="${#MODULES[@]}" '
    function fmt(s) { return sprintf("%.1fs (%dm %02ds)", s, int(s / 60), int(s % 60 + 0.5)) }
    { x[NR] = $1; sum += $1
      if (NR == 1 || $1 < min) min = $1
      if (NR == 1 || $1 > max) max = $1 }
    END {
        mean = sum / NR
        for (i = 1; i <= NR; i++) ss += (x[i] - mean) ^ 2
        sd = NR > 1 ? sqrt(ss / (NR - 1)) : 0
        printf "Successful renders: %d/%d\n", NR, total
        printf "Mean:    %s\n", fmt(mean)
        printf "Std dev: %s\n", fmt(sd)
        printf "Min:     %s\n", fmt(min)
        printf "Max:     %s\n", fmt(max)
    }'
[ "${#OK_TIMES[@]}" -eq "${#MODULES[@]}" ]

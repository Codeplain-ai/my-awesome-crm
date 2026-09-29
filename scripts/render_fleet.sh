#!/bin/bash
# Render <count> instances of one integration module side by side, then deploy
# and run.
#
#   1. Starts from a clean slate: removes the original module's build folder
#      plain/plain_modules/<module>/ and log, and every copy left by an earlier
#      run - plain/<module><N>.plain, plain/plain_modules/<module><N>/, and its
#      log - so every render starts from scratch. Only plain/<module>.plain
#      itself is kept. Then copies it to plain/<module>1.plain ...
#      <module><count-1>.plain, so there are <count> modules in total.
#   2. Opens a tmux session "<module>-fleet" whose "renders" window is a tiled
#      grid (3 x 3 for the default 9) running `codeplain <module><idx>.plain` in
#      each pane (from plain/).
#      Each render writes its own log (plain/codeplain.<module><idx>.log) so the
#      concurrent runs do not overwrite each other's codeplain.log. A
#      "<module>-fleet" session left over from an earlier run is killed first.
#   3. A second window, "deploy", waits until all renders have finished, then
#      runs scripts/deploy_integrations.sh. A copy whose render failed
#      is left out (its code/ may be partial or stale); every other module
#      under plain/plain_modules/ is deployed. codeplain exits 0 even when a
#      render fails, so success is read from the render's own log: it must
#      carry codeplain's success banner.
#   4. The "deploy" window then runs scripts/start.sh (the server).
#
# Switch windows with the tmux prefix + n / p. The script attaches to the
# session (or switches to it when already inside tmux).
#
#   Usage: ./scripts/render_fleet.sh <module> [count]
#          e.g. ./scripts/render_fleet.sh hubspot 4
#          <count> is the total number of renders, default 9.
#
# Requires tmux and codeplain on PATH, and CODEPLAIN_API_KEY in the shell the
# panes start (i.e. exported by your shell profile or the tmux server's env).
#
# macOS / Linux only: tmux has no native Windows build, so there is no .ps1
# counterpart.

set -u

DEFAULT_COUNT=9

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLAIN_DIR="$ROOT/plain"

# Internal mode, run inside the "deploy" window: wait for every render, then
# deploy and start the server.
if [ "${1:-}" = "--after-renders" ]; then
    STATUS_DIR="$2"
    shift 2
    RENDERED=("$@")

    succeeded() {
        grep -qE "Render of module $1 completed successfully|rendering succeeded|rendering complete" \
            "$PLAIN_DIR/codeplain.$1.log" 2>/dev/null
    }
    failed() {
        grep -qE "Render of module $1 failed|rendering failed" \
            "$PLAIN_DIR/codeplain.$1.log" 2>/dev/null
    }

    # codeplain's TUI stays open after a render ends, so the process exiting
    # (the pane's marker file) cannot be the signal. A render counts as
    # finished once its log carries the success or failure banner; the marker
    # still covers a codeplain that crashed or quit before writing either.
    echo "Waiting for ${#RENDERED[@]} renders to finish..."
    while :; do
        done_count=0
        for module in "${RENDERED[@]}"; do
            if succeeded "$module" || failed "$module" || [ -f "$STATUS_DIR/$module" ]; then
                done_count=$((done_count + 1))
            fi
        done
        [ "$done_count" -eq "${#RENDERED[@]}" ] && break
        printf "\r%d/%d renders finished" "$done_count" "${#RENDERED[@]}"
        sleep 5
    done
    printf "\rAll %d renders finished.        \n" "${#RENDERED[@]}"

    FAILED=()
    for module in "${RENDERED[@]}"; do
        log="$PLAIN_DIR/codeplain.$module.log"
        if ! succeeded "$module"; then
            echo "Render of $module FAILED (no success banner in $log) - not deploying it."
            FAILED+=("$module")
        fi
    done
    rm -rf "$STATUS_DIR"

    DEPLOY=()
    for dir in "$PLAIN_DIR/plain_modules"/*/; do
        [ -d "$dir" ] || continue
        module="$(basename "$dir")"
        case " ${FAILED[*]:-} " in *" $module "*) continue ;; esac
        DEPLOY+=("$module")
    done
    if [ "${#DEPLOY[@]}" -eq 0 ]; then
        echo "Error: nothing to deploy." >&2
        exit 1
    fi

    "$SCRIPT_DIR/deploy_integrations.sh" "${DEPLOY[@]}" || {
        echo "Error: deploy failed - not starting the server." >&2
        exit 1
    }
    exec "$SCRIPT_DIR/start.sh"
fi

# tmux is checked before anything else: without it there is nothing to run.
if ! command -v tmux >/dev/null 2>&1; then
    echo "Error: tmux is not installed - this script runs the renders in a tmux session." >&2
    case "$(uname -s)" in
        Darwin) echo "       Install it with: brew install tmux" >&2 ;;
        Linux)
            if command -v apt-get >/dev/null 2>&1; then
                echo "       Install it with: sudo apt-get install tmux" >&2
            elif command -v dnf >/dev/null 2>&1; then
                echo "       Install it with: sudo dnf install tmux" >&2
            else
                echo "       Install tmux with your distribution's package manager." >&2
            fi ;;
        *) echo "       Install tmux, then re-run this script." >&2 ;;
    esac
    echo "       Then re-run: $0 $*" >&2
    exit 69
fi

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
SESSION="$MODULE-fleet"

if ! command -v codeplain >/dev/null 2>&1; then
    echo "Error: codeplain is not on PATH." >&2
    exit 69
fi

if [ ! -f "$PLAIN_DIR/$MODULE.plain" ]; then
    echo "Error: $PLAIN_DIR/$MODULE.plain not found." >&2
    exit 2
fi

# A fleet session left over from an earlier run is replaced, not reused: kill
# it (stopping any renders still running in it) and drop its stale status dirs.
if tmux has-session -t "=$SESSION" 2>/dev/null; then
    if [ -n "${TMUX:-}" ] && [ "$(tmux display-message -p '#{session_name}')" = "$SESSION" ]; then
        echo "Error: run this from outside the '$SESSION' tmux session - it is about to be replaced." >&2
        exit 1
    fi
    echo "Killing previous tmux session '$SESSION'"
    tmux kill-session -t "=$SESSION"
fi
rm -rf "${TMPDIR:-/tmp}"/"${MODULE}"_fleet.*

# Step 1 - clean slate, then the copies. The original module's build and log
# are removed so it renders from scratch like the copies, and every
# <module><digits> copy from an earlier run is removed - not just the ones this
# run recreates - so a smaller count does not leave stale builds behind for
# deploy_integrations.sh to pick up. plain/<module>.plain, the source of every
# copy, is the only thing kept.
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

# Each pane drops a marker file here when its codeplain run finishes.
STATUS_DIR="$(mktemp -d "${TMPDIR:-/tmp}/${MODULE}_fleet.XXXXXX")"

# Step 2 - the tiled render grid, one pane per module. Pane/window ids (not indexes) are used so a
# custom base-index / pane-base-index in the user's tmux.conf does not matter.
PANES=()
PANES+=("$(tmux new-session -d -s "$SESSION" -n renders -c "$PLAIN_DIR" -x 240 -y 60 -P -F '#{pane_id}')")
RENDER_WINDOW="$(tmux display-message -p -t "${PANES[0]}" '#{window_id}')"
for ((n = 1; n < ${#MODULES[@]}; n++)); do
    PANES+=("$(tmux split-window -t "$RENDER_WINDOW" -c "$PLAIN_DIR" -P -F '#{pane_id}')")
    tmux select-layout -t "$RENDER_WINDOW" tiled >/dev/null
done

i=0
for module in "${MODULES[@]}"; do
    # A stale log from an earlier run must not count as this run's success.
    rm -f "$PLAIN_DIR/codeplain.$module.log"
    tmux send-keys -t "${PANES[$i]}" \
        "codeplain $module.plain --log-file-name codeplain.$module.log; touch '$STATUS_DIR/$module'" Enter
    i=$((i + 1))
done

# Steps 3 + 4 - the deploy window (waits, deploys, starts the server).
tmux new-window -d -t "$SESSION" -n deploy -c "$ROOT" \
    "'$SCRIPT_DIR/render_fleet.sh' --after-renders '$STATUS_DIR' ${MODULES[*]}; echo; echo '[deploy window finished - press Enter to close]'; read -r _"

tmux select-window -t "$RENDER_WINDOW"
if [ -n "${TMUX:-}" ]; then
    tmux switch-client -t "$SESSION"
else
    tmux attach-session -t "$SESSION"
fi

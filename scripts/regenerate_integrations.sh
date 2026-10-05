#!/bin/bash
# Regenerate the code of four integrations - hubspot, dynamics, salesforce and
# attio - side by side, then deploy and run.
#
#   1. Starts from a clean slate: removes each module's build folder
#      plain/plain_modules/<module>/ and its log plain/codeplain.<module>.log, so
#      every render starts from scratch. The plain/<module>.plain specs are
#      never touched.
#   2. Opens a tmux session "regenerate-integrations" whose "renders" window is a
#      tiled grid (2 x 2) running `codeplain <module>.plain` in each pane (from
#      plain/). Each render writes its own log (plain/codeplain.<module>.log) so
#      the concurrent runs do not overwrite each other's codeplain.log. A
#      session left over from an earlier run is killed first.
#   3. A second window, "deploy", waits until all renders have finished, then
#      runs scripts/deploy_integrations.sh. A module whose render failed is left
#      out (its code/ may be partial or stale); the others are deployed.
#      codeplain exits 0 even when a render fails, so success is read from the
#      render's own log: it must carry codeplain's success banner.
#   4. The "deploy" window then runs scripts/start.sh (the server).
#
# Because deploy_integrations.sh empties src/integrations/ first, only the
# modules that rendered successfully in this run are present afterwards.
#
# Switch windows with the tmux prefix + n / p. The script attaches to the
# session (or switches to it when already inside tmux).
#
#   Usage: ./scripts/regenerate_integrations.sh
#
# Requires tmux and codeplain on PATH, and CODEPLAIN_API_KEY in the shell the
# panes start (i.e. exported by your shell profile or the tmux server's env).
#
# macOS / Linux only: tmux has no native Windows build, so there is no .ps1
# counterpart.

set -u

MODULES=(hubspot dynamics salesforce attio)
SESSION="regenerate-integrations"

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

    DEPLOY=()
    for module in "${RENDERED[@]}"; do
        if succeeded "$module"; then
            DEPLOY+=("$module")
        else
            echo "Render of $module FAILED (no success banner in $PLAIN_DIR/codeplain.$module.log) - not deploying it."
        fi
    done
    rm -rf "$STATUS_DIR"

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
    echo "       Then re-run: $0" >&2
    exit 69
fi

if [ $# -ne 0 ]; then
    echo "Usage: $0   (takes no arguments; regenerates: ${MODULES[*]})" >&2
    exit 1
fi

if ! command -v codeplain >/dev/null 2>&1; then
    echo "Error: codeplain is not on PATH." >&2
    exit 69
fi

for module in "${MODULES[@]}"; do
    if [ ! -f "$PLAIN_DIR/$module.plain" ]; then
        echo "Error: $PLAIN_DIR/$module.plain not found." >&2
        exit 2
    fi
done

# A session left over from an earlier run is replaced, not reused: kill it
# (stopping any renders still running in it) and drop its stale status dirs.
if tmux has-session -t "=$SESSION" 2>/dev/null; then
    if [ -n "${TMUX:-}" ] && [ "$(tmux display-message -p '#{session_name}')" = "$SESSION" ]; then
        echo "Error: run this from outside the '$SESSION' tmux session - it is about to be replaced." >&2
        exit 1
    fi
    echo "Killing previous tmux session '$SESSION'"
    tmux kill-session -t "=$SESSION"
fi
rm -rf "${TMPDIR:-/tmp}"/regenerate_integrations.*

# Step 1 - clean slate: each module's build folder and log are removed so it
# renders from scratch.
for module in "${MODULES[@]}"; do
    for path in "$PLAIN_DIR/plain_modules/$module" "$PLAIN_DIR/codeplain.$module.log"; do
        [ -e "$path" ] || continue
        echo "Removing $path"
        rm -rf "$path"
    done
done
echo "Regenerating ${#MODULES[@]} integrations: ${MODULES[*]}"

# Each pane drops a marker file here when its codeplain run finishes.
STATUS_DIR="$(mktemp -d "${TMPDIR:-/tmp}/regenerate_integrations.XXXXXX")"

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
    tmux send-keys -t "${PANES[$i]}" \
        "codeplain $module.plain --log-file-name codeplain.$module.log; touch '$STATUS_DIR/$module'" Enter
    i=$((i + 1))
done

# Steps 3 + 4 - the deploy window (waits, deploys, starts the server).
tmux new-window -d -t "$SESSION" -n deploy -c "$ROOT" \
    "'$SCRIPT_DIR/regenerate_integrations.sh' --after-renders '$STATUS_DIR' ${MODULES[*]}; echo; echo '[deploy window finished - press Enter to close]'; read -r _"

tmux select-window -t "$RENDER_WINDOW"
if [ -n "${TMUX:-}" ]; then
    tmux switch-client -t "$SESSION"
else
    tmux attach-session -t "$SESSION"
fi

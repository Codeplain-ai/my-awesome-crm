#!/usr/bin/env bash
#
# start.sh — one-shot getting-started + run script for My Awesome CRM.
#
# Idempotent: on first run it bootstraps everything (Python 3.12-3.14, virtualenv,
# dependencies) and starts the server; on subsequent runs it detects that the
# environment is already set up and just starts the server.
#
# Usage:
#   ./scripts/start.sh
#
# Honors the same env vars the app does (all optional):
#   CRM_PORT     (default 8000)  — port to serve on
#   CRM_DB_PATH  (default crm.db) — where the SQLite file lives

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve paths so the script works no matter where it is invoked from.
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
REQUIREMENTS="$PROJECT_ROOT/requirements.txt"
# Any stable Python release from 3.12 up. The ceiling excludes pre-releases
# (3.15 is a RC and our dependencies don't support it). 
# The minimum version is what auto-install targets.
MIN_PYTHON_VERSION="3.12"
MAX_PYTHON_VERSION="3.14"
MIN_PYTHON_MAJOR="3"
MIN_PYTHON_MINOR="12"
MAX_PYTHON_MINOR="14"

cd "$PROJECT_ROOT"

# ---------------------------------------------------------------------------
# Small logging helpers.
# ---------------------------------------------------------------------------
info()  { printf '\033[0;34m==>\033[0m %s\n' "$*"; }
ok()    { printf '\033[0;32m  ✓\033[0m %s\n' "$*"; }
warn()  { printf '\033[0;33m  ! \033[0m%s\n' "$*"; }
error() { printf '\033[0;31mERROR:\033[0m %s\n' "$*" >&2; }

# ---------------------------------------------------------------------------
# 1. Ensure a supported Python (3.12 - 3.14) is available.
# ---------------------------------------------------------------------------
# Returns 0 if the given interpreter falls inside the supported window.
python_in_range() {
    "$1" -c "import sys; sys.exit(0 if ($MIN_PYTHON_MAJOR, $MIN_PYTHON_MINOR) <= sys.version_info[:2] <= ($MIN_PYTHON_MAJOR, $MAX_PYTHON_MINOR) else 1)" 2>/dev/null
}

find_python() {
    # Try, in order: version-specific launchers from the newest supported down
    # to the minimum, then the generic python3 / python. First one inside the
    # supported range wins, so the script is agnostic to the exact 3.x installed.
    local candidate
    for candidate in \
        python3.14 python3.13 "python$MIN_PYTHON_VERSION" \
        python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && python_in_range "$candidate"; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

install_python() {
    case "$(uname -s)" in
        Darwin)
            if ! command -v brew >/dev/null 2>&1; then
                error "Homebrew is required to auto-install Python $MIN_PYTHON_VERSION but was not found."
                error "Install Homebrew from https://brew.sh and re-run this script."
                exit 1
            fi
            info "Installing Python $MIN_PYTHON_VERSION via Homebrew..."
            brew install "python@$MIN_PYTHON_VERSION"
            # Homebrew's python@3.12 is keg-only: its `python3.12` binary lives in
            # the formula's opt bin and may not be on PATH yet. Add it so the
            # follow-up find_python call can locate it (works on both Apple
            # Silicon /opt/homebrew and Intel /usr/local prefixes).
            local brew_prefix
            brew_prefix="$(brew --prefix "python@$MIN_PYTHON_VERSION" 2>/dev/null || true)"
            if [ -n "$brew_prefix" ] && [ -d "$brew_prefix/bin" ]; then
                export PATH="$brew_prefix/bin:$PATH"
            fi
            ;;
        Linux)
            if command -v apt-get >/dev/null 2>&1; then
                info "Installing Python $MIN_PYTHON_VERSION via apt-get..."
                sudo apt-get update
                sudo apt-get install -y "python$MIN_PYTHON_VERSION" "python$MIN_PYTHON_VERSION-venv"
            elif command -v dnf >/dev/null 2>&1; then
                info "Installing Python $MIN_PYTHON_VERSION via dnf..."
                sudo dnf install -y "python$MIN_PYTHON_VERSION"
            else
                error "No supported package manager (apt-get/dnf) found to install Python $MIN_PYTHON_VERSION."
                exit 1
            fi
            ;;
        *)
            error "Automatic Python install is not supported on this OS. Please install Python $MIN_PYTHON_VERSION manually."
            exit 1
            ;;
    esac
}

info "Checking for Python $MIN_PYTHON_VERSION - $MAX_PYTHON_VERSION..."
if PYTHON_BIN="$(find_python)"; then
    ok "Found: $($PYTHON_BIN --version 2>&1)"
else
    warn "No supported Python ($MIN_PYTHON_VERSION - $MAX_PYTHON_VERSION) was found."
    read -r -p "Install Python $MIN_PYTHON_VERSION now? [y/N] " reply
    case "$reply" in
        [yY][eE][sS]|[yY])
            install_python
            if PYTHON_BIN="$(find_python)"; then
                ok "Installed: $($PYTHON_BIN --version 2>&1)"
            else
                error "A supported Python ($MIN_PYTHON_VERSION - $MAX_PYTHON_VERSION) is still not found after install. Please install it manually."
                exit 1
            fi
            ;;
        *)
            error "Python $MIN_PYTHON_VERSION - $MAX_PYTHON_VERSION is required to run this project. Aborting."
            exit 1
            ;;
    esac
fi

# ---------------------------------------------------------------------------
# 2. Ensure the virtualenv exists.
# ---------------------------------------------------------------------------
# A directory is not proof of a usable venv. An interpreter without ensurepip
# (Debian/Ubuntu lacking python3-venv) builds the tree, aborts at the pip step,
# and leaves a pip-less .venv behind — after which a bare -d check reports
# "already exists" and the install step dies with "No module named pip".
# Validate the way the test scripts do: bin/python plus the pyvenv.cfg marker.
venv_is_valid() {
    [ -x "$VENV_DIR/bin/python" ] && [ -f "$VENV_DIR/pyvenv.cfg" ]
}

info "Checking for virtualenv at .venv..."
if [ -d "$VENV_DIR" ] && ! venv_is_valid; then
    warn "Found an incomplete virtualenv at $VENV_DIR — recreating it."
    rm -rf "$VENV_DIR"
fi
if [ ! -d "$VENV_DIR" ]; then
    warn "No virtualenv found — creating one."
    # Remove the partial tree on failure so the next run recreates it instead of
    # inheriting a broken one.
    if ! "$PYTHON_BIN" -m venv "$VENV_DIR" || ! venv_is_valid; then
        rm -rf "$VENV_DIR"
        error "Failed to create a virtualenv with $PYTHON_BIN."
        error "On Debian/Ubuntu the venv module ships separately:"
        error "  sudo apt install python3-venv   (or python3.12-venv)"
        exit 1
    fi
    ok "Created virtualenv at $VENV_DIR"
else
    ok "Virtualenv already exists."
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# pip can be absent from an otherwise well-formed venv (see above). ensurepip
# bootstraps it — and is itself what Debian/Ubuntu ship in python3-venv, so when
# that package is missing this fails too and the message has to say so.
if ! python -m pip --version >/dev/null 2>&1; then
    warn "pip is missing from the virtualenv — bootstrapping it with ensurepip."
    if ! python -m ensurepip --upgrade >/dev/null 2>&1; then
        error "Could not bootstrap pip: this interpreter has no working ensurepip."
        error "On Debian/Ubuntu:  sudo apt install python3-venv   (or python3.12-venv)"
        error "Then delete $VENV_DIR and re-run this script."
        exit 1
    fi
    ok "pip bootstrapped into the virtualenv."
fi

# ---------------------------------------------------------------------------
# 3. Ensure requirements are installed.
#    We use a stamp file that records the hash of requirements.txt so we only
#    reinstall when the dependency list actually changed.
# ---------------------------------------------------------------------------
STAMP_FILE="$VENV_DIR/.requirements.installed"
current_hash() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$REQUIREMENTS" | awk '{print $1}'
    else
        sha256sum "$REQUIREMENTS" | awk '{print $1}'
    fi
}

info "Checking Python dependencies..."
REQ_HASH="$(current_hash)"
if [ ! -f "$STAMP_FILE" ] || [ "$(cat "$STAMP_FILE" 2>/dev/null)" != "$REQ_HASH" ]; then
    warn "Dependencies missing or out of date — installing."
    python -m pip install --upgrade pip
    python -m pip install -r "$REQUIREMENTS"
    echo "$REQ_HASH" > "$STAMP_FILE"
    ok "Dependencies installed."
else
    ok "Dependencies already up to date."
fi

# ---------------------------------------------------------------------------
# 4. Run the server.
#    We launch uvicorn in the background and wait on it, with a trap that tears
#    it down on Ctrl+C / termination. This guarantees the server (and uvicorn's
#    --reload child worker) is stopped when the script stops — an `exec`/foreground
#    run can otherwise leave the reload worker orphaned.
# ---------------------------------------------------------------------------
PORT="${CRM_PORT:-8000}"
info "Starting My Awesome CRM on http://localhost:$PORT ..."
info "  Web UI:  http://localhost:$PORT/"
info "  Swagger: http://localhost:$PORT/docs"
info "  (press Ctrl+C to stop)"

SERVER_PID=""
shutdown_server() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        info "Shutting down server..."
        # Kill the whole process group so uvicorn's reload worker goes too.
        kill -TERM -- "-$SERVER_PID" 2>/dev/null || kill -TERM "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap shutdown_server INT TERM EXIT

# Drop uvicorn's own startup banner. It reports the bind address
# (http://0.0.0.0:$PORT), which is not an address a browser can open — the
# clickable localhost URLs are printed above instead. Every other line from
# uvicorn (stderr) and from the app's JSON logger (stdout) passes through
# untouched; --line-buffered keeps the output live rather than block-buffered.
#
# The filter is a process substitution, not a pipe, so $! stays uvicorn's own
# PID and the process-group teardown above still works.
#
# Start uvicorn in its own process group so we can signal the whole group.
set -m
uvicorn src.main:app --reload --host 0.0.0.0 --port "$PORT" \
    > >(grep -v --line-buffered 'Uvicorn running on') 2>&1 &
SERVER_PID=$!
set +m
wait "$SERVER_PID"

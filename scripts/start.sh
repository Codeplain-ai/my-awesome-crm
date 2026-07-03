#!/usr/bin/env bash
#
# start.sh — one-shot getting-started + run script for My Awesome CRM.
#
# Idempotent: on first run it bootstraps everything (Python 3.12, virtualenv,
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
PYTHON_VERSION="3.12"

cd "$PROJECT_ROOT"

# ---------------------------------------------------------------------------
# Small logging helpers.
# ---------------------------------------------------------------------------
info()  { printf '\033[0;34m==>\033[0m %s\n' "$*"; }
ok()    { printf '\033[0;32m  ✓\033[0m %s\n' "$*"; }
warn()  { printf '\033[0;33m  ! \033[0m%s\n' "$*"; }
error() { printf '\033[0;31mERROR:\033[0m %s\n' "$*" >&2; }

# ---------------------------------------------------------------------------
# 1. Ensure Python 3.12 is available.
# ---------------------------------------------------------------------------
find_python312() {
    # Prefer the version-specific launcher, then fall back to plain python3.
    if command -v "python$PYTHON_VERSION" >/dev/null 2>&1; then
        echo "python$PYTHON_VERSION"
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        if python3 -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)' 2>/dev/null; then
            echo "python3"
            return 0
        fi
    fi
    return 1
}

install_python312() {
    case "$(uname -s)" in
        Darwin)
            if ! command -v brew >/dev/null 2>&1; then
                error "Homebrew is required to auto-install Python $PYTHON_VERSION but was not found."
                error "Install Homebrew from https://brew.sh and re-run this script."
                exit 1
            fi
            info "Installing Python $PYTHON_VERSION via Homebrew..."
            brew install "python@$PYTHON_VERSION"
            # Homebrew's python@3.12 is keg-only: its `python3.12` binary lives in
            # the formula's opt bin and may not be on PATH yet. Add it so the
            # follow-up find_python312 call can locate it (works on both Apple
            # Silicon /opt/homebrew and Intel /usr/local prefixes).
            local brew_prefix
            brew_prefix="$(brew --prefix "python@$PYTHON_VERSION" 2>/dev/null || true)"
            if [ -n "$brew_prefix" ] && [ -d "$brew_prefix/bin" ]; then
                export PATH="$brew_prefix/bin:$PATH"
            fi
            ;;
        Linux)
            if command -v apt-get >/dev/null 2>&1; then
                info "Installing Python $PYTHON_VERSION via apt-get..."
                sudo apt-get update
                sudo apt-get install -y "python$PYTHON_VERSION" "python$PYTHON_VERSION-venv"
            elif command -v dnf >/dev/null 2>&1; then
                info "Installing Python $PYTHON_VERSION via dnf..."
                sudo dnf install -y "python$PYTHON_VERSION"
            else
                error "No supported package manager (apt-get/dnf) found to install Python $PYTHON_VERSION."
                exit 1
            fi
            ;;
        *)
            error "Automatic Python install is not supported on this OS. Please install Python $PYTHON_VERSION manually."
            exit 1
            ;;
    esac
}

info "Checking for Python $PYTHON_VERSION..."
if PYTHON_BIN="$(find_python312)"; then
    ok "Found: $($PYTHON_BIN --version 2>&1)"
else
    warn "Python $PYTHON_VERSION is not installed."
    read -r -p "Install Python $PYTHON_VERSION now? [y/N] " reply
    case "$reply" in
        [yY][eE][sS]|[yY])
            install_python312
            if PYTHON_BIN="$(find_python312)"; then
                ok "Installed: $($PYTHON_BIN --version 2>&1)"
            else
                error "Python $PYTHON_VERSION still not found after install. Please install it manually."
                exit 1
            fi
            ;;
        *)
            error "Python $PYTHON_VERSION is required to run this project. Aborting."
            exit 1
            ;;
    esac
fi

# ---------------------------------------------------------------------------
# 2. Ensure the virtualenv exists.
# ---------------------------------------------------------------------------
info "Checking for virtualenv at .venv..."
if [ ! -d "$VENV_DIR" ]; then
    warn "No virtualenv found — creating one."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    ok "Created virtualenv at $VENV_DIR"
else
    ok "Virtualenv already exists."
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

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

# Start uvicorn in its own process group so we can signal the whole group.
set -m
uvicorn src.main:app --reload --host 0.0.0.0 --port "$PORT" &
SERVER_PID=$!
set +m
wait "$SERVER_PID"

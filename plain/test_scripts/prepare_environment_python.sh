#!/bin/bash
# Prepare-environment script for an EMBEDDED CRM integration plug-in (Python).
#
# The renderer calls this ONCE per render, before any conformance run. It
# builds the one expensive thing every conformance run needs - a venv with the
# host requirements.txt and pytest installed - so run_conformance_tests_python.sh
# (activate-only variant) attaches to it instead of creating and populating a
# fresh venv on every one of its N invocations per render.
#
# What this script deliberately does NOT do: stage the build folder ($1). The
# generated implementation changes after every functional spec renders, while
# this script runs only once, so a copy staged here would be stale. The
# conformance runner keeps overlaying the CURRENT $1 onto its own per-run host
# snapshot; only the venv is shared.
#
# The prepared environment lives at
#
#   <temp>/python_conformance_env_<module>_<hash>/.venv
#
# where <module> is the name of $1's parent folder (plain_modules/<module>/code)
# and <hash> is a short hash of $1's absolute path. $1's own basename is always
# "code", so keying on it alone would make every module share - and clobber -
# one folder; keying on the module lets several renders (e.g.
# scripts/regenerate_integrations.sh) prepare side by side. run_conformance_tests_python.sh
# derives the identical path. The folder is intentionally LEFT IN PLACE on exit:
# it is this script's deliverable, and the next prepare of the same module
# wipes and rebuilds it.
#
# The venv is built from the HOST project's interpreter at
# $HOST_CODEBASE_ROOT/.venv (provisioned by scripts/start.sh), so the tests run
# on the same Python the host uses - never one picked off PATH.
#
#   Usage: prepare_environment_python.sh <build_folder>
#
# Environment overrides:
#   HOST_CODEBASE_ROOT  host repo root (default: parent of plain/)
#
# Every failure exits 69: a half-prepared environment is unusable.

set -u

UNRECOVERABLE_ERROR_EXIT_CODE=69

banner() { printf '\n===== %s =====\n' "$1"; }

fail() {
    printf "Error: %s\n" "$1" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}

# Run a command, echoing it first; on failure print context and exit 69.
run() {
    printf '+ %s\n' "$*"
    "$@"
    local rc=$?
    if [ $rc -ne 0 ]; then
        printf "Error: command failed (exit %s): %s\n" "$rc" "$*" >&2
        printf "       cwd=%s PATH=%s\n" "$(pwd)" "$PATH" >&2
        exit $UNRECOVERABLE_ERROR_EXIT_CODE
    fi
}

start_time=$(date +%s)

# ----- [1/5] Toolchain check ------------------------------------------------
banner "[1/5] Toolchain check"
PLAIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOST_CODEBASE_ROOT="${HOST_CODEBASE_ROOT:-$(cd "$PLAIN_DIR/.." && pwd)}"
HOST_VENV_DIR="$HOST_CODEBASE_ROOT/.venv"
PYTHON_CMD="$HOST_VENV_DIR/bin/python"

if [ ! -x "$PYTHON_CMD" ] || [ ! -f "$HOST_VENV_DIR/pyvenv.cfg" ]; then
    printf "Error: host virtual environment not found or invalid at %s.\n" "$HOST_VENV_DIR" >&2
    printf "       Provision it first, e.g. ./scripts/start.sh (or\n" >&2
    printf "       python3 -m venv .venv && .venv/bin/pip install -r requirements.txt).\n" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
fi
printf "Host codebase root: %s\n" "$HOST_CODEBASE_ROOT"
printf "Python interpreter: %s (host venv)\n" "$PYTHON_CMD"
"$PYTHON_CMD" --version

# ----- [2/5] Argument validation --------------------------------------------
banner "[2/5] Argument validation"
if [ -z "${1:-}" ]; then
    printf "Error: No build folder provided.\n" >&2
    printf "Usage: %s <build_folder>\n" "$0" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
fi
[ -d "$1" ] || fail "build folder not found: $1"
ABS_BUILD_FOLDER="$(cd "$1" && pwd)"
printf "Build folder: %s\n" "$ABS_BUILD_FOLDER"

# ----- [3/5] Working folder setup -------------------------------------------
banner "[3/5] Working folder setup"
# Keep this derivation identical to run_conformance_tests_python.sh.
MODULE_NAME="$(basename "$(dirname "$ABS_BUILD_FOLDER")")"
PATH_HASH="$("$PYTHON_CMD" -c 'import hashlib, sys; print(hashlib.sha1(sys.argv[1].encode()).hexdigest()[:8])' "$ABS_BUILD_FOLDER")" \
    || fail "could not hash the build folder path"
TMP_ROOT="${TMPDIR:-/tmp}"
PREPARED_ENV="${TMP_ROOT%/}/python_conformance_env_${MODULE_NAME}_${PATH_HASH}"
VENV_DIR="$PREPARED_ENV/.venv"
VENV_PY="$VENV_DIR/bin/python"
READY_MARKER="$PREPARED_ENV/.prepared"

printf "Module:           %s\n" "$MODULE_NAME"
printf "Prepared env:     %s\n" "$PREPARED_ENV"
run rm -rf "$PREPARED_ENV"
run mkdir -p "$PREPARED_ENV"
cd "$PREPARED_ENV" 2>/dev/null || fail "could not enter prepared env folder $PREPARED_ENV"
printf "Now in:           %s\n" "$(pwd)"

# ----- [4/5] Create the venv ------------------------------------------------
banner "[4/5] Create venv"
run "$PYTHON_CMD" -m venv "$VENV_DIR"

# Some hosts create a venv without pip (a stripped Python where ensurepip is
# missing, or an incomplete system python3-venv package). Try to bootstrap it.
if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
    printf "pip not found in venv; attempting to bootstrap it with ensurepip\n"
    "$VENV_PY" -m ensurepip --upgrade --default-pip
fi
"$VENV_PY" -m pip --version >/dev/null 2>&1 || {
    printf "Error: pip is not available in the venv at %s and could not be bootstrapped.\n" "$VENV_DIR" >&2
    printf "       Install the platform's Python venv/pip support (e.g. the python3-venv package) and retry.\n" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}

# ----- [5/5] Install dependencies -------------------------------------------
banner "[5/5] Install dependencies"
install_start=$(date +%s)
run "$VENV_PY" -m pip install --upgrade pip
# Host runtime deps, read in place (read-only) from the real host tree, so the
# conformance runner's snapshot of the implementation imports cleanly.
HOST_REQUIREMENTS="$HOST_CODEBASE_ROOT/requirements.txt"
if [ -f "$HOST_REQUIREMENTS" ]; then
    printf "Installing host requirements from %s into %s\n" "$HOST_REQUIREMENTS" "$VENV_DIR"
    run "$VENV_PY" -m pip install -r "$HOST_REQUIREMENTS"
else
    printf "Warning: no host requirements.txt at %s\n" "$HOST_REQUIREMENTS"
fi
run "$VENV_PY" -m pip install pytest
install_end=$(date +%s)
printf "Requirements setup completed in %s seconds\n" "$((install_end - install_start))"

# Written last, so the conformance runner can tell a complete environment from
# one a failed prepare left half-built.
run touch "$READY_MARKER"

end_time=$(date +%s)
printf "\nSummary: lang=python prepared_env=%s venv=%s python=%s duration=%ss exit=0\n" \
    "$PREPARED_ENV" "$VENV_DIR" "$("$VENV_PY" --version 2>&1)" "$((end_time - start_time))"
exit 0

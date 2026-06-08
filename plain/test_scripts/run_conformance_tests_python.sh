#!/bin/bash
# Conformance-test runner for an EMBEDDED CRM integration plug-in (Python).
#
# Variant: install-inline (no prepare_environment_python.sh exists). This maps
# the embedded Java conformance flow onto Python:
#
#   Java                                   | Python (this script)
#   ---------------------------------------|----------------------------------------
#   mvn install from ROOT (host + impl)     | overlay $1 (generated impl) into the
#     -> artifact in ~/.m2                  |   host ROOT src/integrations/<name>/,
#                                           |   install ROOT requirements.txt
#   cd .tmp/java_conformance && mvn install | stage $2 into .tmp/python_conformance,
#     -> resolve conformance deps           |   install the conformance suite's deps
#   mvn test (impl from ~/.m2)              | cd .tmp/python_conformance && pytest
#                                           |   with PYTHONPATH=ROOT so the ROOT impl
#                                           |   code is what gets imported
#
# $1 (build folder) is overlaid into the host root per the embedded contract
# (scoped to the module's own package dir). $2 (conformance tests) is copied
# into .tmp and run from there, leaving the authored test tree pristine.
#
#   Usage: run_conformance_tests_python.sh <build_folder> <conformance_tests_folder>
#
# Credentials come from the environment. A .env file at the project root is
# REQUIRED (the script exits 69 if it is absent) and is loaded into the
# environment before the tests run; shell-exported variables take precedence
# over .env. This script is integration-agnostic - it never inspects or
# validates any specific secret by name. Each integration validates the
# credentials it actually needs at call time (e.g. fetch_contacts() raises if a
# required variable is missing), and the live run surfaces that failure.
#
# Environment overrides:
#   HOST_CODEBASE_ROOT  host repo root (default: parent of plain/)
#   ENV_FILE            path to the required .env file (default: <host root>/.env)

set -u

UNRECOVERABLE_ERROR_EXIT_CODE=69
NO_TESTS_EXIT_CODE=1

banner() { printf '\n===== %s =====\n' "$1"; }

# ----- [1/8] Toolchain check ------------------------------------------------
banner "[1/8] Toolchain check"
if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_CMD=python3.12
elif command -v python3.13 >/dev/null 2>&1; then
    PYTHON_CMD=python3.13
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=python3
else
    printf "Error: Python 3.12+ interpreter not found. Please install Python.\n" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
fi
printf "Python interpreter: %s (%s)\n" "$PYTHON_CMD" "$(command -v "$PYTHON_CMD")"
"$PYTHON_CMD" --version

# ----- [2/8] Argument validation --------------------------------------------
banner "[2/8] Argument validation"
if [ -z "${1:-}" ]; then
    printf "Error: No build folder provided.\n" >&2
    printf "Usage: %s <build_folder> <conformance_tests_folder>\n" "$0" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
fi
if [ -z "${2:-}" ]; then
    printf "Error: No conformance tests folder provided.\n" >&2
    printf "Usage: %s <build_folder> <conformance_tests_folder>\n" "$0" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
fi

BUILD_FOLDER="$1"
TESTS_FOLDER="$2"

if [ ! -d "$BUILD_FOLDER" ]; then
    printf "Error: build folder not found: %s\n" "$BUILD_FOLDER" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
fi
if [ ! -d "$TESTS_FOLDER" ]; then
    printf "Error: conformance tests folder not found: %s\n" "$TESTS_FOLDER" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
fi

# ----- [3/8] Resolve paths --------------------------------------------------
banner "[3/8] Resolve paths"
current_dir="$(pwd)"
PLAIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOST_CODEBASE_ROOT="${HOST_CODEBASE_ROOT:-$(cd "$PLAIN_DIR/.." && pwd)}"
ABS_BUILD_FOLDER="$(cd "$BUILD_FOLDER" && pwd)"
ABS_TESTS_FOLDER="$(cd "$TESTS_FOLDER" && pwd)"

if [ ! -d "$HOST_CODEBASE_ROOT" ]; then
    printf "Error: host codebase root not found: %s\n" "$HOST_CODEBASE_ROOT" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
fi
printf "Invocation dir (current_dir):  %s\n" "$current_dir"
printf "Build folder (impl source):    %s\n" "$ABS_BUILD_FOLDER"
printf "Conformance tests source:      %s\n" "$ABS_TESTS_FOLDER"
printf "Host codebase root:            %s\n" "$HOST_CODEBASE_ROOT"

# ----- [4/8] Overlay generated implementation into the host ROOT ------------
# Mirrors the Java "mvn install from root with all code" step: put the freshly
# generated implementation where the conformance suite will import it from
# (root's src/). Scoped to the module's own integration package dir(s) only -
# never the host's top-level src/ or tests/.
banner "[4/8] Overlay implementation into host root"
STAGED_ANY=0
for sub in src tests; do
    pkg_root="$ABS_BUILD_FOLDER/$sub/integrations"
    [ -d "$pkg_root" ] || continue
    for pkg in "$pkg_root"/*/; do
        [ -d "$pkg" ] || continue
        name="$(basename "$pkg")"
        rel="$sub/integrations/$name"
        dest="$HOST_CODEBASE_ROOT/$rel"
        printf "Staging %s into host root\n" "$rel"
        rm -rf "$dest"
        mkdir -p "$dest"
        cp -R "$pkg"/. "$dest"/
        STAGED_ANY=1
    done
done
if [ "$STAGED_ANY" -ne 1 ]; then
    printf "Error: build folder ships no src/integrations/<name>/ packages: %s\n" "$ABS_BUILD_FOLDER" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
fi

# ----- [5/8] Provider credentials (live run) --------------------------------
# A .env at the project root is REQUIRED. This step only guarantees the file
# exists and loads it into the environment - it is integration-agnostic and
# never validates any specific secret by name. Each integration validates the
# credentials it needs at call time; the live run surfaces a missing one.
banner "[5/8] Provider credentials"
ENV_FILE="${ENV_FILE:-$HOST_CODEBASE_ROOT/.env}"
if [ ! -f "$ENV_FILE" ]; then
    printf "Error: credentials file not found: %s\n" "$ENV_FILE" >&2
    printf "       :ConformanceTests: run live and require a .env at the project root.\n" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
fi
printf "Loading credentials from %s (shell-exported vars take precedence)\n" "$ENV_FILE"
# Shell-exported credentials are authoritative; .env only fills variables the
# shell did not already set. Parse KEY=VALUE lines, skipping comments / blanks.
while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue ;; esac
    key="${line%%=*}"
    val="${line#*=}"
    key="$(printf '%s' "$key" | tr -d '[:space:]')"
    [ "$key" = "$line" ] && continue   # line had no '='
    case "$val" in                     # strip one layer of surrounding quotes
        \"*\") val="${val#\"}"; val="${val%\"}" ;;
        \'*\') val="${val#\'}"; val="${val%\'}" ;;
    esac
    if [ -z "${!key:-}" ]; then
        export "$key=$val"
    fi
done < "$ENV_FILE"

# ----- [6/8] Stage conformance tests into .tmp ------------------------------
banner "[6/8] Stage conformance tests into working folder"
WORKING_FOLDER="$PLAIN_DIR/.tmp/python_conformance"
printf "Working folder: %s\n" "$WORKING_FOLDER"
if [ -d "$WORKING_FOLDER" ]; then
    find "$WORKING_FOLDER" -mindepth 1 -exec rm -rf {} +
else
    mkdir -p "$WORKING_FOLDER"
fi
cp -R "$ABS_TESTS_FOLDER"/. "$WORKING_FOLDER"/

# ----- [7/8] Install dependencies (isolated venv inside working folder) -----
banner "[7/8] Install dependencies"
start_time=$(date +%s)
VENV_DIR="$WORKING_FOLDER/.venv"
if ! "$PYTHON_CMD" -m venv "$VENV_DIR"; then
    printf "Error: failed to create virtual environment at %s\n" "$VENV_DIR" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
fi
VENV_PY="$VENV_DIR/bin/python"

# Some hosts create a venv without pip (a stripped Python where ensurepip is
# missing, or an incomplete system python3-venv package). pip must be present
# inside the venv; try to bootstrap it with ensurepip, and if it still is not
# available, fail fast with 69 rather than dying later with an opaque error.
if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
    printf "pip not found in venv; attempting to bootstrap it with ensurepip\n" >&2
    "$VENV_PY" -m ensurepip --upgrade --default-pip >/dev/null 2>&1
fi
if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
    printf "Error: pip is not available in the venv at %s and could not be bootstrapped.\n" "$VENV_DIR" >&2
    printf "       Install the platform's Python venv/pip support (e.g. the python3-venv package) and retry.\n" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
fi

"$VENV_PY" -m pip install --upgrade pip || exit $?

# Host runtime deps ("from src") so the root implementation imports cleanly.
if [ -f "$HOST_CODEBASE_ROOT/requirements.txt" ]; then
    printf "Installing host requirements from %s\n" "$HOST_CODEBASE_ROOT/requirements.txt"
    "$VENV_PY" -m pip install -r "$HOST_CODEBASE_ROOT/requirements.txt" || exit $?
fi
# Conformance suite's own deps ("from conformance"), if it ships any.
if [ -f "$WORKING_FOLDER/requirements.txt" ]; then
    printf "Installing conformance-suite requirements\n"
    "$VENV_PY" -m pip install -r "$WORKING_FOLDER/requirements.txt" || exit $?
fi
"$VENV_PY" -m pip install pytest || exit $?

end_time=$(date +%s)
printf "Requirements setup completed in %s seconds\n" "$((end_time - start_time))"

# ----- [8/8] Run conformance tests LIVE from .tmp, impl from ROOT -----------
banner "[8/8] Run conformance tests (live provider)"
cd "$WORKING_FOLDER" 2>/dev/null || {
    printf "Error: could not enter working folder %s\n" "$WORKING_FOLDER" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}
# PYTHONPATH=ROOT => `from src.integrations.<name> import ...` resolves to the
# implementation code in the host root, not anything under .tmp.
export PYTHONPATH="$HOST_CODEBASE_ROOT${PYTHONPATH:+:$PYTHONPATH}"
TEST_CMD=("$VENV_PY" -m pytest -v --import-mode=importlib -p no:cacheprovider \
          --basetemp="$WORKING_FOLDER/.pytest_tmp" \
          "$WORKING_FOLDER")

printf "Now in:       %s\n" "$(pwd)"
printf "PYTHONPATH:   %s\n" "$PYTHONPATH"
printf "Test command: %s\n\n" "${TEST_CMD[*]}"

output=$("${TEST_CMD[@]}" 2>&1)
exit_code=$?
echo "$output"

# pytest exit 5 == no tests collected. Strict no-tests guard.
if [ "$exit_code" -eq 5 ] || echo "$output" | grep -qiE "no tests ran"; then
    printf "\nError: No conformance tests discovered in %s.\n" "$WORKING_FOLDER" >&2
    printf "Failure context: cwd=%s current_dir=%s tests=%s\n" \
        "$(pwd)" "$current_dir" "$ABS_TESTS_FOLDER" >&2
    exit $NO_TESTS_EXIT_CODE
fi

# Strict pass criteria: clean exit AND zero failures / errors / skipped.
if [ "$exit_code" -ne 0 ] || echo "$output" | grep -qiE "[0-9]+ (failed|error|skipped|xfailed|xpassed)"; then
    printf "\nError: conformance run did not pass cleanly (exit %s).\n" "$exit_code" >&2
    printf "All conformance tests must pass with zero failures, errors, and skips.\n" >&2
    printf "Failure context: cwd=%s current_dir=%s tests=%s PYTHONPATH=%s\n" \
        "$(pwd)" "$current_dir" "$ABS_TESTS_FOLDER" "$PYTHONPATH" >&2
    [ "$exit_code" -eq 0 ] && exit_code=1
    exit "$exit_code"
fi

printf "\nConformance run passed.\n"
printf "Summary: variant=install-inline cmd='%s' exit=%s current_dir=%s working_folder=%s\n" \
    "${TEST_CMD[*]}" "$exit_code" "$current_dir" "$WORKING_FOLDER"
exit "$exit_code"

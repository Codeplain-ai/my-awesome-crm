#!/bin/bash
# Conformance-test runner for an EMBEDDED CRM integration plug-in (Python).
#
# Variant: activate-only. prepare_environment_python.sh runs once per render and
# builds the venv (host requirements.txt + pytest); this script attaches to it
# and exits 69 if it is missing. This maps the embedded Java conformance flow
# onto Python:
#
#   Java                                   | Python
#   ---------------------------------------|----------------------------------------
#   mvn install from ROOT (host + impl)     | prepare: venv + host requirements.txt
#     -> artifact in ~/.m2                  | this script: snapshot the host into
#                                           |   the workspace, overlay $1 (generated
#                                           |   impl) onto its src/integrations/<name>/
#   cd .tmp/java_conformance && mvn install | stage $2 into the workspace, install
#     -> resolve conformance deps           |   the suite's own deps (if any) into
#                                           |   the prepared venv
#   mvn test (impl from ~/.m2)              | cd <workspace>/conformance && pytest
#                                           |   with PYTHONPATH=<workspace>/host so
#                                           |   the snapshot's impl is imported
#
# Every run works in its OWN isolated workspace in the system temp directory
# (unique per run), so several renders can run conformance side by side without
# clobbering each other or the real host tree:
#
#   <workspace>/host/         host codebase snapshot + $1 overlaid onto it
#   <workspace>/conformance/  copy of $2 (the authored test tree stays pristine)
#
# The real host tree is never written to, and the workspace is removed on exit.
# The prepared venv (<temp>/python_conformance_env_<module>_<hash>/.venv, see
# prepare_environment_python.sh) is shared by the module's runs and never
# deleted here; prepare owns its lifecycle. $1 is still overlaid on every run
# because the generated implementation changes after each functional spec.
#
#   Usage: run_conformance_tests_python.sh <build_folder> <conformance_tests_folder>
#
# Credentials come from the environment. A .env file at the project root is
# REQUIRED (the script exits 69 if it is absent) and is loaded into the
# environment before the tests run; shell-exported variables take precedence
# over .env. This script is integration-agnostic - it never inspects or
# validates any specific secret by name. Each integration validates the
# credentials it actually needs at call time (e.g. fetch(get_stored) raises if a
# required variable is missing), and the live run surfaces that failure.
#
# Environment overrides:
#   HOST_CODEBASE_ROOT  host repo root (default: parent of plain/)
#   ENV_FILE            path to the required .env file (default: <host root>/.env)
#
# Top-level host entries NOT copied into the workspace snapshot: VCS metadata,
# the venv, secrets (loaded from the real host .env in [6/9] instead), local
# data, caches, agent tooling, and the ***plain project itself.

set -u

UNRECOVERABLE_ERROR_EXIT_CODE=69
NO_TESTS_EXIT_CODE=1
SNAPSHOT_EXCLUDES=".git .venv .env crm.db .pytest_cache .tmp plain .claude .agents .opencode .plainwright"

banner() { printf '\n===== %s =====\n' "$1"; }

# ----- [1/9] Toolchain check ------------------------------------------------
banner "[1/9] Toolchain check"
# The conformance suite runs in its own isolated venv (it installs its own test
# dependencies, which must not pollute the host environment), but that venv is
# built (by prepare_environment_python.sh) from the HOST project's interpreter at $HOST_CODEBASE_ROOT/.venv - the
# one scripts/start.sh provisioned. The project's floor is Python >= 3.12 and
# any interpreter at or above it is fine; what is NOT fine is the tests running
# on a DIFFERENT interpreter than the host. Selecting one off PATH here did
# exactly that (PATH may offer a newer Python than the host venv was built
# with), so a test dependency could break on an interpreter the host never uses.
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
printf "Python interpreter: %s (host venv)\n" "$PYTHON_CMD"
"$PYTHON_CMD" --version

# ----- [2/9] Argument validation --------------------------------------------
banner "[2/9] Argument validation"
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

# ----- [3/9] Resolve paths --------------------------------------------------
banner "[3/9] Resolve paths"
# PLAIN_DIR / HOST_CODEBASE_ROOT were already resolved (and validated) in [1/9],
# because the host venv there is derived from them.
current_dir="$(pwd)"
ABS_BUILD_FOLDER="$(cd "$BUILD_FOLDER" && pwd)"
ABS_TESTS_FOLDER="$(cd "$TESTS_FOLDER" && pwd)"

printf "Invocation dir (current_dir):  %s\n" "$current_dir"
printf "Build folder (impl source):    %s\n" "$ABS_BUILD_FOLDER"
printf "Conformance tests source:      %s\n" "$ABS_TESTS_FOLDER"
printf "Host codebase root:            %s\n" "$HOST_CODEBASE_ROOT"

# The prepared environment - keep this derivation identical to
# prepare_environment_python.sh.
MODULE_NAME="$(basename "$(dirname "$ABS_BUILD_FOLDER")")"
PATH_HASH="$("$PYTHON_CMD" -c 'import hashlib, sys; print(hashlib.sha1(sys.argv[1].encode()).hexdigest()[:8])' "$ABS_BUILD_FOLDER")"
TMP_ROOT="${TMPDIR:-/tmp}"
PREPARED_ENV="${TMP_ROOT%/}/python_conformance_env_${MODULE_NAME}_${PATH_HASH}"
VENV_DIR="$PREPARED_ENV/.venv"
VENV_PY="$VENV_DIR/bin/python"
printf "Prepared env:                  %s\n" "$PREPARED_ENV"

if [ ! -x "$VENV_PY" ] || [ ! -f "$VENV_DIR/pyvenv.cfg" ] || [ ! -f "$PREPARED_ENV/.prepared" ]; then
    printf "Error: prepared environment missing or incomplete at %s.\n" "$PREPARED_ENV" >&2
    printf "       Run prepare_environment_python.sh %s first.\n" "$ABS_BUILD_FOLDER" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
fi

# ----- [4/9] Create the isolated workspace and snapshot the host -----------
banner "[4/9] Create workspace and snapshot host"
# The workspace lives in the system temp directory (an absolute path), not
# inside the project, so no build debris is left in the repo. mktemp makes the
# name unique per run; $2's basename only labels it (never concatenate the raw
# argument).
TMP_ROOT="${TMPDIR:-/tmp}"
WORKSPACE="$(mktemp -d "${TMP_ROOT%/}/python_conformance_$(basename "$ABS_TESTS_FOLDER").XXXXXX")" || {
    printf "Error: could not create a workspace in %s\n" "$TMP_ROOT" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}
trap 'rm -rf "$WORKSPACE"' EXIT
HOST_SNAPSHOT="$WORKSPACE/host"
WORKING_FOLDER="$WORKSPACE/conformance"
mkdir -p "$HOST_SNAPSHOT" "$WORKING_FOLDER"
printf "Workspace:     %s\n" "$WORKSPACE"
printf "Host snapshot: %s\n" "$HOST_SNAPSHOT"

shopt -s dotglob nullglob
for entry in "$HOST_CODEBASE_ROOT"/*; do
    name="$(basename "$entry")"
    case " $SNAPSHOT_EXCLUDES " in *" $name "*) continue ;; esac
    cp -R "$entry" "$HOST_SNAPSHOT"/ || {
        printf "Error: failed to copy %s into host snapshot %s\n" "$entry" "$HOST_SNAPSHOT" >&2
        exit $UNRECOVERABLE_ERROR_EXIT_CODE
    }
done
shopt -u dotglob nullglob

# ----- [5/9] Overlay generated implementation onto the host snapshot --------
# Mirrors the Java "mvn install from root with all code" step: put the freshly
# generated implementation where the conformance suite will import it from
# (the snapshot's src/). Scoped to the module's own integration package dir(s)
# of the snapshot only.
banner "[5/9] Overlay implementation onto host snapshot"
STAGED_ANY=0
for sub in src tests; do
    pkg_root="$ABS_BUILD_FOLDER/$sub/integrations"
    [ -d "$pkg_root" ] || continue
    for pkg in "$pkg_root"/*/; do
        [ -d "$pkg" ] || continue
        name="$(basename "$pkg")"
        rel="$sub/integrations/$name"
        dest="$HOST_SNAPSHOT/$rel"
        printf "Staging %s into host snapshot\n" "$rel"
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

# ----- [6/9] Provider credentials (live run) --------------------------------
# A .env at the project root is REQUIRED. This step only guarantees the file
# exists and loads it into the environment - it is integration-agnostic and
# never validates any specific secret by name. Each integration validates the
# credentials it needs at call time; the live run surfaces a missing one.
banner "[6/9] Provider credentials"
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

# ----- [7/9] Stage conformance tests into the workspace ---------------------
banner "[7/9] Stage conformance tests into working folder"
# The working folder is freshly created inside this run's workspace, so no
# stale files from a previous run can be collected alongside this run's tests.
printf "Working folder: %s\n" "$WORKING_FOLDER"
cp -R "$ABS_TESTS_FOLDER"/. "$WORKING_FOLDER"/

# ----- [8/9] Attach to the prepared venv ------------------------------------
banner "[8/9] Attach to prepared venv"
# Host requirements and pytest were installed by prepare_environment_python.sh.
# Only the suite's own deps vary per functional spec; they go into the prepared
# venv, where pip skips anything already satisfied.
start_time=$(date +%s)
printf "Using prepared venv %s\n" "$VENV_DIR"
if [ -f "$WORKING_FOLDER/requirements.txt" ]; then
    printf "Installing conformance-suite requirements\n"
    "$VENV_PY" -m pip install -r "$WORKING_FOLDER/requirements.txt" || exit $?
fi

end_time=$(date +%s)
printf "Requirements setup completed in %s seconds\n" "$((end_time - start_time))"

# ----- [9/9] Run conformance tests LIVE, impl from the host snapshot --------
banner "[9/9] Run conformance tests (live provider)"
cd "$WORKING_FOLDER" 2>/dev/null || {
    printf "Error: could not enter working folder %s\n" "$WORKING_FOLDER" >&2
    exit $UNRECOVERABLE_ERROR_EXIT_CODE
}
# PYTHONPATH=snapshot => `from src.integrations.<name> import ...` resolves to
# the implementation code in this run's host snapshot, never the real host tree.
export PYTHONPATH="$HOST_SNAPSHOT${PYTHONPATH:+:$PYTHONPATH}"
TEST_CMD=("$VENV_PY" -m pytest \
          -vv \
          -rA \
          -l \
          -s \
          --tb=long \
          --durations=0 \
          --color=yes \
          -o log_cli=true \
          --log-cli-level=DEBUG \
          --import-mode=importlib \
          -p no:cacheprovider \
          --basetemp="$WORKSPACE/.pytest_tmp" \
          "$WORKING_FOLDER")

printf "Now in:       %s\n" "$(pwd)"
printf "PYTHONPATH:   %s\n" "$PYTHONPATH"
printf "Test command: %s\n\n" "${TEST_CMD[*]}"

output=$("${TEST_CMD[@]}" 2>&1)
exit_code=$?
echo "$output"

# The verbose flags above (-s, -rA, log_cli=DEBUG) let test output and live log
# lines land in $output - any of which could contain strings like "3 failed" or
# "no tests ran". So DO NOT grep the whole stream for the verdict. Instead pull
# out pytest's final summary bar (the "===== N passed/failed ... in Xs ====="
# line, always last), strip ANSI color, and judge only that line.
summary_line=$(printf '%s\n' "$output" \
    | sed 's/\x1b\[[0-9;]*m//g' \
    | grep -E '^=+.*=+$' \
    | tail -n 1)

# pytest exit 5 == no tests collected. Strict no-tests guard.
if [ "$exit_code" -eq 5 ] || printf '%s' "$summary_line" | grep -qiE "no tests ran"; then
    printf "\nError: No conformance tests discovered in %s.\n" "$WORKING_FOLDER" >&2
    printf "Failure context: cwd=%s current_dir=%s tests=%s\n" \
        "$(pwd)" "$current_dir" "$ABS_TESTS_FOLDER" >&2
    exit $NO_TESTS_EXIT_CODE
fi

# Strict pass criteria: clean exit AND zero failures / errors / skipped.
if [ "$exit_code" -ne 0 ] || printf '%s' "$summary_line" | grep -qiE "[0-9]+ (failed|error|skipped|xfailed|xpassed)"; then
    printf "\nError: conformance run did not pass cleanly (exit %s).\n" "$exit_code" >&2
    printf "All conformance tests must pass with zero failures, errors, and skips.\n" >&2
    printf "Failure context: cwd=%s current_dir=%s tests=%s PYTHONPATH=%s\n" \
        "$(pwd)" "$current_dir" "$ABS_TESTS_FOLDER" "$PYTHONPATH" >&2
    [ "$exit_code" -eq 0 ] && exit_code=1
    exit "$exit_code"
fi

printf "\nConformance run passed.\n"
printf "Summary: variant=activate-only cmd='%s' exit=%s current_dir=%s working_folder=%s\n" \
    "${TEST_CMD[*]}" "$exit_code" "$current_dir" "$WORKING_FOLDER"
exit "$exit_code"

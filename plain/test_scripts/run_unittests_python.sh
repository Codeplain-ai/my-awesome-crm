#!/bin/bash
# Unit-test runner for an EMBEDDED CRM integration plug-in.
#
# The integration's generated code is consumed in-process by the host CRM
# backend, so unit tests must run against the host's source layout. To let
# several renders run side by side without clobbering each other (or the real
# host tree), every run works in its OWN isolated workspace in the system temp
# directory: the host codebase is snapshotted into it, the renderer's build
# folder ($1) is overlaid onto the snapshot at the module's package path
# (src/integrations/<name>/ and tests/integrations/<name>/), and pytest runs
# from the snapshot root scoped to the staged integration package(s). The real
# host tree is never written to, and the workspace is removed on exit.
#
# Tests run on the host project's OWN virtual environment at
# $HOST_CODEBASE_ROOT/.venv (the one scripts/start.sh provisions), so unit
# tests use the exact interpreter and installed dependencies the host uses.
# The venv is only read, never modified, so concurrent runs can share it.
#
#   Usage: run_unittests_python.sh <source_build_folder>
#
# The host codebase root defaults to the parent of the plain/ folder and can
# be overridden with the HOST_CODEBASE_ROOT environment variable.

set -u

# Top-level host entries NOT copied into the workspace snapshot: VCS metadata,
# the venv (used in place), secrets, local data, caches, agent tooling, and the
# ***plain project itself (plain/ holds generated copies of the tests that
# would collide on module names).
SNAPSHOT_EXCLUDES=".git .venv .env crm.db .pytest_cache .tmp plain .claude .agents .opencode .plainwright"

# Step 1 - argument validation
if [ $# -ne 1 ]; then
    echo "Usage: $0 <source_build_folder>" >&2
    echo "       HOST_CODEBASE_ROOT (env) overrides the host codebase root" >&2
    echo "       (defaults to the parent of the plain/ folder)." >&2
    exit 1
fi

SOURCE_FOLDER="$1"

if [ ! -d "$SOURCE_FOLDER" ]; then
    echo "Error: source build folder not found: $SOURCE_FOLDER" >&2
    exit 2
fi

# Step 2 - resolve the host codebase root (the embedded integration's host)
PLAIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOST_CODEBASE_ROOT="${HOST_CODEBASE_ROOT:-$(cd "$PLAIN_DIR/.." && pwd)}"

if [ ! -d "$HOST_CODEBASE_ROOT" ]; then
    echo "Error: host codebase root not found: $HOST_CODEBASE_ROOT" >&2
    exit 2
fi
echo "Host codebase root: $HOST_CODEBASE_ROOT"

# Step 3 - dependency environment. Use the host project's OWN virtual
# environment at $HOST_CODEBASE_ROOT/.venv, which is expected to already be
# provisioned (e.g. by scripts/start.sh). This script never installs anything -
# it only verifies the environment and fails fast with exit 69 if it is not
# ready. A valid venv requires both bin/python and the pyvenv.cfg marker (a
# bare python symlink with no pyvenv.cfg is NOT a venv).
VENV_DIR="$HOST_CODEBASE_ROOT/.venv"
VENV_PY="$VENV_DIR/bin/python"

if [ ! -x "$VENV_PY" ] || [ ! -f "$VENV_DIR/pyvenv.cfg" ]; then
    echo "Error: host virtual environment not found or invalid at $VENV_DIR." >&2
    echo "       Provision it first, e.g. ./scripts/start.sh (or" >&2
    echo "       python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)." >&2
    exit 69
fi

VENV_PY_VERSION=$("$VENV_PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "unknown")
echo "Using host venv $VENV_DIR (Python $VENV_PY_VERSION)"

# Verify pytest is available in the venv. Do NOT install anything - a missing
# dependency is a provisioning error the user must resolve (re-run
# scripts/start.sh), reported as exit 69. Missing host runtime packages are left
# to surface as import errors from the tests themselves.
if ! "$VENV_PY" -m pytest --version >/dev/null 2>&1; then
    echo "Error: pytest is not installed in host venv $VENV_DIR." >&2
    echo "       Install the project's test dependencies into .venv and retry." >&2
    exit 69
fi

# Step 4 - create this run's isolated workspace (unique per run, so concurrent
# renders never share it) and snapshot the host codebase into it.
TMP_ROOT="${TMPDIR:-/tmp}"
WORKSPACE="$(mktemp -d "${TMP_ROOT%/}/python_unittests.XXXXXX")" || {
    echo "Error: could not create a workspace in $TMP_ROOT" >&2
    exit 69
}
trap 'rm -rf "$WORKSPACE"' EXIT
echo "Workspace: $WORKSPACE"

echo "Snapshotting host codebase into workspace"
shopt -s dotglob nullglob
for entry in "$HOST_CODEBASE_ROOT"/*; do
    name="$(basename "$entry")"
    case " $SNAPSHOT_EXCLUDES " in *" $name "*) continue ;; esac
    cp -R "$entry" "$WORKSPACE"/ || {
        echo "Error: failed to copy $entry into workspace $WORKSPACE" >&2
        exit 69
    }
done
shopt -u dotglob nullglob

# Step 5 - overlay the generated integration package(s) onto the snapshot.
# The build only ships integration package dirs (src/integrations/<name>/ and
# tests/integrations/<name>/), so destructive ops are scoped to those leaf dirs
# of the workspace only.
TEST_TARGETS=()
STAGED_ANY=0

for sub in src tests; do
    pkg_root="$SOURCE_FOLDER/$sub/integrations"
    [ -d "$pkg_root" ] || continue
    for pkg in "$pkg_root"/*/; do
        [ -d "$pkg" ] || continue
        name="$(basename "$pkg")"
        rel="$sub/integrations/$name"
        dest="$WORKSPACE/$rel"

        echo "Staging $rel into workspace"
        rm -rf "$dest"
        mkdir -p "$dest"
        cp -R "$pkg"/. "$dest"/
        STAGED_ANY=1

        if [ "$sub" = "tests" ]; then
            TEST_TARGETS+=("$rel")
        fi
    done
done

if [ "$STAGED_ANY" -ne 1 ]; then
    echo "Error: build folder ships no src/integrations/<name>/ packages: $SOURCE_FOLDER" >&2
    exit 2
fi

if [ "${#TEST_TARGETS[@]}" -eq 0 ]; then
    echo "Error: build folder ships no tests/integrations/<name>/ packages to run." >&2
    exit 1
fi

# Step 6 - run pytest from the workspace root so `from src.integrations.<name> ...`
# resolves against the snapshot's host layout, scoped to the staged package(s).
cd "$WORKSPACE" || {
    echo "Error: could not enter workspace $WORKSPACE" >&2
    exit 69
}

# Activate the host venv so the tests run inside it, then invoke pytest.
# (The activate script is not written for `set -u`, so relax nounset around it.)
set +u
# shellcheck disable=SC1090,SC1091
. "$VENV_DIR/bin/activate"
set -u

# --basetemp keeps pytest's tmp_path dirs inside the workspace rather than the
# per-user directory pytest otherwise shares (and prunes) across runs.
echo "Running pytest in $WORKSPACE for: ${TEST_TARGETS[*]}"
PYTHONPATH="$WORKSPACE" python -m pytest \
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
    --basetemp="$WORKSPACE/.pytest_tmp" \
    "${TEST_TARGETS[@]}"
exit $?

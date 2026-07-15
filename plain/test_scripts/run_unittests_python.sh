#!/bin/bash
# Unit-test runner for an EMBEDDED CRM integration plug-in.
#
# The integration's generated code is consumed in-process by the host CRM
# backend, so unit tests must run against the host's source layout - not a
# detached copy. This script overlays the renderer's build folder ($1) onto
# the host codebase at the module's package path (src/integrations/<name>/
# and tests/integrations/<name>/), then runs pytest from the host root scoped
# to the staged integration package(s).
#
#   Usage: run_unittests_python.sh <source_build_folder>
#
# The host codebase root defaults to the parent of the plain/ folder and can
# be overridden with the HOST_CODEBASE_ROOT environment variable.

set -u

# Step 1 - toolchain check. Any Python >= 3.12 is accepted (version-agnostic).
# Each candidate is version-checked, not just probed for existence, so a launcher
# aliased to an older Python (e.g. python3 -> 3.9) is skipped rather than wrongly
# selected. Newer launchers are preferred over older ones.
MIN_PY_MAJOR=3
MIN_PY_MINOR=12
py_meets_min() {
    "$1" -c "import sys; sys.exit(0 if sys.version_info[:2] >= ($MIN_PY_MAJOR, $MIN_PY_MINOR) else 1)" 2>/dev/null
}
PY=""
for cand in python3.15 python3.14 python3.13 python3.12 python3 python; do
    if command -v "$cand" >/dev/null 2>&1 && py_meets_min "$cand"; then
        PY="$cand"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "Error: a Python >= $MIN_PY_MAJOR.$MIN_PY_MINOR interpreter is required but none was found on PATH." >&2
    exit 69
fi

PY_VERSION=$($PY -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "unknown")
echo "Using $PY ($PY_VERSION)"

# Step 2 - argument validation
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

# Step 3 - resolve the host codebase root (the embedded integration's host)
PLAIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOST_CODEBASE_ROOT="${HOST_CODEBASE_ROOT:-$(cd "$PLAIN_DIR/.." && pwd)}"

if [ ! -d "$HOST_CODEBASE_ROOT" ]; then
    echo "Error: host codebase root not found: $HOST_CODEBASE_ROOT" >&2
    exit 2
fi
echo "Host codebase root: $HOST_CODEBASE_ROOT"

# Step 4 - overlay the generated integration package(s) into the host source tree.
# The build only ships integration package dirs (src/integrations/<name>/ and
# tests/integrations/<name>/), so destructive ops are scoped to those leaf dirs
# only - never the host's top-level src/ or tests/.
TEST_TARGETS=()
STAGED_ANY=0

for sub in src tests; do
    pkg_root="$SOURCE_FOLDER/$sub/integrations"
    [ -d "$pkg_root" ] || continue
    for pkg in "$pkg_root"/*/; do
        [ -d "$pkg" ] || continue
        name="$(basename "$pkg")"
        rel="$sub/integrations/$name"
        dest="$HOST_CODEBASE_ROOT/$rel"

        echo "Staging $rel into host"
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

# Step 5 - dependency environment. Keep the host source tree and the project
# clean by housing the venv in the system temp directory (an absolute path)
# rather than inside the repo. The host-root basename keeps the path stable
# across runs so the venv is reused.
VENV_DIR="/tmp/python_unittests_$(basename "$HOST_CODEBASE_ROOT")/venv"
CREATED_VENV=0
if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Creating venv at $VENV_DIR"
    $PY -m venv "$VENV_DIR" || exit $?
    CREATED_VENV=1
fi
VENV_PY="$VENV_DIR/bin/python"

# Some hosts create a venv without pip (a stripped Python where ensurepip is
# missing, or an incomplete system python3-venv package). pip must be present
# inside the venv; try to bootstrap it with ensurepip, and if it still is not
# available, fail fast with 69 rather than dying later with an opaque error.
if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
    echo "pip not found in venv; attempting to bootstrap it with ensurepip" >&2
    "$VENV_PY" -m ensurepip --upgrade --default-pip >/dev/null 2>&1
fi
if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
    echo "Error: pip is not available in the venv at $VENV_DIR and could not be bootstrapped." >&2
    echo "       Install the platform's Python venv/pip support (e.g. the python3-venv package) and retry." >&2
    exit 69
fi
if [ "$CREATED_VENV" -eq 1 ]; then
    "$VENV_PY" -m pip install --upgrade pip >/dev/null || exit $?
fi

if [ -f "$HOST_CODEBASE_ROOT/requirements.txt" ]; then
    "$VENV_PY" -m pip install -r "$HOST_CODEBASE_ROOT/requirements.txt" || exit $?
elif [ -f "$HOST_CODEBASE_ROOT/pyproject.toml" ]; then
    "$VENV_PY" -m pip install -e "$HOST_CODEBASE_ROOT" || exit $?
else
    echo "Error: no requirements.txt or pyproject.toml in $HOST_CODEBASE_ROOT" >&2
    exit 69
fi

# pytest is needed to run the suite even if the host does not declare it.
"$VENV_PY" -m pip install pytest >/dev/null || exit $?

# Step 6 - run pytest from the host root so `from src.integrations.<name> ...`
# resolves against the host layout, scoped to the staged integration package(s).
cd "$HOST_CODEBASE_ROOT" || {
    echo "Error: could not enter host codebase root $HOST_CODEBASE_ROOT" >&2
    exit 2
}

echo "Running pytest in $HOST_CODEBASE_ROOT for: ${TEST_TARGETS[*]}"
PYTHONPATH="$HOST_CODEBASE_ROOT" "$VENV_DIR/bin/pytest" \
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
    "${TEST_TARGETS[@]}"
exit $?

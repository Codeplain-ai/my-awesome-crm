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
# Tests run inside the host project's OWN virtual environment at
# $HOST_CODEBASE_ROOT/.venv (the one scripts/start.sh provisions), so unit
# tests use the exact interpreter and installed dependencies the host uses.
# The script does not create a throwaway venv.
#
#   Usage: run_unittests_python.sh <source_build_folder>
#
# The host codebase root defaults to the parent of the plain/ folder and can
# be overridden with the HOST_CODEBASE_ROOT environment variable.

set -u

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

# Step 3 - overlay the generated integration package(s) into the host source tree.
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

# Step 4 - dependency environment. Use the host project's OWN virtual
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

# Verify every host requirement AND pytest are already installed in the venv.
# Do NOT install anything - a missing dependency is a provisioning error the
# user must resolve (re-run scripts/start.sh), reported as exit 69. The check
# reads requirements.txt and confirms each distribution is present via
# importlib.metadata (network-free; matches PyPI/requirements distribution names).
if [ -f "$HOST_CODEBASE_ROOT/requirements.txt" ]; then
    if ! "$VENV_PY" - "$HOST_CODEBASE_ROOT/requirements.txt" <<'PY'
import re, sys
import importlib.metadata as md
missing = []
for raw in open(sys.argv[1]):
    line = raw.split("#", 1)[0].strip()
    if not line or line.startswith("-"):
        continue
    name = re.split(r"[<>=!~;\[ ]", line, 1)[0].strip()
    if not name:
        continue
    try:
        md.version(name)
    except md.PackageNotFoundError:
        missing.append(name)
if missing:
    sys.stderr.write("Missing from venv: " + ", ".join(missing) + "\n")
    sys.exit(1)
PY
    then
        echo "Error: host venv $VENV_DIR is missing packages from requirements.txt." >&2
        echo "       Provision it first, e.g. ./scripts/start.sh." >&2
        exit 69
    fi
fi
if ! "$VENV_PY" -m pytest --version >/dev/null 2>&1; then
    echo "Error: pytest is not installed in host venv $VENV_DIR." >&2
    echo "       Install the project's test dependencies into .venv and retry." >&2
    exit 69
fi

# Step 5 - run pytest from the host root so `from src.integrations.<name> ...`
# resolves against the host layout, scoped to the staged integration package(s).
cd "$HOST_CODEBASE_ROOT" || {
    echo "Error: could not enter host codebase root $HOST_CODEBASE_ROOT" >&2
    exit 2
}

# Activate the host venv so the tests run inside it, then invoke pytest.
# (The activate script is not written for `set -u`, so relax nounset around it.)
set +u
# shellcheck disable=SC1090,SC1091
. "$VENV_DIR/bin/activate"
set -u

echo "Running pytest in $HOST_CODEBASE_ROOT for: ${TEST_TARGETS[*]}"
PYTHONPATH="$HOST_CODEBASE_ROOT" python -m pytest \
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

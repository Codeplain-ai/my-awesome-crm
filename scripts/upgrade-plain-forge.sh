#!/bin/bash
# Upgrade the vendored plain-forge installs, then apply this repo's local tweaks.
#
# 1. Runs `npx plain-forge@latest update`, which refreshes every plain-forge
#    install in the repo (.agents/, .claude/, .opencode/) and in $HOME.
# 2. In each of .agents/, .claude/, .opencode/:
#    - removes the render-spec (pyro) skill — this repo renders with codeplain;
#    - removes the "First, confirm the rules about to be loaded are current"
#      paragraphs and the "Skip the check …" paragraph from
#      load-plain-reference/SKILL.md, so the skill no longer invokes
#      check-forge-version or asks to run `npx plain-forge update`.
#
# The manifests are left as plain-forge wrote them. Review and commit by hand.
#
#   Usage: ./scripts/upgrade-plain-forge.sh [plain-forge update options]
#          e.g. ./scripts/upgrade-plain-forge.sh --yes

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> npx plain-forge@latest update $*"
npx --yes plain-forge@latest update "$@"

START='**First, confirm the rules about to be loaded are current.**'
END='later behaves unexpectedly.'
SKIP='Skip the check on later invocations'
status=0

for dir in .agents .claude .opencode; do
    if [ ! -d "$dir/.plain-forge" ]; then
        echo "==> $dir: no plain-forge install, skipped"
        continue
    fi

    if [ -d "$dir/skills/render-spec" ]; then
        rm -rf "$dir/skills/render-spec"
        echo "==> $dir: removed skills/render-spec"
    fi

    skill="$dir/skills/load-plain-reference/SKILL.md"
    before="$(cat "$skill")"
    # Drop the paragraphs from START through the line ending in END, and the
    # paragraph starting with SKIP, each with the blank line after it.
    START="$START" END="$END" SKIP="$SKIP" perl -0777 -i -pe '
        s/^\Q$ENV{START}\E.*?\Q$ENV{END}\E\n\n//ms;
        s/^\Q$ENV{SKIP}\E.*?\n\n//ms;
    ' "$skill"
    if grep -qF -e "check-forge-version" -e "$SKIP" "$skill"; then
        echo "!! $skill: version-check wording changed upstream, edit it by hand" >&2
        status=1
    elif [ "$before" != "$(cat "$skill")" ]; then
        echo "==> $dir: removed version-check paragraphs from load-plain-reference"
    else
        echo "==> $dir: load-plain-reference already has no version check"
    fi
done

exit "$status"

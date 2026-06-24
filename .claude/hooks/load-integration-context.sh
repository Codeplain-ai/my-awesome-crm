#!/usr/bin/env bash
# SessionStart hook for my-awesome-crm.
#
# Emits ONLY the small, DYNAMIC piece of startup context: the list of providers
# that already exist, so a new integration never duplicates one.
#
# The heavy, static authoring context (the ***plain language reference, the
# salesforce.plain exemplar, the crm_common / integration_testing templates, the
# host schemas.py / ingest.py / requirements.txt, plain/config.yaml, and the
# salesforce openapi.yaml + contact-mapping.md) is NOT emitted here. Claude Code
# caps each hook output string at ~10K chars and persists the overflow to a file
# instead of injecting it — which silently truncated the old all-in-one bundle.
# That content now loads, uncapped, via CLAUDE.md `@imports` (see CLAUDE.md §
# "Auto-loaded startup context"). Keep this hook tiny and under the cap.
#
# Resolve the repo root relative to THIS script (.claude/hooks/), never $PWD.

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

bundle="$(
  printf '# my-awesome-crm — existing integrations (SessionStart hook)\n'
  printf 'The full ***plain reference + exemplar/host context is loaded via CLAUDE.md @imports.\n'
  printf 'This hook adds only the live provider list below — do NOT duplicate these providers.\n'

  printf '\nRendered plug-ins under src/integrations/:\n'
  ls -1 "$ROOT/src/integrations" 2>/dev/null | grep -v '^_' | sed 's/^/  - /' || true

  printf 'Root .plain modules under plain/:\n'
  ( ls -1 "$ROOT/plain"/*.plain 2>/dev/null | xargs -n1 basename | sed 's/^/  - /' ) || true
)"

# Encode as SessionStart additionalContext. Prefer jq; fall back to python3 (always present
# in this Python project) so the hook never silently fails to inject.
if command -v jq >/dev/null 2>&1; then
  jq -n --arg ctx "$bundle" \
    '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
else
  CTX="$bundle" python3 -c 'import json,os; print(json.dumps({"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":os.environ["CTX"]}}))'
fi

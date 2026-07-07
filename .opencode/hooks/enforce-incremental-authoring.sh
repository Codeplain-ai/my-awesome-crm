#!/usr/bin/env bash
# UserPromptSubmit hook for my-awesome-crm.
#
# Forcing function for the "write the spec after EACH answer" rule (CLAUDE.md §
# "Ask the user before authoring"). That rule fights the model's batch-then-write
# default and has no mechanical gate, so it silently gets dropped: the agent
# answers all the questions, then writes once at the end.
#
# This hook reinstates the missing per-turn checkpoint. It fires on every user
# prompt, but only injects a reminder when an integration is actually mid-authoring
# — defined as a top-level plain/*.plain module that was modified recently AND is
# still missing at least one of the four required spec sections. That window is
# exactly Phase 1 (the ask -> answer -> write loop). Once all four sections exist,
# or the file is stale, the hook stays silent so it never nags unrelated sessions.
#
# Resolve the repo root relative to THIS script (.claude/hooks/), never $PWD.

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PLAIN_DIR="$ROOT/plain"

# Only consider files touched in the last 12h, so an abandoned half-built module
# from a long-past session does not nag forever.
RECENCY_MIN=720

incomplete=""
if [ -d "$PLAIN_DIR" ]; then
  for f in "$PLAIN_DIR"/*.plain; do
    [ -e "$f" ] || continue

    # recency guard
    [ -n "$(find "$f" -mmin -"$RECENCY_MIN" 2>/dev/null)" ] || continue

    # missing any of the four required sections => mid-authoring
    missing=""
    grep -qF '***definitions***'        "$f" || missing="1"
    grep -qF '***implementation reqs***' "$f" || missing="1"
    grep -qF '***test reqs***'          "$f" || missing="1"
    grep -qF '***functional specs***'   "$f" || missing="1"

    [ -n "$missing" ] && incomplete="$incomplete $(basename "$f")"
  done
fi

# Nothing mid-authoring -> stay silent.
[ -z "$incomplete" ] && exit 0

reminder="$(
  printf '⚠ Integration authoring in progress — incomplete module(s):%s\n\n' "$incomplete"
  printf 'PER-QUESTION WRITE RULE (CLAUDE.md § "Ask the user before authoring"):\n'
  printf 'If your previous turn received an answer to an authoring question, you MUST fold\n'
  printf 'that answer into the .plain module (and its linked resources) with a small Edit\n'
  printf 'BEFORE you ask the next question. Writing after each answer is a hard rule inside\n'
  printf 'the question loop — it is NOT a drafting phase you do after the interview.\n\n'
  printf 'Workflow: Phase 1 = repeat {ask one question -> user answers -> write specs}.\n'
  printf 'Phase 2 = fetch/web-search/live-probe the API. Phase 3 = correct specs from\n'
  printf 'findings. Phase 4 = review. The write in Phase 1 is a precondition for the next\n'
  printf 'question, not optional.\n'
)"

if command -v jq >/dev/null 2>&1; then
  jq -n --arg ctx "$reminder" \
    '{hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $ctx}}'
else
  CTX="$reminder" python3 -c 'import json,os; print(json.dumps({"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":os.environ["CTX"]}}))'
fi

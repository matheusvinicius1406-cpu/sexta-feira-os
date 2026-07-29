#!/usr/bin/env bash
# Hand one implementation step to the OpenAI Codex CLI on the current branch.
# The Architect (Claude) writes the brief; Codex implements; Claude reviews.
# Usage: scripts/ai/codex-task.sh "<task brief>"   OR   scripts/ai/codex-task.sh -f brief.md
set -euo pipefail

BRANCH=$(git rev-parse --abbrev-ref HEAD)
case "$BRANCH" in
  main|develop)
    echo "refusing to run Codex on protected branch '$BRANCH'." >&2
    echo "create a branch first: scripts/ai/new-branch.sh codex \"<slug>\"" >&2
    exit 2 ;;
esac

if ! command -v codex >/dev/null 2>&1; then
  cat >&2 <<'EOF'
OpenAI Codex CLI is not installed. Install it, then re-run:
  npm install -g @openai/codex      # or: brew install codex
  codex login                       # authenticate once
See docs/AI_FACTORY.md for the full setup.
EOF
  exit 127
fi

if [ "${1:-}" = "-f" ]; then
  [ -n "${2:-}" ] || { echo "usage: $0 -f <brief-file>" >&2; exit 2; }
  BRIEF=$(cat "$2")
else
  BRIEF="${1:-}"
fi
[ -n "$BRIEF" ] || { echo "usage: $0 \"<task brief>\" | -f <brief-file>" >&2; exit 2; }

# Prepend the shared contract so Codex respects the same rules as Claude.
PROMPT="You are the Senior Implementation Engineer. Follow AGENTS.md strictly.
Implement ONLY the task below on the current branch ($BRANCH). Add/adjust tests.
Do not touch main/develop, do not merge, do not change architecture beyond the task.

TASK:
$BRIEF"

echo "==> running Codex on branch $BRANCH"
# --full-auto lets Codex edit files and run commands in the workspace sandbox;
# it stops at file changes — committing/merging stays with the Architect.
codex exec --full-auto "$PROMPT"

echo
echo "Codex finished. Review its changes before committing:"
echo "  git diff"
echo "  scripts/ai/test-all.sh auto"
echo "Then commit on this branch and run /ai-review. Do NOT merge to main yet."

#!/usr/bin/env bash
# Report the state of the AI factory workflow for the current branch.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "branch:        $BRANCH"

case "$BRANCH" in
  main|develop) echo "protected:     YES — do not commit work here directly" ;;
  *)            echo "protected:     no (working branch)" ;;
esac

DIRTY=$(git status --porcelain | wc -l | tr -d ' ')
echo "uncommitted:   $DIRTY file(s)"

AHEAD=$(git rev-list --count main..HEAD 2>/dev/null || echo "?")
echo "commits ahead of main: $AHEAD"

echo
echo "diff vs main:"
git diff --stat main...HEAD 2>/dev/null | tail -n 1 || echo "  (no diff / main unavailable)"

echo
echo "languages touched:"
CHANGED=$(git diff --name-only main...HEAD 2>/dev/null)
grep -q '^backend-core/'   <<<"$CHANGED" && echo "  - Python (backend-core)"
grep -qE '^(src/|Cargo\.)' <<<"$CHANGED" && echo "  - Rust"
grep -q '^mobile-android/'  <<<"$CHANGED" && echo "  - Android"
[ -z "$CHANGED" ] && echo "  (none vs main)"

echo
echo "next step: plan → code → test → review → merge  (see AGENTS.md)"

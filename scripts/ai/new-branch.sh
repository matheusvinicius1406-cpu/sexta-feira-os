#!/usr/bin/env bash
# Create an isolated working branch for the AI factory flow.
# Usage: scripts/ai/new-branch.sh <feature|codex|experiment> "<slug>"
set -euo pipefail

PREFIX="${1:-}"
SLUG="${2:-}"

case "$PREFIX" in
  feature|codex|experiment) ;;
  *) echo "usage: $0 <feature|codex|experiment> \"<slug>\"" >&2; exit 2 ;;
esac
if [ -z "$SLUG" ]; then
  echo "error: slug is required" >&2; exit 2
fi

# Normalize slug: lowercase, spaces/underscores -> hyphens, strip junk.
CLEAN=$(printf '%s' "$SLUG" | tr '[:upper:]' '[:lower:]' | tr ' _' '--' | tr -cd 'a-z0-9-')
BRANCH="${PREFIX}/${CLEAN}"

# Base off an up-to-date main (fall back gracefully if offline).
git fetch origin main --quiet 2>/dev/null || true
BASE=main
git rev-parse --verify --quiet origin/main >/dev/null && BASE=origin/main

if git rev-parse --verify --quiet "$BRANCH" >/dev/null; then
  echo "branch $BRANCH already exists — checking it out"
  git checkout "$BRANCH"
else
  git checkout -b "$BRANCH" "$BASE"
fi

echo "on branch: $(git rev-parse --abbrev-ref HEAD) (based on $BASE)"

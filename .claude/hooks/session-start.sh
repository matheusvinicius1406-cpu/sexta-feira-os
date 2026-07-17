#!/bin/bash
# SessionStart hook for Claude Code on the web.
# Installs the backend-core Python deps (venv + ruff, mirroring `make setup`)
# and warms the Rust dependency cache so tests and linters run out of the box.
set -euo pipefail

# Only needed in remote (web) sessions; local machines are assumed set up.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# --- Python kernel (backend-core) ---
if [ ! -x backend-core/.venv/bin/python ]; then
  python3 -m venv backend-core/.venv
fi
backend-core/.venv/bin/pip install -q -U pip -r backend-core/requirements.txt ruff

# --- Rust perception layer (root crate) ---
if command -v cargo >/dev/null 2>&1; then
  cargo fetch --quiet || true
fi

echo "session-start: backend-core venv ready, cargo deps fetched"

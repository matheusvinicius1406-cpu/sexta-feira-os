#!/usr/bin/env bash
# Run the test suites relevant to the current work.
# Usage: scripts/ai/test-all.sh [python|rust|android|all|auto]   (default: auto)
set -uo pipefail

SCOPE="${1:-auto}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

FAIL=0
run() { echo; echo "==> $1"; shift; "$@"; local rc=$?; [ $rc -ne 0 ] && FAIL=1; return 0; }

want() {
  case "$SCOPE" in
    all) return 0 ;;
    "$1") return 0 ;;
    auto)
      local changed
      changed=$(git diff --name-only main...HEAD 2>/dev/null; git diff --name-only 2>/dev/null)
      case "$1" in
        python)  grep -q '^backend-core/' <<<"$changed" ;;
        rust)    grep -qE '^(src/|Cargo\.)' <<<"$changed" ;;
        android) grep -q '^mobile-android/' <<<"$changed" ;;
      esac ;;
    *) return 1 ;;
  esac
}

# Python kernel
if want python; then
  PY=backend-core/.venv/bin/python
  [ -x "$PY" ] || PY=backend-core/.venv/Scripts/python
  if [ -x "$PY" ]; then
    run "ruff (backend-core)" bash -c "cd backend-core && ./$( [ -x .venv/bin/ruff ] && echo .venv/bin/ruff || echo .venv/Scripts/ruff ) check app tests"
    run "pytest (backend-core)" bash -c "cd backend-core && '$ROOT/$PY' -m pytest -q"
  else
    echo "!! backend-core venv missing — run 'make setup'"; FAIL=1
  fi
fi

# Rust
if want rust; then
  if command -v cargo >/dev/null 2>&1; then
    run "cargo check" cargo check --all-targets
    run "cargo test" cargo test --all-targets
  else
    echo "!! cargo not installed — skipping Rust"
  fi
fi

# Android
if want android; then
  if [ -x mobile-android/gradlew ]; then
    run "gradle testDebug" bash -c "cd mobile-android && ./gradlew testDebug --console=plain"
  else
    echo "!! mobile-android/gradlew missing — skipping Android"
  fi
fi

echo
if [ $FAIL -eq 0 ]; then echo "ALL TESTS PASSED (scope: $SCOPE)"; else echo "TESTS FAILED (scope: $SCOPE)"; fi
exit $FAIL

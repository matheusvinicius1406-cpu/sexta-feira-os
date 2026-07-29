---
description: Run the test suites relevant to the current changes (Python / Rust / Android)
argument-hint: [python | rust | android | all — defaults to auto-detect from diff]
---

Run tests for scope: ${ARGUMENTS:-auto}.

Use `scripts/ai/test-all.sh ${ARGUMENTS:-auto}`. In `auto` mode it detects which languages the current diff touches and runs only those suites:
- Python kernel: `ruff check` + `pytest` (in `backend-core/`)
- Rust: `cargo check --all-targets` + `cargo test --all-targets`
- Android: `./gradlew testDebug` (in `mobile-android/`)

Report pass/fail per suite with the failing output if any. Do not "fix" failures silently — if something fails, summarize the root cause and recommend the `/ai-code` follow-up. State plainly whether everything passed.

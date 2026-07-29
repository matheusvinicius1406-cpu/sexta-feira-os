---
description: Report the state of the AI factory workflow — branch, diff, pending review, CI
---

Give me a status report of the current development state. Run `scripts/ai/status.sh` and summarize:

- Current branch and whether it's a protected branch (`main`/`develop` should have no direct work).
- Uncommitted changes and unpushed commits.
- Diff size vs `main` (files changed, +/- lines) and which languages are touched.
- Whether this branch has passed `/ai-review` yet (has it been reviewed/approved?).
- Any obvious next step in the flow: plan → code → review → merge.

Keep it to a short, scannable summary I can act on.

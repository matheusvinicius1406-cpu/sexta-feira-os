---
description: Hand one planned step to the implementation engineer (Codex CLI or Claude) on its own branch
argument-hint: <what to implement — one PR-sized step>
---

Implement this step on an isolated branch. Task:

> $ARGUMENTS

Follow the workflow in `AGENTS.md`:

1. **Branch**: create the working branch with `scripts/ai/new-branch.sh codex "<short-slug>"` (or `feature`/`experiment` prefix as appropriate). Never work on `main` or `develop`.
2. **Implement**: write the code for exactly this step — nothing more. Match the architect's plan and the surrounding code's style. If the OpenAI Codex CLI is available and I asked for Codex, generate the task brief and run it via `scripts/ai/codex-task.sh`; otherwise implement it directly.
3. **Tests**: add/update tests that prove the step works. Run the relevant suite with `scripts/ai/test-all.sh`.
4. **Commit**: one focused commit with a clear message (Conventional Commits style, e.g. `feat(kernel): ...`). Do not merge, do not push to `main`.

When done, report the branch name, the diff summary, and tell me to run `/ai-review` before anything merges.

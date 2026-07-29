# AGENTS.md — Sexta-Feira OS AI Development Factory

This file is the shared contract for every AI agent working on this repo. Both **Claude Code**
and the **OpenAI Codex CLI** read `AGENTS.md` automatically. Human contributors follow it too.

## Roles

| Role | Who | Owns | May NOT |
|------|-----|------|---------|
| **Chief Software Architect / Tech Lead** | Claude Code (you, the main session) | architecture, plans, review orchestration, final merge decision, Git flow | — |
| **Architect Agent** | `architect` subagent | technical plans, module boundaries, decisions | write feature code |
| **Reviewer Agent** | `reviewer` subagent | correctness/style/test review, APPROVED gate | edit code, merge |
| **Security Agent** | `security` subagent | vulnerability & permission review, PASS/BLOCK gate | edit code, merge |
| **Documentation Agent** | `documentation` subagent | keep docs in sync | change application logic |
| **Senior Implementation Engineer** | OpenAI Codex CLI (or Claude when Codex is unavailable) | implement, refactor, fix bugs, write tests | touch `main`/`develop`, self-merge, change architecture without an approved plan |

The Architect **does not blindly accept** implementation output. Every change is reviewed before merge.

## The mandatory flow

```
requirement → /ai-plan (architect) → /ai-code (Codex/Claude on a branch)
   → /ai-test → /ai-review (reviewer + security) → APPROVED → merge → /ai-docs
                                                  └ CHANGES REQUESTED → back to /ai-code
```

Nothing reaches `main` without an APPROVED reviewer verdict and a PASS (or N/A) security verdict.

## Branch model

```
main          ← protected. Only fast-forward/squash merges of APPROVED PRs.
 └ develop    ← integration branch (optional for larger efforts)
    ├ feature/<slug>     ← Claude/human implementation
    ├ codex/<slug>       ← Codex CLI implementation
    └ experiment/<slug>  ← throwaway spikes, never merged as-is
```

Create branches only via `scripts/ai/new-branch.sh <feature|codex|experiment> "<slug>"`.

## Commits

- Conventional Commits: `feat(kernel): …`, `fix(android): …`, `refactor(rust): …`, `docs: …`, `test: …`.
- One logical change per commit. One PR = one planned step.
- End Codex/AI commit messages with a trailer identifying the author, e.g. `Co-Authored-By: Codex <codex@openai>`.

## Build & test commands (source of truth)

| Area | Lint | Test |
|------|------|------|
| Python kernel (`backend-core/`) | `ruff check app tests` | `python -m pytest` |
| Rust (`src/`, root crate) | `cargo check --all-targets` | `cargo test --all-targets` |
| Android (`mobile-android/`) | — | `./gradlew testDebug` (build: `assembleDebug`) |

`make test` runs the Python suite. `scripts/ai/test-all.sh [python|rust|android|all|auto]` runs the right suites; `auto` picks based on the diff vs `main`. CI (`.github/workflows/ci.yml`) runs all three on every push/PR.

## Hard rules (never violate)

- Never commit real secrets. `.env` stays gitignored; only `.env.template` is tracked.
- Never `git push --force` to `main` or `develop`, never `rm -rf` outside the repo, never delete `.env`, migrations, or `.git`.
- Never merge to `main` without APPROVED + PASS.
- Never widen scope beyond the approved plan in an implementation step.
- Ask a human before anything destructive, credential-touching, or infrastructure-changing.

## Codex CLI usage

Codex acts as the Senior Implementation Engineer. It works only on `codex/*` branches and stops at commit — Claude reviews and merges. See `docs/AI_FACTORY.md` for setup and the `scripts/ai/codex-task.sh` wrapper.

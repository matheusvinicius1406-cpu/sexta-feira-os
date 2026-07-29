# AI Development Factory — Sexta-Feira OS

This repo is configured as a multi-agent engineering team. **Claude Code is the Chief Software
Architect and tech lead**; the **OpenAI Codex CLI** is the implementation engineer; specialized
Claude subagents handle review, security, and docs. Nothing reaches `main` unreviewed.

The authoritative contract every agent obeys is [`AGENTS.md`](../AGENTS.md). This doc explains how
the pieces fit and how to operate them.

## The team

```
Claude Code  ──  Chief Software Architect / Tech Lead / Auditor
   │
   ├── architect   (subagent)  →  turns requirements into technical plans
   ├── reviewer    (subagent)  →  code review, APPROVED gate
   ├── security    (subagent)  →  vulnerability review, PASS/BLOCK gate
   ├── documentation (subagent) →  keeps docs in sync
   └── Codex CLI   (external)   →  Senior Implementation Engineer (writes the code)
```

Subagents live in `.claude/agents/*.md`. Each has least-privilege tools (reviewer/security are
read-only; documentation can edit Markdown only; architect plans but doesn't code).

## The workflow

```
requirement
   → /ai-plan     architect produces a plan (no code)
   → /ai-code     implement ONE step on a codex/* or feature/* branch (Codex or Claude)
   → /ai-test     run the relevant suites
   → /ai-review   reviewer + security gate → APPROVED / CHANGES REQUESTED
        ├ APPROVED → merge to main (with your go-ahead)
        └ CHANGES REQUESTED → back to /ai-code
```

Slash commands are defined in `.claude/commands/`:

| Command | Does |
|---------|------|
| `/ai-plan <requirement>` | Architect turns a requirement into a step-by-step technical plan |
| `/ai-code <step>` | Implements one PR-sized step on an isolated branch (+ tests, one commit) |
| `/ai-test [scope]` | Runs Python/Rust/Android tests (`auto` detects from the diff) |
| `/ai-review [ref]` | Runs code review + security review + tests, ends in a verdict |
| `/ai-status` | Shows branch, diff, and where you are in the flow |

## Automation scripts (`scripts/ai/`)

| Script | Purpose |
|--------|---------|
| `new-branch.sh <feature\|codex\|experiment> "<slug>"` | Create an isolated branch off `main` |
| `test-all.sh [python\|rust\|android\|all\|auto]` | Run the right test suites |
| `status.sh` | Workflow status report |
| `codex-task.sh "<brief>"` | Hand one step to the Codex CLI (refuses on `main`/`develop`) |

Make them executable once: `chmod +x scripts/ai/*.sh` (already committed with the exec bit on Unix;
on Windows run them via Git Bash: `bash scripts/ai/status.sh`).

## Setting up the Codex CLI

Codex is optional — if it's absent, Claude plays the implementation engineer role directly. To
enable the real Codex hand-off:

```bash
npm install -g @openai/codex     # or: brew install codex
codex login                      # authenticate once (ChatGPT or API key)
```

Then, on a `codex/*` branch, `scripts/ai/codex-task.sh "<task brief>"` runs Codex in `--full-auto`
mode. Codex reads `AGENTS.md` automatically, edits files, runs tests in its sandbox, and **stops at
file changes** — committing, reviewing, and merging stay with Claude. Codex never touches
`main`/`develop` (the script refuses).

## Guardrails (`.claude/settings.json`)

- **Denied outright**: force-push, `git push origin main/develop`, `git reset --hard`,
  `git clean -fdx`, `rm -rf /` or `~`, and reading/editing `.env` files (secrets stay out of context).
- **Requires confirmation**: any `git merge`, `git push`, `git rebase`, branch deletion, `rm`,
  `codex`, and `gh pr merge`.
- `.env` is gitignored; only `.env.template` is tracked.

These enforce the "nothing to `main` without approval" rule at the tool level, not just by convention.

## Why no custom MCP server (yet)

The prompt asked to evaluate an MCP server for agent-to-agent communication. It isn't needed for the
core flow: Claude's native subagents already provide controlled, logged, least-privilege delegation,
and `AGENTS.md` is the shared memory both Claude and Codex read. Adding a bespoke MCP "message bus"
would add a fragile moving part with no capability we don't already have.

MCP **would** earn its place for connecting to *external* systems this project already uses — e.g. an
n8n MCP server to trigger/inspect workflows, an Obsidian vault MCP for the knowledge base, or a
GitHub MCP for richer PR automation. Those are read/write bridges to real services, which is exactly
what MCP is for. Add them per-service, scoped to least privilege, when a task needs them — not as a
generic inter-agent channel.

## Recommended: GitHub branch protection

The tool-level guardrails protect *this* machine. To enforce the same rules server-side, protect
`main` on GitHub (Settings → Branches): require a PR, require the CI checks
(`Kernel`, `Rust`, `Android` from `.github/workflows/ci.yml`) to pass, and disallow direct pushes.
That makes "nothing merges to main unreviewed" true even outside Claude Code.

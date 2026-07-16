# Claude Code skills (developer tooling)

These are **Claude Code skills** — markdown "Agent Skills" that enhance the *coding
assistant* working on this repo. They are **not** part of the Sexta-Feira product,
do not run in the kernel, and do not affect CI. They take effect the next time the
project is opened in Claude Code (skills are discovered at session start).

To use them globally on your own machine instead of per-repo, copy the skill folders
into `~/.claude/skills/`.

## Installed (safe, markdown-only — no code execution)

- **skillsmith** — meta-skill to author/scaffold/audit other Claude Code skills.
  Source: https://github.com/ChristopherKahler/skillsmith
- **brand-*** (29 skills) — brand strategy, naming, identity, voice, positioning,
  messaging, audits, launch, plus channels (email/meta/google ads, ASO, WhatsApp…).
  Source: https://github.com/arnabbagxd/Brand-building-skills (see its LICENSE)

Each folder is a self-contained `SKILL.md`. Content was reviewed before install; no
install scripts were run and no auto-executing hooks were added.

## Deliberately NOT installed (and why)

- **affaan-m/ECC** — a large multi-harness framework that ships **auto-running hooks**,
  commands and MCP configs. Dropping it in wholesale is a supply-chain / behavior risk.
  Only a reviewed, markdown-skills-only subset should be added, on request.
- **public-apis/public-apis** — a curated *list* of APIs (reference data), not a
  Claude Code skill. Better used as a source for automations/tools.
- **karpathy/llm-council** — a web app that calls **cloud LLMs** (OpenRouter). Not a
  skill, and its cloud dependency is antithetical to Sexta-Feira's local-only design.
  The *concept* (a council of models) can be re-implemented with local Ollama models.

_Third-party skills retain their original licenses; see each source repository._

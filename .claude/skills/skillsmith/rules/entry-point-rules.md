---
paths:
  - "skills/*/*.md"
---

# Entry Point Rules

Authoring rules for skill entry points. Validate against these when generating or reviewing `{skill-name}/{skill-name}.md` files.

## Must Have

### YAML Frontmatter
- `name` — kebab-case, matches directory name
- `type` — one of: `suite`, `standalone`, `task-only`
- `version` — semver format, start at `0.1.0`
- `category` — domain grouping (e.g., operations, content, development)
- `description` — one-line, action-oriented summary

### XML Sections (all 5, in order)
1. `<activation>` — What, When to Use, Not For
2. `<persona>` — Role, Style, Expertise
3. `<commands>` — Command table (omit for task-only)
4. `<routing>` — Always Load, Load on Command, Load on Demand
5. `<greeting>` — Brief intro, available actions, prompt

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Directory | kebab-case | `revops-expert/` |
| Entry point file | Matches directory | `revops-expert.md` |
| Slash command | Matches directory | `/revops-expert` |

## Anti-Patterns

| Pattern | Why It's Wrong |
|---------|---------------|
| Process logic in entry point | Entry points route to tasks — they don't execute workflows |
| Generic XML tags (`<section>`) | Use semantic tags: `<activation>`, `<persona>`, `<routing>` |
| Missing "Not For" in activation | Skill tries to do everything without scope boundaries |
| Version stuck at 1.0.0 | Start at 0.1.0, bump meaningfully |
| Vague persona | "Helpful assistant" — define role, style, expertise concretely |
| Loading everything always | Use "Load on Demand" for conditional files to save context |
| No greeting | User gets no orientation on what's available |

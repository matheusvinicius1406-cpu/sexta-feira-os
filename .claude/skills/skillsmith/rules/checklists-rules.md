---
paths:
  - "skills/*/checklists/*.md"
---

# Checklists Rules

Authoring rules for checklist files. Validate against these when generating or reviewing `checklists/*.md` files.

## Must Have

### Structure
1. **Header** — `# [Name] Checklist`
2. **Purpose** — One-line description: `**Purpose:** [what this checklist validates]`
3. **Categories** — Grouped `- [ ]` items organized by concern
4. **Scoring** (optional) — How to interpret results

### Item Requirements
- Every item uses `- [ ]` checkbox format
- Each item is independently pass/fail verifiable
- Items are specific enough to evaluate without interpretation
- Group related items under `##` category headers

### No Frontmatter
Checklists do NOT use YAML frontmatter. Content starts with a header.

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Checklist file | kebab-case, named for what it validates | `offer-quality.md`, `copy-review.md` |
| Directory | Always `checklists/` | `skills/revops-expert/checklists/` |

## Anti-Patterns

| Pattern | Why It's Wrong |
|---------|---------------|
| Vague criteria ("looks good") | Must be pass/fail — "Price anchored against value, not cost" |
| Mixing instructions with validation | Checklists validate, they don't instruct — that's what tasks do |
| Uncategorized flat list | Group by concern for readability and focused review |
| Items requiring subjective judgment | Each item should be objectively verifiable |
| No purpose line | Reader doesn't know what this checklist is for |

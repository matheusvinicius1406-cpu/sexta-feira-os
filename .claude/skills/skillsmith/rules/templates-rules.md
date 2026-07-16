---
paths:
  - "skills/*/templates/*.md"
---

# Templates Rules

Authoring rules for template files. Validate against these when generating or reviewing `templates/*.md` files.

## Must Have

### Structure (in order)
1. **Header** — `# [Name] Template`
2. **Intro** — Brief description + output file naming pattern
3. **Template block** — Fenced code block with ` ```template ` language tag
4. **Field Documentation** — Table explaining variable and prose fields
5. **Section Specifications** — Guidance for each section in the template

### Placeholder Conventions
- `{curly-braces}` — Variable interpolation, replaced with exact user input
- `[square-brackets]` — Human-written prose, replaced with descriptive text
- Never mix conventions: `{curly}` fields get data, `[square]` fields get prose

### Conditional Sections
- Document which template sections apply to which skill types
- Sections with no entries should show "None" rather than empty tables

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Template file | kebab-case | `offer-design.md`, `skill-spec.md` |
| Directory | Always `templates/` | `skills/revops-expert/templates/` |

## Anti-Patterns

| Pattern | Why It's Wrong |
|---------|---------------|
| Template without field documentation | Users don't know what to fill in or how |
| Mixing placeholder types | Confuses variable interpolation with prose — pick the right one |
| No output file naming pattern | Users don't know where to save the filled template |
| Template block without language tag | Use ` ```template ` for clear identification |
| Overly rigid templates | Templates should guide, not constrain — allow Notes/custom sections |

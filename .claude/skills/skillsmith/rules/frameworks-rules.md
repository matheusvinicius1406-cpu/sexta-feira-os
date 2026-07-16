---
paths:
  - "skills/*/frameworks/*.md"
---

# Frameworks Rules

Authoring rules for framework files. Validate against these when generating or reviewing `frameworks/*.md` files.

## Must Have

### Structure
1. **Purpose section** — What this framework explains and when to reference it
2. **Core Concepts** — The knowledge itself, organized by topic/component
3. **Examples** — Concrete illustrations (good vs bad when applicable)

### Optional Sections
- Outer XML container matching the concept (adds semantic clarity)
- **Anti-Patterns** — What to avoid and WHY
- **Sources** — Attribution if from a book, course, or methodology

### No Frontmatter
Frameworks do NOT use YAML frontmatter. They are read-only knowledge, not executable artifacts.

### Teaching Orientation
Frameworks teach — they don't command. Content should explain concepts and provide examples, not give step-by-step instructions (that's what tasks do).

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Framework file | kebab-case, named for the concept | `hormozi-value-equation.md` |
| Directory | Always `frameworks/` | `skills/revops-expert/frameworks/` |

## Anti-Patterns

| Pattern | Why It's Wrong |
|---------|---------------|
| Prescriptive instructions | Frameworks teach concepts — tasks give instructions |
| No examples | Concepts without examples are abstract and unhelpful |
| Dumping raw text | Organize by topic with clear headers and structure |
| Frontmatter on frameworks | Frameworks are reference knowledge, not metadata-bearing artifacts |
| Missing purpose section | Reader doesn't know when or why to reference this framework |

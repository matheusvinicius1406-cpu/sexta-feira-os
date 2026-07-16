# Rules Syntax Spec

Defines the syntax for rule files: `rules/*.md` — authoring rules that define what every file of a given type must contain.

**Applies to:** Meta-skill only (`skills/skillsmith/rules/*.md`). Individual skills do NOT carry their own rules.

---

## YAML Frontmatter

Rules files use YAML frontmatter with a `paths:` field targeting the folder type they govern:

```yaml
---
paths:
  - "skills/*/tasks/**/*.md"
---
```

### Frontmatter Fields

| Field | Required | Purpose | Example |
|-------|----------|---------|---------|
| `paths` | Yes | Glob patterns for files this rule applies to | `["skills/*/entry-point.md"]` |

The `paths` field tells tooling which files to validate against this rule. Use glob patterns with `*` for skill name and `**` for nested directories.

---

## File Structure

Every rule file follows this structure:

1. **YAML frontmatter** — `paths:` field
2. **Header** — `# [Folder Type] Rules`
3. **Intro** — What this rule governs and why
4. **File Structure** — What every file of this type must contain
5. **Conventions** — Naming, formatting, and style rules
6. **Examples** — Good vs bad illustrations
7. **Cross-References** — Links to the syntax spec for full detail

---

## Rule Content Structure

### Intro

```markdown
# Task Rules

Rules for editing files in `tasks/`. Every task file must conform to these rules to ensure consistency across all skills.
```

### File Structure Section

Define what every file of this type must contain:

```markdown
## File Structure

Every task file must have these XML sections in order:

1. `<purpose>` — What this task accomplishes (required)
2. `<user-story>` — Who benefits and how (required)
3. `<when-to-use>` — Trigger conditions (required)
4. `<context>` — Files to read before starting (optional)
5. `<references>` — Frameworks to lazy-load (optional)
6. `<steps>` — Execution steps (required)
7. `<output>` — What this task produces (required)
8. `<acceptance-criteria>` — Completion verification (required)
```

### Conventions Section

Define naming, formatting, and style rules:

```markdown
## Conventions

### Naming
- File name: kebab-case (`design-offer.md`, not `DesignOffer.md`)
- Step names: snake_case attribute (`name="gather_requirements"`)

### Formatting
- No YAML frontmatter
- Imperative voice in steps ("Ask the user" not "The user is asked")
- Explicit wait points ("Wait for response before proceeding")

### Acceptance Criteria
- Plain checklists only (`- [ ]` format)
- NOT BDD Given/When/Then
- Each item must have clear pass/fail criterion
```

### Cross-References Section

Point to the full syntax spec for comprehensive detail:

```markdown
## Full Specification

See: `specs/tasks.md` for complete syntax specification including:
- All XML section specifications with examples
- Step element attributes and content rules
- Conditional logic patterns
- Good vs bad examples
- Anti-patterns
```

---

## Scope: Meta-Skill Only

Rules live **exclusively** in the Skillsmith meta-skill:

```
skills/
  skillsmith/                  # Meta-skill
    skillsmith.md              # Entry point
    rules/                     # ← Rules live HERE
      entry-point-rules.md
      tasks-rules.md
      templates-rules.md
      frameworks-rules.md
      context-rules.md
      checklists-rules.md
    tasks/
    ...

  revops-expert/               # Regular skill
    revops-expert.md
    tasks/                     # ← No rules/ folder
    frameworks/
    ...
```

**Why meta-skill only:** Individual skills follow the standards — they don't carry the rulebook. Rules are the meta-layer that Skillsmith uses to validate and scaffold.

---

## How Rules Reference Specs

Rules are the **enforcement layer**. Specs are the **source of truth**. Rules summarize what specs define in detail:

```markdown
## Relationship

| Artifact | Purpose | Detail Level |
|----------|---------|-------------|
| **Spec** (`specs/tasks.md`) | Full syntax definition with rationale, examples, anti-patterns | Comprehensive |
| **Rule** (`rules/tasks-rules.md`) | Quick-reference enforcement checklist | Summary |

Rules say "what must be true." Specs explain "why and how."
```

A rule file should be concise enough to scan quickly during scaffolding. For the full explanation, it points to the spec.

---

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Rule file | `{folder-type}-rules.md` | `tasks-rules.md`, `entry-point-rules.md` |
| Directory | Always `rules/` | `skills/skillsmith/rules/` |
| Paths glob | `skills/*/{folder}/**/*.md` | `skills/*/tasks/**/*.md` |

---

## Core Principle

**Rules are the enforcement layer for specs.** They tell Skillsmith what to check when scaffolding or auditing a skill. They are concise summaries, not comprehensive documentation.

If someone asks "what must a task file contain?" — the rule answers in 30 seconds. If they ask "why, and what are the edge cases?" — the spec answers in 5 minutes.

---

## Good vs Bad Examples

### Good: Concise Rule with Cross-Reference

```yaml
---
paths:
  - "skills/*/tasks/**/*.md"
---
```

```markdown
# Task Rules

Rules for files in `tasks/`. Full specification: `specs/tasks.md`

## Required Sections

Every task file must have these XML sections:

| Section | Required | Key Rule |
|---------|----------|----------|
| `<purpose>` | Yes | 1-2 sentences, specific |
| `<user-story>` | Yes | "As a [role], I want [action], so that [outcome]" |
| `<when-to-use>` | Yes | Bullet list of trigger conditions |
| `<context>` | No | @-references only if genuinely needed |
| `<references>` | No | Lazy-load with conditional notes |
| `<steps>` | Yes | Named steps (`name="snake_case"`), imperative voice |
| `<output>` | Yes | Artifact format and file location |
| `<acceptance-criteria>` | Yes | Plain checklists, not BDD |

## Quick Checks

- [ ] No YAML frontmatter
- [ ] All steps have `name` attribute (snake_case)
- [ ] Acceptance criteria use `- [ ]` format (not Given/When/Then)
- [ ] Output section specifies file location
- [ ] Wait points are explicit ("Wait for response")

## Full Specification

See: `specs/tasks.md`
```

### Bad: Rule That Duplicates the Spec

```markdown
# Task Rules

## Purpose Section
The purpose section describes what the task accomplishes. It should be 1-2 sentences.
Here's what a good purpose looks like...
[300 lines of the spec repeated verbatim]
```

**Why bad:** Duplicates the spec — now changes must happen in two places. Rules summarize; specs detail.

---

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Rules in individual skills | Every skill carries its own rulebook — maintenance nightmare | Rules in meta-skill only |
| Rule duplicates full spec | Two sources of truth — drift inevitable | Rule summarizes, cross-references spec |
| Missing `paths:` frontmatter | Tooling can't know which files the rule applies to | Always include paths glob |
| Rule without quick checks | Can't scan quickly during scaffolding | Include checkbox summary |
| Rules that prescribe content | Rules define structure, not domain content | Structure rules only — content comes from frameworks |

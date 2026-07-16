---
paths:
  - "skills/*/tasks/*.md"
---

# Tasks Rules

Authoring rules for task files. Validate against these when generating or reviewing `tasks/*.md` files.

## Must Have

### XML Sections (all required, in order)
1. `<purpose>` — 1-2 sentences, what this task accomplishes
2. `<user-story>` — As a [role], I want [action], so that [outcome]
3. `<when-to-use>` — Trigger conditions (2-4 items)
4. `<steps>` — Execution steps with named step elements
5. `<output>` — What artifact is produced, format, location
6. `<acceptance-criteria>` — Plain checklist with `- [ ]` items

### Optional Sections
- `<context>` — Files to read before starting (after when-to-use)
- `<references>` — Frameworks to lazy-load during execution (after context)

### No Frontmatter
Tasks do NOT use YAML frontmatter. Content starts with `<purpose>`.

### Step Requirements
- Every `<step>` must have a `name` attribute in snake_case
- Use `priority="first"` on the opening step
- Include explicit "Wait for response" signals at user input points
- Use `<if condition="...">` for conditional logic within steps

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Task file | kebab-case | `full-build.md`, `design-offer.md` |
| Step names | snake_case | `gather_input`, `execute_core_work` |
| Directory | Always `tasks/` | `skills/revops-expert/tasks/` |

## Anti-Patterns

| Pattern | Why It's Wrong |
|---------|---------------|
| Unnamed steps | Can't reference, skip, or debug specific steps |
| Vague instructions ("make it good") | Claude interprets differently each time — be specific |
| No wait points | Task races through without user input |
| BDD acceptance criteria (Given/When/Then) | Skills use plain checklists — BDD is for PAUL plans |
| Monolithic task | Split into focused tasks, each with one concern |
| Loading all frameworks upfront | Use `<references>` with conditional loading notes |
| Missing `<output>` | No one knows what the task produces or where |
| No user-story | Task has no clear beneficiary or outcome |

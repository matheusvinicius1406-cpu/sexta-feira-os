---
paths:
  - "skills/*/context/*.md"
---

# Context Rules

Authoring rules for context files. Validate against these when generating or reviewing `context/*.md` files.

## Must Have

### Structure
1. **Header** — `# [Name]` (e.g., `# User Profile`, `# Business Profile`)
2. **Standard sections** — Based on context subtype (see below)
3. **Placeholder values** — Use `[Not yet captured]` for empty fields during scaffolding

### Context Subtypes
- **User Profile** — Identity, Role, Company, Preferences
- **Business Profile** — Business Name, Industry, Services, Target Audience
- **Custom** — Domain-specific state (e.g., pipeline status, inventory)

### Mutability
Context is the ONLY mutable file type in a skill. All other files (entry points, tasks, frameworks, templates, checklists) are stable reference. Context files are updated during skill use as the user provides information.

### No Frontmatter
Context files do NOT use YAML frontmatter. They are plain markdown with standard sections.

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Context file | kebab-case, named for what it stores | `user-profile.md`, `business-profile.md` |
| Directory | Always `context/` | `skills/revops-expert/context/` |

## Anti-Patterns

| Pattern | Why It's Wrong |
|---------|---------------|
| Storing process state | Context stores identity/profile, not workflow progress |
| Config in context | Settings belong in frontmatter or environment, not context files |
| No placeholder values | Empty files give no guidance on what to capture |
| Overly structured (YAML in markdown) | Keep it simple — headers and bullet points |
| Treating context as read-only | Context is meant to be updated — that's its purpose |

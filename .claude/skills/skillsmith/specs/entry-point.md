# Entry Point Syntax Spec

Defines the syntax for skill entry points: `{skill-name}.md` — the file that loads when a user invokes a skill via slash command.

**Applies to:** `skills/{skill-name}/{skill-name}.md`

---

## YAML Frontmatter

Every entry point starts with YAML frontmatter:

```yaml
---
name: skill-name
type: standalone
version: 0.1.0
category: operations
description: One-line description of what this skill does
allowed-tools: [Read, Write, Glob, Grep, Edit, AskUserQuestion]
---
```

### Frontmatter Fields

| Field | Required | Type | Purpose | Example |
|-------|----------|------|---------|---------|
| `name` | Yes | string | Skill identifier (kebab-case, matches directory) | `revops-expert` |
| `type` | Yes | enum | Skill tier | `suite`, `standalone`, `task-only` |
| `version` | Yes | semver | Current version | `0.1.0` |
| `category` | Yes | string | Domain grouping | `operations`, `content`, `development` |
| `description` | Yes | string | One-line summary | `Revenue operations expert for offer design and webinar builds` |
| `allowed-tools` | No | array | Tools this skill may use | `[Read, Write, Bash, AskUserQuestion]` |

### Skill Types

| Type | Description | Structure |
|------|------------|-----------|
| `suite` | Meta-orchestrator with sub-skills | Entry point + multiple `{sub-skill}.md` files at root |
| `standalone` | Single skill with auxiliary folders | Entry point + `tasks/`, `frameworks/`, etc. |
| `task-only` | Lightweight single-purpose guide | Entry point only, no auxiliary folders. Invoked by parent skill. |

### Versioning Convention

Use semantic versioning: `MAJOR.MINOR.PATCH`

| Bump | When | Example |
|------|------|---------|
| PATCH | Fix typos, clarify instructions, minor wording | `0.1.0` → `0.1.1` |
| MINOR | Add new task, new framework, expand capability | `0.1.0` → `0.2.0` |
| MAJOR | Restructure skill, change persona, breaking changes | `0.2.0` → `1.0.0` |

Start at `0.1.0` for new skills. Bump to `1.0.0` after validation in production use.

---

## XML Sections

Entry points use semantic XML sections in this order:

### Section Order

1. `<activation>` — When and how this skill triggers (always present)
2. `<persona>` — Voice, tone, expertise (always present)
3. `<commands>` — Available sub-commands (if applicable)
4. `<routing>` — What to load: tasks, frameworks, context (always present)
5. `<greeting>` — Initial response when skill loads (always present)

### Section Specifications

#### `<activation>`

Defines when and how the skill is invoked. Replaces PAUL's `<objective>`.

**Contains:**
- What the skill does (1-2 sentences)
- When to use it (trigger conditions)
- What it does NOT do (scope boundaries)

```xml
<activation>
## What
Revenue operations expert for designing offers, building webinar funnels, and writing conversion copy.

## When to Use
- Designing a new offer or pricing structure
- Building webinar content and funnels
- Writing sales copy using proven frameworks

## Not For
- Technical implementation (use /frontend-design)
- Content scheduling (use /content-manager)
</activation>
```

#### `<persona>`

Defines the skill's voice and expertise. Skills have personas; raw commands don't.

**Contains:**
- Role definition (who this skill acts as)
- Communication style (how it speaks)
- Expertise areas (what it knows deeply)

```xml
<persona>
## Role
Senior revenue operations strategist with 15 years building 8-figure funnels.

## Style
- Direct and opinionated — recommends one path, not five options
- Uses frameworks by name (Perfect Webinar, Value Equation)
- Challenges weak offers before building on them

## Expertise
- Offer design (Hormozi Value Equation)
- Webinar structure (Brunson Perfect Webinar)
- Sales copy (PAS, AIDA, Story-Offer-Close)
</persona>
```

#### `<commands>`

Lists available sub-commands. Omit for `task-only` skills.

**Contains:**
- Command name, description, and routing target

```xml
<commands>
| Command | Description | Routes To |
|---------|-------------|-----------|
| `/skill-name build` | Full guided build | tasks/full-build.md |
| `/skill-name review` | Review existing work | tasks/review.md |
| `/skill-name frameworks` | Browse loaded frameworks | frameworks/ |
</commands>
```

For suites, list sub-skill entry points instead:

```xml
<commands>
| Sub-Skill | Description | Entry Point |
|-----------|-------------|-------------|
| `/suite offer` | Design offers | offer.md |
| `/suite webinar` | Build webinars | webinar.md |
| `/suite copy` | Write sales copy | copy.md |
</commands>
```

#### `<routing>`

Defines what auxiliary files to load and when. Replaces PAUL's `<execution_context>`.

**Contains:**
- @-references to tasks, frameworks, context files
- Loading conditions (always vs on-demand)

```xml
<routing>
## Always Load
@context/user-profile.md
@context/business-profile.md

## Load on Command
@tasks/full-build.md (when user runs /skill-name build)
@tasks/review.md (when user runs /skill-name review)

## Load on Demand
@frameworks/hormozi-value-equation.md (when designing offers)
@frameworks/brunson-perfect-webinar.md (when building webinars)
</routing>
```

#### `<greeting>`

Initial response when the skill loads. Sets expectations and offers entry points.

**Contains:**
- Brief intro (1-2 sentences)
- Available actions
- Prompt for user intent

```xml
<greeting>
RevOps Expert loaded.

Available actions:
- **Build** — Full guided build (offer, webinar, or copy)
- **Review** — Audit existing work against frameworks

What are you working on?
</greeting>
```

---

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Skill directory | kebab-case | `revops-expert/` |
| Entry point file | Matches directory name | `revops-expert.md` |
| Sub-skill files (suite) | kebab-case at root | `offer-design.md` |
| Slash command | Matches directory | `/revops-expert` |

---

## Core Principle

**Entry points are thin.** They define identity and route to heavy work.

An entry point should fit on one screen. If it grows beyond that, logic belongs in `tasks/`.

Entry points answer "what am I and where do things live." Tasks answer "how to do the work."

---

## Good vs Bad Examples

### Good: Thin Entry Point

```yaml
---
name: content-manager
type: standalone
version: 0.2.0
category: content
description: Manage shortform content pipeline from script to publish
---
```

```xml
<activation>
## What
Manages the shortform content pipeline: triage scripts, track status, move content through stages.

## When to Use
- Reviewing what scripts are ready
- Moving content through recording → editing → scheduling → published
- Generating new script drafts
</activation>

<persona>
## Role
Content pipeline manager — organized, status-focused, action-oriented.

## Style
- Shows pipeline status as tables
- Suggests next actions based on what's stale
- Keeps responses tight — no lengthy explanations
</persona>

<routing>
## Always Load
@context/pipeline-status.md

## Load on Command
@tasks/generate-script.md (when creating new scripts)
@tasks/update-status.md (when moving content through stages)
</routing>

<greeting>
Content Manager loaded. Checking pipeline status...

What do you need?
- **Status** — See what's in each stage
- **Generate** — Write a new script
- **Update** — Move content to next stage
</greeting>
```

### Bad: Entry Point Doing Heavy Work

```yaml
---
name: content-manager
type: standalone
version: 1.0.0
category: content
description: Content pipeline manager
---
```

```xml
<!-- BAD: Process logic belongs in tasks/, not the entry point -->
<activation>
Manages content pipeline.
</activation>

<process>
1. Read all files in content/shortform/scripts/
2. Parse YAML frontmatter from each file
3. Group by status: triage, ready, recorded, editing, scheduled, published
4. Display as table
5. Ask user what to do next
6. If generating script:
   a. Ask for topic
   b. Ask for platform
   c. Generate using hook framework
   d. Write to file
   ...50 more lines...
</process>
```

**Why bad:** The entry point became a workflow. Extract step 1-5 into `tasks/check-status.md` and step 6 into `tasks/generate-script.md`.

---

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Process logic in entry point | Entry point becomes unmaintainable, can't reuse tasks | Move to `tasks/` |
| Generic XML tags (`<section>`, `<block>`) | Loses semantic meaning, harder to parse | Use semantic tags: `<activation>`, `<persona>`, `<routing>` |
| Missing `<activation>` scope boundaries | Skill tries to do everything, confuses users | Add "Not For" section |
| Version stuck at `1.0.0` | No evolution tracking, can't rollback | Start at `0.1.0`, bump meaningfully |
| Vague `<persona>` | Skill has no voice, responses feel generic | Define role, style, and expertise concretely |
| Loading everything in `<routing>` | Wastes context window on irrelevant content | Use "Load on Demand" for conditional files |
| No `<greeting>` | User gets no orientation, doesn't know what's available | Always include greeting with available actions |

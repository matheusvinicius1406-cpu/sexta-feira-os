<purpose>
Guided conversational interview that captures all design decisions needed to scaffold a new Claude Code skill. Produces a structured skill spec as output.
</purpose>

<user-story>
As a skill builder, I want a structured interview that walks me through every design decision so that I get a complete skill spec without missing anything or guessing at conventions.
</user-story>

<when-to-use>
- Creating a new skill from scratch
- Documenting an existing skill's design for future scaffolding
- Exploring what a skill should look like before building it
</when-to-use>

<context>
@specs/entry-point.md
</context>

<references>
@specs/tasks.md (when discussing task structure)
@specs/templates.md (when discussing template structure)
@specs/frameworks.md (when discussing framework structure)
@specs/context.md (when discussing context structure)
@specs/checklists.md (when discussing checklist structure)
@specs/rules.md (when discussing rules — meta-skill only)
</references>

<steps>

<step name="phase-1-identity" label="Identity">
Capture the skill's core identity. Ask as a group, wait for responses.

**Ask:**
1. **Skill name** — What should this skill be called? (kebab-case, e.g., `revops-expert`)
2. **Type** — What tier?
   - `suite` — Orchestrator with sub-skills (e.g., skillsmith itself)
   - `standalone` — Single skill with auxiliary folders (most common)
   - `task-only` — Lightweight single-purpose, no auxiliary folders
3. **Category** — What domain? (common: operations, content, development, design, analysis)
4. **Description** — One sentence: what does this skill do?

**Validate:**
- Name must be kebab-case (lowercase, hyphens only)
- Type must be one of: suite, standalone, task-only
- Description should be one line, action-oriented

**After responses:** Confirm back: "Got it — `{name}` is a `{type}` skill in `{category}`: {description}. Correct?"
</step>

<step name="phase-2-persona" label="Persona">
Define who this skill acts as. Ask as a group, wait for responses.

**Ask:**
1. **Role** — Who does this skill act as? (e.g., "Senior revenue operations strategist", "Content pipeline manager")
2. **Style** — How does it communicate? Pick or describe:
   - Structured / casual / opinionated / minimal / technical / conversational
   - Any specific behaviors (e.g., "uses frameworks by name", "challenges weak inputs")
3. **Expertise** — What domains does it know deeply? List 2-5 areas.

**After responses:** Summarize persona in 3 bullets (role, style, expertise) and confirm.
</step>

<step name="phase-3-scope" label="Scope & Commands">
Define what the skill does and doesn't do, plus its command structure.

**Ask:**
1. **What** — What does this skill do? (1-2 sentences for the activation section)
2. **When to Use** — When should someone reach for this skill? (list 2-4 triggers)
3. **Not For** — What is explicitly NOT this skill's job? (list 1-3 boundaries, reference other skills if applicable)
4. **Commands** (skip for task-only):
   - What actions/workflows does this skill offer?
   - For each: command name, brief description, what it routes to

**After responses:** Display activation scope and command table for confirmation.
</step>

<step name="phase-4-content-architecture" label="Content Architecture">
Walk through each auxiliary folder type to determine what the skill needs.

**For each folder type below, ask:** "Does this skill need [type]? If yes, what files?"

**Tasks** (`tasks/*.md`):
- What guided workflows does this skill perform?
- For each: file name (kebab-case), purpose, loading condition (on-command)

**Frameworks** (`frameworks/*.md`):
- What domain knowledge does this skill carry?
- For each: file name, what it teaches, loading condition (on-demand typical)

**Templates** (`templates/*.md`):
- What structured outputs does this skill produce?
- For each: file name, what it generates

**Context** (`context/*.md`):
- What user or business state does this skill need to remember between sessions?
- For each: file name, what it stores, loading condition (always typical for context)

**Checklists** (`checklists/*.md`):
- What quality gates does this skill enforce?
- For each: file name, what it validates

**Note:** Rules folder is meta-skill only (Skillsmith carries rules, individual skills don't).

**After each "yes":** Capture file name, purpose, and loading condition.
**After all types reviewed:** Display content architecture summary table and confirm.
</step>

<step name="phase-5-review" label="Review & Confirm">
Present the complete skill spec for final review.

1. Generate the full skill spec using @templates/skill-spec.md format
2. Display it to the user with all captured decisions filled in
3. Ask: "Does this look right? Say **confirm** to finalize, or tell me what to change."

**On confirm:**
- Output the finalized skill spec
- Report: "Skill spec complete. Run `/skillsmith scaffold` to generate the directory. (Phase 3)"

**On edit requests:**
- Apply changes to the spec
- Re-display affected sections
- Re-confirm
</step>

</steps>

<output>
Filled skill spec following templates/skill-spec.md format, containing:
- Identity (name, type, category, description)
- Persona (role, style, expertise)
- Activation scope (what, when, not for)
- Commands table
- Content architecture (tasks, frameworks, templates, context, checklists with file names and loading conditions)
</output>

<acceptance-criteria>
- [ ] All 5 phases completed in order
- [ ] Skill name validated as kebab-case
- [ ] Skill type is one of: suite, standalone, task-only
- [ ] Persona captured with role, style, expertise
- [ ] Activation scope has What, When to Use, and Not For
- [ ] Each auxiliary folder type explicitly addressed (yes with details, or no)
- [ ] Skill spec output generated with all fields populated
- [ ] User confirmed the final spec
</acceptance-criteria>

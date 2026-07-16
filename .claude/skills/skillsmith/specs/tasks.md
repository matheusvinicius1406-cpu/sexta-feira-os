# Tasks Syntax Spec

Defines the syntax for task files: `tasks/*.md` — step-by-step guided workflows that do the heavy work.

**Applies to:** `skills/{skill-name}/tasks/*.md`

---

## No Frontmatter

Tasks do not use YAML frontmatter. Content starts immediately with semantic XML. This matches PAUL workflow convention — tasks are execution files, not metadata-bearing artifacts.

---

## XML Sections

Tasks use semantic XML sections in this order:

### Section Order

1. `<purpose>` — What this task accomplishes (always present)
2. `<user-story>` — Who benefits and how (always present)
3. `<when-to-use>` — Trigger conditions (always present)
4. `<context>` — Files to read before starting (if needed)
5. `<references>` — Frameworks to lazy-load (if needed)
6. `<steps>` — Execution steps (always present)
7. `<output>` — What this task produces (always present)
8. `<acceptance-criteria>` — How to verify completion (always present)

### Section Specifications

#### `<purpose>`

One to two sentences describing what this task accomplishes.

```xml
<purpose>
Guide the user through designing a complete offer using the Hormozi Value Equation. Produces a structured offer document ready for sales copy.
</purpose>
```

#### `<user-story>`

Defines who this task serves and the outcome they get.

**Format:** As a [role], I want [action], so that [outcome].

```xml
<user-story>
As a business owner, I want to design a structured offer using proven frameworks, so that my offer is compelling and I don't leave money on the table.
</user-story>
```

#### `<when-to-use>`

Decision criteria for invoking this task. Helps the entry point route correctly.

```xml
<when-to-use>
- User explicitly asks to design or redesign an offer
- User has a product/service but no structured pricing
- Entry point routes here via `/revops-expert build offer`
</when-to-use>
```

#### `<context>`

Files to read before starting execution. Equivalent to PAUL's `<required_reading>`.

```xml
<context>
@context/user-profile.md
@context/business-profile.md
</context>
```

Only include files genuinely needed. Do not reflexively load everything.

#### `<references>`

Frameworks to lazy-load when relevant during execution. Not pre-loaded — read when a step needs them.

```xml
<references>
@frameworks/hormozi-value-equation.md (during pricing step)
@frameworks/risk-reversal-patterns.md (during guarantee step)
</references>
```

#### `<steps>`

The execution logic. This is where the heavy work lives.

**Step elements:**

```xml
<step name="snake_case_name" priority="first">
Imperative instructions here.

1. Do this first
2. Then do this
3. Finally do this
</step>
```

**Step attributes:**

| Attribute | Required | Purpose | Values |
|-----------|----------|---------|--------|
| `name` | Yes | Identifier (snake_case) | `gather_requirements`, `design_pricing` |
| `priority` | No | Ordering hint | `first`, `last` |

**Step content rules:**
- Imperative voice: "Ask the user" not "The user is asked"
- Numbered sub-steps for sequential actions
- Prose for conditional logic or decision trees
- Can include `<if>` elements for conditional behavior

**Conditional logic within steps:**

```xml
<step name="determine_approach">
<if condition="user has existing offer">
  Review current offer structure.
  Identify gaps using Value Equation.
  Recommend specific improvements.
</if>

<if condition="user starting from scratch">
  Start with dream outcome identification.
  Walk through full Value Equation build.
</if>
</step>
```

**Wait points within steps:**

When a step requires user input before continuing, use explicit wait signals:

```xml
<step name="gather_requirements">
Ask the user:
1. What is your product or service?
2. Who is your ideal customer?
3. What is their dream outcome?

**Wait for response before proceeding.**

Once received, summarize back to confirm understanding.
</step>
```

#### `<output>`

Defines what this task produces. Be specific about format and location.

```xml
<output>
## Artifact
Structured offer document in markdown.

## Format
```markdown
# [Offer Name]

## Dream Outcome
[What the customer gets]

## Perceived Likelihood
[Why they'll believe it works]

## Time Delay
[How fast they get results]

## Effort & Sacrifice
[What they don't have to do]

## Price
[Pricing structure]

## Guarantee
[Risk reversal]
```

## Location
Write to: `output/{offer-name}-offer.md`
</output>
```

#### `<acceptance-criteria>`

How to verify the task completed successfully. Uses **plain checklists** (not BDD Given/When/Then).

```xml
<acceptance-criteria>
- [ ] Offer document created with all Value Equation sections
- [ ] Dream outcome is specific and measurable
- [ ] Price anchored against value (not cost)
- [ ] Guarantee includes specific risk reversal mechanism
- [ ] User confirmed the offer matches their intent
</acceptance-criteria>
```

**Checklist rules:**
- Each item has a clear pass/fail criterion
- Items are independently verifiable
- Include both output checks and quality checks
- Always include user confirmation as final item

---

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Task file | kebab-case | `full-build.md`, `design-offer.md` |
| Step names | snake_case | `name="gather_requirements"` |
| Directory | Always `tasks/` | `skills/revops-expert/tasks/` |

---

## Core Principle

**Tasks contain the heavy logic.** Entry points route here; tasks execute.

A task can be long and detailed. It answers "how to do it" comprehensively. If a task grows beyond a single concern, split into multiple tasks — not into a longer task.

---

## Good vs Bad Examples

### Good: Structured Task with Clear Steps

```xml
<purpose>
Generate a shortform video script for LinkedIn or Instagram based on a topic and hook.
</purpose>

<user-story>
As a content creator, I want a structured script for a 60-second video, so that I can record without improvising and stay on message.
</user-story>

<when-to-use>
- User has a topic and wants a script
- Entry point routes here via /content-manager generate
</when-to-use>

<references>
@frameworks/hook-patterns.md (during hook selection)
</references>

<steps>

<step name="gather_input" priority="first">
Ask the user:
1. What topic or lesson do you want to share?
2. Target platform: LinkedIn or Instagram?
3. Any specific angle or hook in mind?

**Wait for response.**
</step>

<step name="select_hook">
Load @frameworks/hook-patterns.md

Based on the topic, select 2-3 hook options:
- Pattern interrupt hook
- Contrarian hook
- Story hook

Present options. Let user choose or request alternatives.

**Wait for selection.**
</step>

<step name="write_script">
Write the script following this structure:
1. Hook (selected above) — first 3 seconds
2. Context — why this matters (10 seconds)
3. Core lesson — the insight (30 seconds)
4. CTA — what to do next (5 seconds)

Keep total under 150 words for 60-second delivery.
</step>

<step name="review_and_refine">
Present the script to the user.
Ask: "Does this capture your message? Any adjustments?"

**Wait for approval or revision requests.**

If revisions requested, adjust and re-present.
</step>

</steps>

<output>
## Artifact
Script in markdown with sections labeled.

## Location
Write to: content/shortform/scripts/0-triage/{platform}-{topic-slug}.md
</output>

<acceptance-criteria>
- [ ] Script has hook, context, core lesson, and CTA sections
- [ ] Total word count under 150 words
- [ ] Platform-appropriate formatting (LinkedIn vs Instagram)
- [ ] User approved final script
</acceptance-criteria>
```

### Bad: Vague Task with No Structure

```xml
<!-- BAD: No user story, no step names, no acceptance criteria -->
<purpose>
Generate a script.
</purpose>

<steps>
Ask the user what they want to talk about.
Then write a script.
Make it good.
Show it to them.
</steps>
```

**Why bad:** No user story (who is this for?), no step names (can't reference or skip steps), instructions are vague ("make it good"), no output spec, no acceptance criteria.

---

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| No `<user-story>` | Task has no clear beneficiary or outcome | Always define who benefits and what they get |
| Unnamed steps | Can't reference, skip, or debug specific steps | Always use `<step name="snake_case">` |
| "Make it good" instructions | Vague — Claude will interpret differently each time | Be specific: "Keep under 150 words", "Include 3 options" |
| No wait points | Task races through without user input | Add explicit "Wait for response" signals |
| BDD acceptance criteria | Over-formal for skill context, adds friction | Use plain checklists: `- [ ] Specific criterion` |
| Monolithic task | Single task trying to do everything | Split into focused tasks, each with one concern |
| Loading all frameworks upfront | Wastes context on irrelevant knowledge | Use `<references>` with conditional loading notes |
| Missing `<output>` section | No one knows what the task produces or where | Always specify artifact format and location |

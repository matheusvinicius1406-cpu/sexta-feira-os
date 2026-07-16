# Frameworks Syntax Spec

Defines the syntax for framework files: `frameworks/*.md` — read-only reference knowledge loaded by tasks when domain context is needed.

**Applies to:** `skills/{skill-name}/frameworks/*.md`

---

## No Frontmatter

Frameworks do not use YAML frontmatter. They are conceptual knowledge, not executable artifacts. Content starts immediately.

---

## File Structure

Frameworks follow a teaching-oriented structure:

1. **Outer XML container** (optional) — Semantic tag matching the concept
2. **Purpose section** — What this framework explains
3. **Core concepts** — The knowledge itself, organized by topic
4. **Examples** — Concrete illustrations (good vs bad when applicable)
5. **Anti-patterns** — What to avoid and WHY
6. **Sources** (optional) — Attribution if from a book, course, or methodology

---

## Outer XML Container

Frameworks may use an outer XML container related to their topic. Not required, but adds semantic clarity for parseable sections.

```xml
<!-- hormozi-value-equation.md -->
<value_equation>
## Purpose
...

## The Four Variables
...
</value_equation>

<!-- hook-patterns.md -->
<hook_patterns>
## Purpose
...

## Pattern Types
...
</hook_patterns>
```

**Tag naming:** snake_case matching the concept. Use when the framework has distinct parseable sections a task might reference individually.

---

## Teaching Patterns

Frameworks explain domain knowledge for tasks to consume. Two primary teaching patterns:

### Teach by Contrast

Show good vs bad to make principles concrete:

```markdown
## Weak vs Strong Dream Outcomes

**Weak:** "Grow your business"
- Not specific, not measurable, not compelling

**Strong:** "Generate 20 qualified leads per month without cold calling"
- Specific number, specific method, specific relief
```

### Explain WHY

Don't just state rules — explain the reasoning:

```markdown
## Why Price Anchoring Matters

Without anchoring, customers compare your price to competitors.
With anchoring, customers compare your price to the VALUE they receive.

A $5,000 offer feels expensive compared to a $2,000 competitor.
A $5,000 offer feels like a steal compared to $50,000 in delivered value.

The anchor shifts the reference point from cost to value.
```

---

## Loading Pattern

Frameworks are lazy-loaded by tasks when conceptual context is needed:

```xml
<!-- In a task file -->
<references>
@frameworks/hormozi-value-equation.md (during pricing step)
@frameworks/risk-reversal-patterns.md (during guarantee step)
</references>
```

**Rules:**
- Frameworks are loaded on demand, not pre-loaded at skill activation
- A task can load one framework without needing others (self-contained)
- Entry point `<routing>` lists frameworks under "Load on Demand"

---

## Distinction: Frameworks vs Context vs Templates

| Type | Purpose | Mutability | Loaded When |
|------|---------|------------|-------------|
| **Frameworks** | Domain knowledge (concepts, methods, patterns) | Read-only — never modified | On demand by tasks |
| **Context** | Business/user state (profiles, preferences, history) | Mutable — updated as context changes | On skill activation |
| **Templates** | Output structure (fill-in-the-blank formats) | Read-only — output written elsewhere | During task output generation |

**Rule of thumb:**
- If it teaches a concept → framework
- If it describes a specific user/business → context
- If it defines output shape → template

---

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Framework file | kebab-case, descriptive | `hormozi-value-equation.md`, `hook-patterns.md` |
| Directory | Always `frameworks/` | `skills/revops-expert/frameworks/` |
| Outer XML tag | snake_case | `<value_equation>`, `<hook_patterns>` |

---

## Core Principle

**Frameworks are knowledge, not instructions.** They explain concepts and patterns that tasks reference when making decisions or generating output.

Frameworks are self-contained — loading one framework should never require loading another. If two concepts are tightly coupled, they belong in the same file.

---

## Good vs Bad Examples

### Good: Teaching-Oriented Framework

```xml
<value_equation>

## Purpose

Alex Hormozi's Value Equation from "$100M Offers." Quantifies offer value using four variables. Used during offer design to ensure compelling pricing.

## The Equation

```
Value = (Dream Outcome × Perceived Likelihood) / (Time Delay × Effort & Sacrifice)
```

Maximize the top (outcome, believability). Minimize the bottom (time, effort).

## Variables

### Dream Outcome
The ideal result your customer achieves.

**Strong:** "Generate 20 qualified leads per month without cold calling"
**Weak:** "Grow your business" (vague, not measurable)

### Perceived Likelihood of Achievement
Why the customer believes this will work FOR THEM.

**Elements:** Case studies, credentials, specificity of method, guarantees.

### Time Delay
How long until they see results. Shorter = more valuable.

**Strong:** "First leads within 14 days"
**Weak:** "Results over time"

### Effort & Sacrifice
What the customer DOESN'T have to do. Less effort = more valuable.

**Strong:** "Done-for-you setup, no technical skills needed"
**Weak:** "Easy to use" (subjective, unspecific)

## Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| Pricing based on cost, not value | Anchor to dream outcome dollar value |
| Vague dream outcomes | Make specific and measurable |
| No proof elements | Add case studies, guarantees, credentials |
| Ignoring effort reduction | Explicitly list what customer doesn't do |

## Source

Alex Hormozi, "$100M Offers" (2021)

</value_equation>
```

### Bad: Vague Framework

```markdown
# Value Equation

The value equation helps you price offers.

You should think about what the customer gets and how much effort it takes.
Price your offer based on value.
```

**Why bad:** No structure, no variables explained, no examples, no contrast, nothing actionable. A task loading this framework gains nothing.

---

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Framework with instructions | Frameworks teach, they don't instruct — that's tasks | Move step-by-step instructions to `tasks/` |
| Framework requiring other frameworks | Breaks self-contained principle | Merge coupled concepts into one file |
| No examples | Abstract knowledge without concrete illustration | Add good/bad contrast examples |
| No "WHY" explanations | Rules without reasoning are hard to apply | Explain the principle behind each concept |
| Modifying frameworks during execution | Breaks read-only contract | Frameworks are immutable reference — write output elsewhere |
| Loading all frameworks at activation | Wastes context on irrelevant knowledge | Lazy-load from tasks when needed |

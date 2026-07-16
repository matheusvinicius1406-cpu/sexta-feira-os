# Checklists Syntax Spec

Defines the syntax for checklist files: `checklists/*.md` — reusable QA validation lists for skill outputs.

**Applies to:** `skills/{skill-name}/checklists/*.md`

---

## No Frontmatter

Checklists do not use YAML frontmatter. Content starts with a header.

---

## File Structure

Every checklist follows this structure:

1. **Header** — `# [Name] Checklist`
2. **Purpose** — One-line description of what this checklist validates
3. **Categories** — Grouped `- [ ]` items organized by concern
4. **Scoring** (optional) — How to interpret results

---

## Checklist Format

### Header and Purpose

```markdown
# Offer Design Checklist

Validates a completed offer document against the Value Equation framework.
```

### Categories

Group items by concern. Each category has a header and checkbox items:

```markdown
## Dream Outcome
- [ ] Outcome is specific (not "grow your business")
- [ ] Outcome is measurable (includes numbers or timeframes)
- [ ] Outcome matches target audience's language

## Perceived Likelihood
- [ ] At least one proof element included (case study, credential, or guarantee)
- [ ] Claims are specific, not vague ("20 leads/month" not "more leads")
- [ ] Method is named and described (not "our proprietary system")

## Pricing
- [ ] Value anchor stated before price
- [ ] Value-to-price ratio is at least 3:1
- [ ] Price is a specific number (not "starting at" or "contact us")

## Guarantee
- [ ] Risk reversal mechanism is specific
- [ ] Guarantee has clear terms (timeframe, conditions)
- [ ] Guarantee reduces perceived risk, not just restating the offer
```

### Item Format

Every checklist item must have a **clear pass/fail criterion**:

```markdown
<!-- GOOD: Clear pass/fail -->
- [ ] Value-to-price ratio is at least 3:1
- [ ] Hook is under 15 words
- [ ] CTA includes one specific action

<!-- BAD: Subjective, can't pass/fail -->
- [ ] Offer looks good
- [ ] Price feels right
- [ ] Content is engaging
```

### Scoring (Optional)

For checklists where partial completion is meaningful:

```markdown
## Scoring

| Score | Rating | Action |
|-------|--------|--------|
| 100% | Ship it | Ready for production |
| 75-99% | Fix and ship | Address gaps, then go |
| 50-74% | Rework | Significant gaps — revisit framework |
| Below 50% | Restart | Fundamental issues — redesign needed |
```

---

## Relationship to Task Acceptance Criteria

Checklists and task acceptance criteria serve different purposes:

| Dimension | Task Acceptance Criteria | Checklists |
|-----------|------------------------|------------|
| **Scope** | Specific to one task | Reusable across tasks and skills |
| **Location** | Inside `<acceptance-criteria>` in task file | Separate file in `checklists/` |
| **Purpose** | "Did this task complete?" | "Is the output quality good?" |
| **Used When** | Task completion verification | Output QA, before delivery |

**How they work together:**
- A task's acceptance criteria might include: `- [ ] Output passes offer-design checklist`
- The checklist itself lives in `checklists/offer-design.md`
- The task references the checklist; it doesn't duplicate it

```xml
<!-- In a task file -->
<acceptance-criteria>
- [ ] Offer document created with all sections
- [ ] User confirmed the offer matches their intent
- [ ] Output passes checklists/offer-design.md validation
</acceptance-criteria>
```

---

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Checklist file | kebab-case, matches what it validates | `offer-design.md`, `script-quality.md` |
| Directory | Always `checklists/` | `skills/revops-expert/checklists/` |
| Categories | Title case headers | `## Dream Outcome`, `## Pricing` |

---

## Core Principle

**Checklists are reusable quality gates.** They validate output quality independently of the task that produced it. A checklist written once can be used by multiple tasks, multiple users, and across skill versions.

Every item must be pass/fail. If you can't objectively determine whether an item passes, it's too vague.

---

## Good vs Bad Examples

### Good: Specific, Grouped Checklist

```markdown
# Script Quality Checklist

Validates a shortform video script before recording.

## Hook (0-3 seconds)
- [ ] Hook is under 15 words
- [ ] Hook uses one pattern: interrupt, contrarian, or story
- [ ] Hook does not start with "In this video" or "Hey guys"

## Structure
- [ ] Script has exactly 4 sections: hook, context, lesson, CTA
- [ ] Total word count is 120-150 words
- [ ] Core lesson contains one specific, actionable takeaway

## CTA
- [ ] CTA includes exactly one action (not "follow, like, and subscribe")
- [ ] Action is specific: "Comment X below" or "Link in bio for Y"

## Platform Fit
- [ ] LinkedIn: Professional tone, no slang, insight-focused
- [ ] Instagram: Casual tone, visual language, emotion-focused
- [ ] Script matches selected platform conventions
```

### Bad: Vague Checklist

```markdown
# Script Checklist

- [ ] Script is good
- [ ] Hook grabs attention
- [ ] Content is valuable
- [ ] CTA is clear
```

**Why bad:** Every item is subjective. "Script is good" — by what standard? "Hook grabs attention" — how do you measure that? No categories, no pass/fail criteria.

---

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Subjective items ("looks good", "feels right") | Can't objectively pass/fail | Make measurable: "under 15 words", "at least 3:1 ratio" |
| No categories | Long flat list is hard to scan | Group by concern |
| Duplicating task acceptance criteria | Maintenance burden — changes in two places | Reference checklist from task AC, don't copy |
| Too many items (30+) | Checklist fatigue — people skip items | Keep under 20 items. Split into multiple checklists if needed |
| Missing scoring guidance | Users don't know what "enough" looks like | Add scoring section for partial completion |
| Checklist for process (not output) | Checklists validate outputs, not how you got there | Move process steps to `tasks/` |

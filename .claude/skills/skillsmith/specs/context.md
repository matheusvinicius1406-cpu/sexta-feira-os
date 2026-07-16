# Context Syntax Spec

Defines the syntax for context files: `context/*.md` — business and user state that personalizes skill behavior.

**Applies to:** `skills/{skill-name}/context/*.md`

---

## No Frontmatter

Context files do not use YAML frontmatter. They are plain markdown with standard sections. Content starts with a header.

---

## Context Subtypes

### User Profile

Personal information about the skill's user — preferences, history, identity.

**Standard sections:**

```markdown
# User Profile

## Identity
- Name: [Full name]
- Role: [Primary role or title]
- Company: [Business name]

## Preferences
- Communication style: [Direct / Conversational / Formal]
- Output format: [Markdown / PDF / Plain text]
- Tone: [Professional / Casual / Technical]

## History
- Previous outputs: [Links or references to prior work]
- Known constraints: [Time zones, tools, limitations]

## Notes
[Free-form notes that affect skill behavior]
```

### Business Profile

Information about the business the skill serves — brand, positioning, audience.

**Standard sections:**

```markdown
# Business Profile

## Company
- Name: [Business name]
- Website: [URL]
- Industry: [Primary industry]
- Stage: [Startup / Growth / Established]

## Brand Voice
- Tone: [How the brand speaks]
- Values: [Core principles]
- Avoid: [Words, phrases, or approaches to never use]

## Target Audience
- Primary: [Who they serve]
- Pain points: [What problems they solve]
- Language: [How the audience talks about their problems]

## Products/Services
- [Product 1]: [Brief description and price point]
- [Product 2]: [Brief description and price point]

## Competitors
- [Competitor 1]: [Key differentiator]
- [Competitor 2]: [Key differentiator]
```

### Custom Context

For domain-specific state that doesn't fit user or business profiles.

**Naming:** Descriptive kebab-case — `pipeline-status.md`, `client-roster.md`, `campaign-history.md`

**Structure:** Use headers that make sense for the domain. No rigid template — but maintain consistent formatting with other context files in the skill.

---

## Onboarding Template Pattern

When context is missing, skills should gather it. Include an onboarding template that defines questions to ask:

```markdown
# Onboarding: User Profile

## Questions

Ask these questions when `context/user-profile.md` doesn't exist or is incomplete:

1. What's your name and role?
2. What's your business called and what do you do?
3. How do you prefer output — formal or conversational?
4. Any tools, platforms, or constraints I should know about?

## After Gathering

Create `context/user-profile.md` from responses using the standard user profile structure.
```

**Rules:**
- Onboarding templates live alongside context files: `context/onboarding-user.md`
- Tasks check for context existence before starting and route to onboarding if missing
- Onboarding runs once — after gathering, context file exists for future sessions

---

## Loading Pattern

Context files load on skill activation — they are "always load" in the entry point routing:

```xml
<!-- In entry point -->
<routing>
## Always Load
@context/user-profile.md
@context/business-profile.md

## Load on Demand
@frameworks/... (loaded by tasks when needed)
</routing>
```

**Why always-load:** Context personalizes every interaction. Unlike frameworks (which are domain knowledge), context is identity — the skill needs it from the start.

---

## Distinction: Context vs Frameworks

| Dimension | Context | Frameworks |
|-----------|---------|------------|
| **Contains** | State about this user/business | Knowledge about a domain |
| **Mutability** | Mutable — updates as context changes | Read-only — never modified |
| **Loading** | Always-load on activation | Lazy-load by tasks on demand |
| **Example** | "Chris runs C&C Strategic Consulting" | "The Value Equation has four variables" |
| **Lifespan** | Changes over time | Stable reference material |

**Rule of thumb:** If it would be different for a different user → context. If it's the same regardless of user → framework.

---

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Context file | kebab-case, descriptive | `user-profile.md`, `business-profile.md` |
| Onboarding file | `onboarding-{type}.md` | `onboarding-user.md` |
| Directory | Always `context/` | `skills/revops-expert/context/` |

---

## Core Principle

**Context is the skill's memory of who it's serving.** Without context, every interaction starts from zero. With context, the skill personalizes from the first word.

Context files are the only mutable files in a skill directory. Everything else (entry point, tasks, frameworks, templates, checklists) is stable reference material.

---

## Good vs Bad Examples

### Good: Structured Business Profile

```markdown
# Business Profile

## Company
- Name: C&C Strategic Consulting
- Website: https://ccstrategic.io
- Industry: AI implementation for agencies
- Stage: Growth

## Brand Voice
- Tone: Direct, confident, no-fluff
- Values: Results over promises, implementation over theory
- Avoid: "Leverage", "synergy", buzzword-heavy language

## Target Audience
- Primary: Agency owners doing $500K-$5M/year
- Pain points: Manual processes eating margins, can't scale without hiring
- Language: "I need more time", "I'm doing everything myself", "My team can't keep up"

## Products/Services
- AI Agent Setup: Done-for-you automation — $4,997
- Voice AI Employee: Handles calls 24/7 — $2,497/mo
- CRM Automation: GoHighLevel setup — $1,997

## Competitors
- Generic AI agencies: Lower price, no specialization
- In-house hires: Higher cost, slower ramp
```

### Bad: Vague Context

```markdown
# Business

We do AI stuff for agencies. Our clients are business owners.
We charge various prices depending on the project.
```

**Why bad:** No structure, no specifics the skill can use. "AI stuff" and "various prices" give the skill nothing to personalize with.

---

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Domain knowledge in context files | Mixes state with reference — hard to maintain | Move knowledge to `frameworks/`, keep context for state |
| No onboarding path | Skill fails silently when context is missing | Add onboarding template with questions |
| Loading context on demand | Skill gives generic responses until context loads | Always-load context at activation |
| Stale context never updated | Skill uses outdated information | Note update triggers in each section |
| Context file too large | Wastes context window on low-value details | Keep profiles concise — move history to separate files |
| Hardcoded context in entry point | Can't be updated without editing skill source | Always use separate context files |

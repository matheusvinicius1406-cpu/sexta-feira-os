---
description: Turn a requirement into an architect-reviewed technical plan (no code written)
argument-hint: <requirement in plain language>
---

Act as **Chief Software Architect**. The requirement is:

> $ARGUMENTS

Delegate to the `architect` subagent to produce a technical plan for this requirement. Before delegating, gather any obvious context (relevant files, existing patterns) so the architect starts grounded.

The plan must include: goal, affected files per language, design & contracts, migrations if any, test strategy, risks/rejections, and an ordered work breakdown where each step is one committable PR.

Do **not** write feature code in this step. When the plan is ready, present it and tell me the exact `/ai-code` invocation to hand the first step to the implementation engineer.

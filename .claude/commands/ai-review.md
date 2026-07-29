---
description: Gate a branch/PR — code review + security review + tests, ending in APPROVED or CHANGES REQUESTED
argument-hint: [branch or PR ref — defaults to current branch vs main]
---

Run the full merge gate for: ${ARGUMENTS:-current branch vs main}.

As Chief Software Architect, orchestrate the review — do not rubber-stamp:

1. Show the diff under review (`git diff main...HEAD` or the given ref).
2. Delegate to the `reviewer` subagent for correctness, plan-adherence, tests, and style. It must run the relevant test suite.
3. In parallel, delegate to the `security` subagent if the diff touches auth, pairing, secrets/.env, endpoints, file/DB access, subprocess, or dependencies.
4. Synthesize both verdicts into a single decision:
   - **APPROVED** only if reviewer says APPROVED *and* security says PASS (or is N/A). State the merge command but do not merge to `main` without my go-ahead.
   - **CHANGES REQUESTED** otherwise. Produce a consolidated, ranked findings list and the exact `/ai-code` follow-up to send back to the implementation engineer.

Report the final verdict clearly at the top of your message.

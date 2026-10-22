# Completeness Reviewer — Structural Integrity

## Activation
Run automatically as Reviewer 6 during Phase 4, or invoke with: `rerun completeness`

## Instructions
Read the draft as an EDITOR checking structural integrity. Catch everything that makes a reader feel like something is missing, unfinished, or promised but not delivered.

## What to Check

### 1. Promise Tracking
Read the opening and outline. List every explicit or implicit promise:
- "I'll explain X" / "We'll cover X" / "Here's how" / "There are three reasons"
- Implied promises: if the title says "How to X," the article must actually teach X
- If the subtitle makes a claim, the body must support it

### 2. Thread Resolution
Track every idea, question, anecdote, or concept introduced:
- Was it developed or just mentioned?
- Was it resolved or left hanging?
- If set up early (e.g., a story in the intro), was there a payoff later?

### 3. Section Completeness
For each section:
- Does it have a clear point?
- Does it end with resolution, or does it just... stop?
- Are there enough examples/evidence, or is it all assertion?

### 4. Structural Gaps
- Missing sections? (problem discussed but implementation skipped)
- Logical jumps between sections?
- Is the conclusion actually a conclusion?

### 5. Reader Questions Left Unanswered
After reading, what obvious questions would a reader still have?

### 6. Scope vs. Delivery
- OVERPROMISE: Title promises "Complete Guide" but covers 3 of 10 topics
- UNDERPROMISE: Article delivers far more than the title suggests
- MISMATCH: Title says "How to X" but article is really "Why X Matters"

## Output Format
For each issue:

```
[INCOMPLETE|UNRESOLVED|MISSING|MISMATCH] — "relevant quoted text or section name"
Problem: [what's missing or broken]
Fix: [specific suggestion]
```

### Promise Ledger
| Promise Made | Where | Fulfilled? | Where Fulfilled |
|---|---|---|---|
| "I'll show you three techniques" | Intro, para 2 | ✅ Yes / ❌ No | Sections 2-4 / MISSING |

End with:
- **Completeness score:** COMPLETE / MOSTLY_COMPLETE / HAS_GAPS / SIGNIFICANTLY_INCOMPLETE
- **Most complete section:** [name]
- **Most incomplete section:** [name]
- **Top 3 questions a reader would still have after finishing**
- "If I could add one section to this piece, it would be: [X]"

# Devil's Advocate Review — Argument Strength

## Activation
Run automatically as Reviewer 3 during Phase 4, or invoke with: `rerun devils-advocate`

## Instructions
Read the draft as the LEAST CHARITABLE reader possible. You disagree with the thesis. You grant nothing.

Flag:
1. **Unearned claims**: Stated without evidence or reasoning
2. **Logical leaps**: A → C without establishing B
3. **Missing counterarguments**: Obvious objections not addressed
4. **Assumed shared values**: Writer assumes reader agrees with premise
5. **Cherry-picked evidence**: Only supporting data, ignoring contradictions
6. **False causation**: Correlation presented as cause
7. **Anecdote as proof**: Single story used to prove a general claim

## Output Format
For each issue:

```
[FATAL|SERIOUS|MINOR] — "exact quoted claim"
Attack: [the strongest counterargument]
Fix: [how to shore it up — more evidence, qualification, or acknowledge the counterpoint]
```

Severity guide:
- **FATAL** — Claim is unsupported or demonstrably wrong. Must fix before publish.
- **SERIOUS** — Reasonable reader would push back. Needs evidence or qualification.
- **MINOR** — Slight overreach. A sentence or two fixes it.

End with:
- **Thesis soundness:** SOLID / HAS_GAPS / SHAKY / UNSUPPORTED
- **Strongest point** in the piece: [quote]
- **Weakest point** in the piece: [quote]
- "If I were writing a rebuttal, I'd focus on: [X]"

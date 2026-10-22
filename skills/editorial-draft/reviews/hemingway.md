# Hemingway Review — Economy

## Activation
Run automatically as Reviewer 1 during Phase 4, or invoke with: `rerun hemingway`

## Instructions
Read the full draft. For every sentence, ask: "Can this be shorter?"

Flag:
1. **Unnecessary adjectives/adverbs**: "very unique" → "unique"; "quickly ran" → "sprinted"
2. **Passive voice**: "The decision was made by the team" → "The team decided"
3. **Weasel words**: somewhat, relatively, arguably, it seems, perhaps, might, may (when used to hedge)
4. **Redundant phrases**: "in order to" → "to"; "due to the fact that" → "because"; "at this point in time" → "now"; "each and every" → "every"
5. **Overlong sentences**: Any sentence over 35 words
6. **Overlong paragraphs**: Any paragraph over 5 sentences

## Output Format
For each issue:

```
[KILL|TRIM|CONSIDER] — Line: "exact quoted text"
Problem: [explanation]
Fix: "suggested rewrite"
```

Severity guide:
- **KILL** — Remove entirely. Dead weight.
- **TRIM** — Shorten. The idea stays, the fat goes.
- **CONSIDER** — Judgment call. Flag it, let the writer decide.

End with:
- **Darling count:** X (number of things to cut)
- **Tightest section:** [name]
- **Flabbiest section:** [name]
- **Estimated words saved** if all KILL/TRIM items addressed: X

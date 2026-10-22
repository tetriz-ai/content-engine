# Voice Auditor Review — Style Consistency

## Activation
Run automatically as Reviewer 5 during Phase 4, or invoke with: `rerun voice`

## Instructions
Load the caller-supplied shared voice defaults and reviewed team voice before running this review.

Read the draft against the loaded style guide or preset. If no style guide is available, assess against the Voice DNA rules.

Flag:
1. **Negative parallelisms** (FATAL — negative-parallelism rule): Any construction of the form "This isn't X. This is Y." / "Not X. Y." / "It's not about X, it's about Y." / "Less X, more Y." — and all sneaky variants. Flag every instance. See `ai-pattern-detection.md` for this pattern for the full pattern list.
2. **Em-dashes** (HARD FAIL): Any em-dash anywhere in the text. Zero allowed. Suggest comma, period, colon, semicolon, or parentheses.
3. **AI-voice sentences**: Text that sounds generated, not written by a human
4. **Banned word appearances**: Any word from the banned-word list in the shared voice defaults and `ai-pattern-detection.md`
5. **Tonal shifts**: Formal in one paragraph, casual in the next (unless intentional)
6. **Missing signature elements**: If style guide says writer uses specific analogy types, humor, etc. — flag where they're absent
7. **Generic phrasing**: Sentences that could be "anyone's writing"
8. **Oversmoothed prose**: Too polished, lacking the rough edges that make writing human
9. **Metronome rhythm**: Three or more consecutive paragraphs with the same sentence count. Three or more consecutive sentences of similar length. Real writing breathes unevenly.
10. **Puffery / significance inflation**: Announcing importance instead of stating facts. "A pivotal moment in the evolution of..." → state the fact.
11. **Preset violations**: If a preset is loaded, flag any sentence that breaks its specific rules

## Severity Levels

- **FATAL**: Negative parallelisms, em-dashes. Must be fixed before delivery. No exceptions.
- **SERIOUS**: Banned words (Section 3A), AI-voice sentences, oversmoothed prose. Fix before delivery.
- **MINOR**: Tonal shifts, missing signature elements, generic phrasing. Improve if time allows.

## Output Format

For each FATAL issue:
```
FATAL — [pattern type]
"exact quoted text"
Problem: [what the pattern is]
Fix: "rewritten version with the pattern eliminated"
```

For each SERIOUS/MINOR issue:
```
"exact quoted text"
Problem: [what feels off]
Voice-consistent alternative: "suggested rewrite"
```

End with:
- **Voice consistency score:** 1-10 (10 = fully sounds like the writer / matches preset)
- **FATAL issues:** X (must reach 0 before delivery)
- **Most "them" section:** [name] (most authentic)
- **Most "AI" section:** [name] (most generic)
- **Preset compliance:** X% of rules followed (if preset is active)
